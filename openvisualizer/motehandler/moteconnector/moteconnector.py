# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import socket
import threading

from pydispatch import dispatcher

from openvisualizer.eventbus.eventbusclient import EventBusClient
from openvisualizer.motehandler.moteconnector.openparser import openparser, parserexception
from openvisualizer.motehandler.motestate.motestate import MoteState

log = logging.getLogger('MoteConnector')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


class MoteConnector(EventBusClient):

    def __init__(self, mote_probe, stack_defines, mqtt_broker):

        # log
        log.debug("create instance")

        self.mote_probe = mote_probe
        self.stack_defines = stack_defines
        # store params
        self.serialport = self.mote_probe.portname

        # local variables
        self.parser = openparser.OpenParser(mqtt_broker, stack_defines, self.serialport)
        self.state_lock = threading.Lock()
        self.network_prefix = None
        self._subscribed_data_for_dagroot = False

        # give this thread a name
        self.name = 'mote_connector@{0}'.format(self.serialport)

        super(MoteConnector, self).__init__(
            name=self.name,
            registrations=[
                {
                    'sender': self.WILDCARD,
                    'signal': 'infoDagRoot',
                    'callback': self._info_dag_root_handler,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'cmdToMote',
                    'callback': self._cmd_to_mote_handler,
                },
            ],
        )

        self.mote_probe.send_to_parser = self._send_to_parser
        self.received_status_notif = None

    def _send_to_parser(self, data):

        # log
        log.debug("received input={0}".format(data))

        # parse input
        try:
            (event_sub_type, parsed_notif) = self.parser.parse_input(data)
            assert isinstance(event_sub_type, str)
        except parserexception.ParserException as err:
            # log
            log.error(str(err))
            pass
        else:
            if event_sub_type == 'status':
                if self.received_status_notif:
                    self.received_status_notif(parsed_notif)
            else:
                # dispatch
                self.dispatch('fromMote.' + event_sub_type, parsed_notif)

    # ======================== eventBus interaction ============================

    def _info_dag_root_handler(self, sender, signal, data):

        # I only care about "infoDagRoot" notifications about my mote
        if not data['serialPort'] == self.serialport:
            return

        with self.state_lock:

            if data['isDAGroot'] == 1 and (not self._subscribed_data_for_dagroot):
                # this mote_connector is connected to a DAGroot

                # connect to dispatcher
                self.register(sender=self.WILDCARD, signal='bytesToMesh', callback=self._bytes_to_mesh_handler)

                # remember I'm subscribed
                self._subscribed_data_for_dagroot = True

            elif data['isDAGroot'] == 0 and self._subscribed_data_for_dagroot:
                # this mote_connector is *not* connected to a DAGroot

                # disconnect from dispatcher
                self.unregister(sender=self.WILDCARD, signal='bytesToMesh', callback=self._bytes_to_mesh_handler)

                # remember I'm not subscribed
                self._subscribed_data_for_dagroot = False

    def _cmd_to_mote_handler(self, sender, signal, data):
        if data['serialPort'] == self.serialport:
            if data['action'] == MoteState.TRIGGER_DAGROOT:

                # retrieve the prefix of the network
                with self.state_lock:
                    if not self.network_prefix:
                        network_prefix = self._dispatch_and_get_result(signal='getNetworkPrefix', data=[])
                        self.network_prefix = network_prefix

                # retrieve the security key of the network
                with self.state_lock:
                    key_dict = self._dispatch_and_get_result(signal='getL2SecurityKey', data=[])

                # create data to send
                with self.state_lock:
                    data_to_send = [
                                       openparser.OpenParser.SERFRAME_PC2MOTE_SETDAGROOT,
                                       openparser.OpenParser.SERFRAME_ACTION_TOGGLE,
                                   ] + self.network_prefix + key_dict['index'] + key_dict['value']

                # toggle the DAGroot state
                self._send_to_mote_probe(data_to_send=data_to_send)
            else:
                raise SystemError('unexpected action={0}'.format(data['action']))

    def _bytes_to_mesh_handler(self, sender, signal, data):
        assert type(data) == tuple
        assert len(data) == 2

        next_hop, lowpan = data

        self._send_to_mote_probe(data_to_send=[openparser.OpenParser.SERFRAME_PC2MOTE_DATA] + next_hop + lowpan)

    # ======================== public ==========================================

    def quit(self):
        raise NotImplementedError()

    # ======================== private =========================================

    def _send_to_mote_probe(self, data_to_send):
        try:
            dispatcher.send(
                sender=self.name,
                signal='fromMoteConnector@' + self.serialport,
                data=''.join([chr(c) for c in data_to_send]),
            )

        except socket.error as err:
            log.error(err)
