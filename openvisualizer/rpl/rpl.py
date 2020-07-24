# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

"""
Module which coordinates rpl DIO and DAO messages.

.. module author:: Xavi Vilajosana <xvilajosana@eecs.berkeley.edu>
                  January 2013
.. module author:: Thomas Watteyne <watteyne@eecs.berkeley.edu>
                  April 2013
"""

import logging
import os
import threading

from appdirs import user_data_dir

from openvisualizer.eventbus import eventbusclient
from openvisualizer.rpl import sourceroute
from openvisualizer.utils import format_addr, format_buf, format_ipv6_addr

log = logging.getLogger('RPL')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


class RPL(eventbusclient.EventBusClient):
    _TARGET_INFORMATION_TYPE = 0x05
    _TRANSIT_INFORMATION_TYPE = 0x06

    # Period between successive DIOs, in seconds.
    DIO_PERIOD = 10

    ALL_RPL_NODES_MULTICAST = [0xff, 0x02] + [0x00] * 13 + [0x1a]

    # http://www.iana.org/assignments/protocol-numbers/protocol-numbers.xml
    IANA_ICMPv6_RPL_TYPE = 155

    # rpl DIO (RFC6550)
    DIO_OPT_GROUNDED = 1 << 7  # Grounded
    # Non-Storing Mode of Operation (1)
    MOP_DIO_A = 0 << 5
    MOP_DIO_B = 0 << 4
    MOP_DIO_C = 1 << 3
    # most preferred (7) as I am DAGRoot
    PRF_DIO_A = 1 << 2
    PRF_DIO_B = 1 << 1
    PRF_DIO_C = 1 << 0

    def __init__(self):

        # log
        log.debug("create instance")

        # initialize parent class
        eventbusclient.EventBusClient.__init__(
            self,
            name='rpl',
            registrations=[
                {
                    'sender': self.WILDCARD,
                    'signal': 'networkPrefix',
                    'callback': self._network_prefix_notif,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'infoDagRoot',
                    'callback': self._info_dagroot_notif,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'getSourceRoute',
                    'callback': self._get_source_route_notif,
                },
            ],
        )

        # local variables
        self.state_lock = threading.Lock()
        self.state = {}
        self.network_prefix = None
        self.dagroot_eui64 = None
        self.source_route = sourceroute.SourceRoute()
        self.latency_stats = {}
        self.parents_dao_seq = {}

    # ======================== public ==========================================

    def close(self):
        # nothing to do
        pass

    # ======================== private =========================================

    # ==== handle EventBus notifications

    def _network_prefix_notif(self, sender, signal, data):
        """ Record the network prefix. """
        # store
        with self.state_lock:
            self.network_prefix = data[:]

    def _info_dagroot_notif(self, sender, signal, data):
        """ Record the DAGroot's EUI64 address. """

        # stop of we don't have a networkPrefix assigned yet
        if not self.network_prefix:
            log.error("infoDagRoot signal received while not have been assigned a networkPrefix yet")
            return

        new_dagroot_eui64 = data['eui64'][:]

        with self.state_lock:
            same_dagroot = (self.dagroot_eui64 == new_dagroot_eui64)

        # register the DAGroot
        if data['isDAGroot'] == 1 and not same_dagroot:
            # log
            log.info("registering DAGroot {0}".format(format_addr(new_dagroot_eui64)))

            # register
            self.register(
                sender=self.WILDCARD,
                signal=(
                    tuple(self.network_prefix + new_dagroot_eui64),
                    self.PROTO_ICMPv6,
                    self.IANA_ICMPv6_RPL_TYPE,
                ),
                callback=self._from_mote_data_local_notif,
            )

            # announce new DAG root
            self.dispatch(
                signal='registerDagRoot',
                data={'prefix': self.network_prefix, 'host': new_dagroot_eui64},
            )

            # store DAGroot
            with self.state_lock:
                self.dagroot_eui64 = new_dagroot_eui64

        # unregister the DAGroot
        if data['isDAGroot'] == 0 and same_dagroot:
            # log
            log.warning("unregistering DAGroot {0}".format(format_addr(new_dagroot_eui64)))

            # unregister from old DAGroot
            self.unregister(
                sender=self.WILDCARD,
                signal=(
                    tuple(self.network_prefix + new_dagroot_eui64),
                    self.PROTO_ICMPv6,
                    self.IANA_ICMPv6_RPL_TYPE,
                ),
                callback=self._from_mote_data_local_notif,
            )

            # announce that node is no longer DAG root
            self.dispatch(
                signal='unregisterDagRoot',
                data={'prefix': self.network_prefix, 'host': self.dagroot_eui64},
            )

            # clear DAGroot
            with self.state_lock:
                self.dagroot_eui64 = None

    def _from_mote_data_local_notif(self, sender, signal, data):
        """ Called when receiving fromMote.data.local, probably a DAO. """
        # indicate data to topology
        self._indicate_dao(data)
        return True

    def _get_source_route_notif(self, sender, signal, data):
        destination = data
        return self.source_route.get_source_route(destination)

    # ===== receive DAO

    def _indicate_dao(self, tup):
        """
        Indicate a new DAO was received.
        This function parses the received packet, and if valid, updates the information needed to compute source routes.
        """
        dao = []
        # retrieve source and destination
        try:
            source = tup[0]
            if len(source) > 8:
                source = source[len(source) - 8:]
            dao = tup[1]
        except IndexError:
            log.warning("DAO too short ({0} bytes), no space for destination and source".format(len(dao)))
            return

        # log
        output = []
        output += ['received DAO:']
        output += ['- source :      {0}'.format(format_addr(source))]
        output += ['- dao :         {0}'.format(format_buf(dao))]
        output = '\n'.join(output)
        log.debug(output)

        # retrieve DAO header
        dao_header = {}
        dao_transit_information = {}
        dao_target_information = {}

        try:
            # rpl header
            dao_header['RPL_InstanceID'] = dao[0]
            dao_header['RPL_flags'] = dao[1]
            dao_header['RPL_Reserved'] = dao[2]
            dao_header['RPL_DAO_Sequence'] = dao[3]
            # DODAGID
            dao_header['DODAGID'] = dao[4:20]

            dao = dao[20:]
            # retrieve transit information header and parents
            parents = []
            children = []

            while len(dao) > 0:
                if dao[0] == self._TRANSIT_INFORMATION_TYPE:
                    # transit information option
                    dao_transit_information['Transit_information_type'] = dao[0]
                    dao_transit_information['Transit_information_length'] = dao[1]
                    dao_transit_information['Transit_information_flags'] = dao[2]
                    dao_transit_information['Transit_information_path_control'] = dao[3]
                    dao_transit_information['Transit_information_path_sequence'] = dao[4]
                    dao_transit_information['Transit_information_path_lifetime'] = dao[5]
                    # address of the parent
                    _ = dao[6:14]  # prefix
                    parents += [dao[14:22]]
                    dao = dao[22:]
                elif dao[0] == self._TARGET_INFORMATION_TYPE:
                    dao_target_information['Target_information_type'] = dao[0]
                    dao_target_information['Target_information_length'] = dao[1]
                    dao_target_information['Target_information_flags'] = dao[2]
                    dao_target_information['Target_information_prefix_length'] = dao[3]
                    # address of the child
                    _ = dao[4:12]  # prefix
                    children += [dao[12:20]]
                    dao = dao[20:]
                else:
                    log.warning("DAO with wrong Option {0}. Neither Transit nor Target.".format(dao[0]))
                    return
        except IndexError:
            log.warning("DAO too short ({0} bytes), no space for DAO header".format(len(dao)))
            return

        # log
        output = []
        output += [
            'received RPL DAO from {0}:{1}'.format(format_ipv6_addr(self.network_prefix), format_ipv6_addr(source))]
        output += ['- parents:']
        for p in parents:
            output += ['   {0}:{1}'.format(format_ipv6_addr(self.network_prefix), format_ipv6_addr(p))]
        output += ['- children:']
        for p in children:
            output += ['   {0}:{1}'.format(format_ipv6_addr(self.network_prefix), format_ipv6_addr(p))]
        output = '\n\t'.join(output)
        log.info(output)

        node = format_ipv6_addr(source)
        if not (node in self.parents_dao_seq.keys()):
            self.parents_dao_seq[node] = [dao_header['RPL_DAO_Sequence']]
        else:
            self.parents_dao_seq[node].append(dao_header['RPL_DAO_Sequence'])

        try:
            with open(os.path.join(user_data_dir('openvisualizer'), 'dao_sequence.txt'), 'a') as f:
                f.write(str(self.parents_dao_seq) + '\n')
        except IOError as err:
            log.error("Permission error: {}".format(err))

        # if you get here, the DAO was parsed correctly

        # update parents information with parents collected -- calls topology module.
        self.dispatch(signal='updateParents', data=(tuple(source), parents))

        # with self.data_lock:
        #    self.parents.update({tuple(source):parents})
