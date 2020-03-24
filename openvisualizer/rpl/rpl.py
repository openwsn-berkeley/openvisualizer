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
import threading

import openvisualizer.openvisualizer_utils as u
import sourcerouting
from openvisualizer.eventBus import eventBusClient

log = logging.getLogger('RPL')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


class RPL(eventBusClient.eventBusClient):
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
        eventBusClient.eventBusClient.__init__(
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
            ]
        )

        # local variables
        self.stateLock = threading.Lock()
        self.state = {}
        self.networkPrefix = None
        self.dagRootEui64 = None
        self.sourceRoute = sourcerouting.SourceRoute()
        self.latencyStats = {}
        self.parentsDaoSeq = {}

    # ======================== public ==========================================

    def close(self):
        # nothing to do
        pass

    # ======================== private =========================================

    # ==== handle EventBus notifications

    def _network_prefix_notif(self, sender, signal, data):
        """ Record the network prefix. """
        # store
        with self.stateLock:
            self.networkPrefix = data[:]

    def _info_dagroot_notif(self, sender, signal, data):
        """ Record the DAGroot's EUI64 address. """

        # stop of we don't have a networkPrefix assigned yet
        if not self.networkPrefix:
            log.error("infoDagRoot signal received while not have been assigned a networkPrefix yet")
            return

        new_dagroot_eui64 = data['eui64'][:]

        with self.stateLock:
            same_dagroot = (self.dagRootEui64 == new_dagroot_eui64)

        # register the DAGroot
        if data['isDAGroot'] == 1 and not same_dagroot:
            # log
            log.info("registering DAGroot {0}".format(u.formatAddr(new_dagroot_eui64)))

            # register
            self.register(
                sender=self.WILDCARD,
                signal=(
                    tuple(self.networkPrefix + new_dagroot_eui64),
                    self.PROTO_ICMPv6,
                    self.IANA_ICMPv6_RPL_TYPE
                ),
                callback=self._from_mote_data_local_notif,
            )

            # announce new DAG root
            self.dispatch(
                signal='registerDagRoot',
                data={'prefix': self.networkPrefix,
                      'host': new_dagroot_eui64}
            )

            # store DAGroot
            with self.stateLock:
                self.dagRootEui64 = new_dagroot_eui64

        # unregister the DAGroot
        if data['isDAGroot'] == 0 and same_dagroot:
            # log
            log.info("unregistering DAGroot {0}".format(u.formatAddr(new_dagroot_eui64)))

            # unregister from old DAGroot
            self.unregister(
                sender=self.WILDCARD,
                signal=(
                    tuple(self.networkPrefix + new_dagroot_eui64),
                    self.PROTO_ICMPv6,
                    self.IANA_ICMPv6_RPL_TYPE
                ),
                callback=self._from_mote_data_local_notif,
            )

            # announce that node is no longer DAG root
            self.dispatch(
                signal='unregisterDagRoot',
                data={'prefix': self.networkPrefix,
                      'host': self.dagRootEui64}
            )

            # clear DAGroot
            with self.stateLock:
                self.dagRootEui64 = None

    def _from_mote_data_local_notif(self, sender, signal, data):
        """ Called when receiving fromMote.data.local, probably a DAO. """
        # indicate data to topology
        self._indicate_dao(data)
        return True

    def _get_source_route_notif(self, sender, signal, data):
        destination = data
        return self.sourceRoute.getSourceRoute(destination)

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
        output += ['- source :      {0}'.format(u.formatAddr(source))]
        output += ['- dao :         {0}'.format(u.formatBuf(dao))]
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
                    prefix = dao[6:14]
                    parents += [dao[14:22]]
                    dao = dao[22:]
                elif dao[0] == self._TARGET_INFORMATION_TYPE:
                    dao_target_information['Target_information_type'] = dao[0]
                    dao_target_information['Target_information_length'] = dao[1]
                    dao_target_information['Target_information_flags'] = dao[2]
                    dao_target_information['Target_information_prefix_length'] = dao[3]
                    # address of the child
                    prefix = dao[4:12]
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
            'received RPL DAO from {0}:{1}'.format(u.formatIPv6Addr(self.networkPrefix), u.formatIPv6Addr(source))]
        output += ['- parents:']
        for p in parents:
            output += ['   {0}:{1}'.format(u.formatIPv6Addr(self.networkPrefix), u.formatIPv6Addr(p))]
        output += ['- children:']
        for p in children:
            output += ['   {0}:{1}'.format(u.formatIPv6Addr(self.networkPrefix), u.formatIPv6Addr(p))]
        output = '\n'.join(output)
        log.info(output)

        node = u.formatIPv6Addr(source)
        if not (node in self.parentsDaoSeq.keys()):
            self.parentsDaoSeq[node] = [dao_header['RPL_DAO_Sequence']]
        else:
            self.parentsDaoSeq[node].append(dao_header['RPL_DAO_Sequence'])

        with open('dao_sequence.txt', 'a') as f:
            f.write(str(self.parentsDaoSeq) + '\n')

        # if you get here, the DAO was parsed correctly

        # update parents information with parents collected -- calls topology module.
        self.dispatch(signal='updateParents', data=(tuple(source), parents))

        # with self.dataLock:
        #    self.parents.update({tuple(source):parents})
