# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import binascii
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

    def __init__(self, mote_probe, stack_defines):

        # log
        log.debug("create instance")

        self.mote_probe = mote_probe
        self.stack_defines = stack_defines
        # store params
        self.serialport = self.mote_probe.portname

        # local variables
        self.parser = openparser.OpenParser(mote_probe.mqtt_broker_address, stack_defines)
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
            ]
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
                self.register(
                    sender=self.WILDCARD,
                    signal='bytesToMesh',
                    callback=self._bytes_to_mesh_handler,
                )

                # remember I'm subscribed
                self._subscribed_data_for_dagroot = True

            elif data['isDAGroot'] == 0 and self._subscribed_data_for_dagroot:
                # this mote_connector is *not* connected to a DAGroot

                # disconnect from dispatcher
                self.unregister(
                    sender=self.WILDCARD,
                    signal='bytesToMesh',
                    callback=self._bytes_to_mesh_handler,
                )

                # remember I'm not subscribed
                self._subscribed_data_for_dagroot = False

    def _cmd_to_mote_handler(self, sender, signal, data):
        if data['serialPort'] == self.serialport:
            if data['action'] == MoteState.TRIGGER_DAGROOT:

                # retrieve the prefix of the network
                with self.state_lock:
                    if not self.network_prefix:
                        network_prefix = self._dispatch_and_get_result(
                            signal='getNetworkPrefix',
                            data=[],
                        )
                        self.network_prefix = network_prefix

                # retrieve the security key of the network
                with self.state_lock:
                    key_dict = self._dispatch_and_get_result(
                        signal='getL2SecurityKey',
                        data=[],
                    )

                # create data to send
                with self.state_lock:
                    data_to_send = [
                                       openparser.OpenParser.SERFRAME_PC2MOTE_SETDAGROOT,
                                       openparser.OpenParser.SERFRAME_ACTION_TOGGLE,
                                   ] + self.network_prefix + key_dict['index'] + key_dict['value']

                # toggle the DAGroot state
                self._send_to_mote_probe(data_to_send=data_to_send)
            elif data['action'][0] == MoteState.SET_COMMAND:
                # this is command for golden image
                with self.state_lock:
                    [success, data_to_send] = self._command_to_bytes(data['action'][1:])

                if not success:
                    return

                # send command to GD image
                self._send_to_mote_probe(data_to_send=data_to_send)
            else:
                raise SystemError('unexpected action={0}'.format(data['action']))

    def _command_to_bytes(self, data):

        # data[0]: commandID
        # data[1]: parameter

        outcome = False
        data_to_send = []
        ptr = 0

        # get commandId
        command_index = 0
        for cmd in MoteState.COMMAND_ALL:
            if data[0] == cmd[0]:
                command_id = cmd[1]
                command_len = cmd[2]
                break
            else:
                command_index += 1

        # check avaliability of command
        if command_index == len(MoteState.COMMAND_ALL):
            print "============================================="
            print "Wrong Command Type! Available Command Type: {"
            for cmd in MoteState.COMMAND_ALL:
                print " {0}".format(cmd[0])
            print " }"
            return [outcome, data_to_send]

        if data[0][:2] == '6p':
            try:
                data_to_send = [openparser.OpenParser.SERFRAME_PC2MOTE_COMMAND, command_id, command_len]
                param_list = data[1].split(',')
                if data[0] != '6pClear':
                    if param_list[0] == 'tx':
                        cell_options = 1 << 0
                    elif param_list[0] == 'rx':
                        cell_options = 1 << 1
                    elif param_list[0] == 'shared':
                        cell_options = 1 << 0 | 1 << 1 | 1 << 2
                    else:
                        print "unsupport cell_options!"
                        assert True
                else:
                    data_to_send[2] = len(data_to_send) - 3
                    outcome = True
                    return [outcome, data_to_send]
                ptr += 1
                data_to_send += [cell_options]
                cell_list_add = {}
                cell_list_delete = {}
                if data[0] == '6pList' and len(param_list) == 3:
                    data_to_send += map(int, param_list[ptr:])
                if data[0] == '6pAdd':
                    # append numCell
                    data_to_send += [int(param_list[ptr])]
                    # append celllist
                    cell_list_add['slotoffset'] = param_list[ptr + 1].split('-')
                    cell_list_add['channeloffset'] = param_list[ptr + 2].split('-')
                    if len(cell_list_add['slotoffset']) != len(cell_list_add['channeloffset']) or len(
                            cell_list_add['slotoffset']) < int(param_list[ptr]):
                        print "the length of slotoffset list and channeloffset list for candidate cell should be equal!"
                        assert True
                    data_to_send += map(int, cell_list_add['slotoffset'])
                    data_to_send += map(int, cell_list_add['channeloffset'])
                if data[0] == '6pDelete':
                    # append numCell
                    data_to_send += [int(param_list[ptr])]
                    # append celllist
                    cell_list_delete['slotoffset'] = param_list[ptr + 1].split('-')
                    cell_list_delete['channeloffset'] = param_list[ptr + 2].split('-')
                    if int(param_list[ptr]) != len(cell_list_delete['slotoffset']) or int(param_list[ptr]) != len(
                            cell_list_delete['channeloffset']):
                        print "length of celllist (slotoffset/channeloffset) to delete doesn't match numCell!"
                        assert False
                    data_to_send += map(int, cell_list_delete['slotoffset'])
                    data_to_send += map(int, cell_list_delete['channeloffset'])
                if data[0] == '6pRelocate':
                    data_to_send += [int(param_list[ptr])]
                    # append cell_list
                    cell_list_delete['slotoffset'] = param_list[ptr + 1].split('-')
                    cell_list_delete['channeloffset'] = param_list[ptr + 2].split('-')
                    if int(param_list[ptr]) != len(cell_list_delete['slotoffset']) or int(param_list[ptr]) != len(
                            cell_list_delete['channeloffset']):
                        print "length of celllist (slotoffset/channeloffset) to delete doesn't match numCell!"
                        assert False
                    data_to_send += map(int, cell_list_delete['slotoffset'])
                    data_to_send += map(int, cell_list_delete['channeloffset'])
                    ptr += 3
                    # append cell_list
                    cell_list_add['slotoffset'] = param_list[ptr].split('-')
                    cell_list_add['channeloffset'] = param_list[ptr + 1].split('-')
                    if len(cell_list_add['slotoffset']) != len(cell_list_add['channeloffset']) or len(
                            cell_list_add['slotoffset']) < len(cell_list_delete['slotoffset']):
                        print "The length of slotoffset list and channeloffset list for candidate cell should be " \
                              "equal and the length of candidate celllist must no less than numCell! "
                        assert False
                    data_to_send += map(int, cell_list_add['slotoffset'])
                    data_to_send += map(int, cell_list_add['channeloffset'])
                data_to_send[2] = len(data_to_send) - 3
                outcome = True
                return [outcome, data_to_send]
            except:
                print "============================================="
                print "Wrong 6p parameter format."
                print "                           command    cell_options numCell     cell_list_delete         cell_list_add       listoffset maxListLen addition"
                print "                                                          (slotlist,channellist)  (slotlist,channellist)"
                print "comma. e.g. set <portname> 6pAdd      tx,         1,                                  5-6-7,4-4-4"
                print "comma. e.g. set <portname> 6pDelete   rx,         1,              5,4"
                print "comma. e.g. set <portname> 6pRelocate tx,         1,              5,4,                6-7-8,4-4-4"
                print "comma. e.g. set <portname> 6pCount    shared"
                print "comma. e.g. set <portname> 6pList     tx,                                                                 5,         3"
                print "comma. e.g. set <portname> 6pClear                                                                                              all"
                return [outcome, data_to_send]
        elif data[0] == 'joinKey':
            try:
                if len(data[1]) != command_len * 2:  # two hex chars is one byte
                    raise ValueError
                payload = binascii.unhexlify(data[1])
                data_to_send = [openparser.OpenParser.SERFRAME_PC2MOTE_COMMAND, command_id, command_len]
                data_to_send += [ord(b) for b in payload]
            except:
                print "============================================="
                print "Wrong joinKey format. Input 16-byte long hex string. e.g. cafebeefcafebeefcafebeefcafebeef"
        else:
            parameter = int(data[1])
            if parameter <= 0xffff:
                parameter = [(parameter & 0xff), ((parameter >> 8) & 0xff)]
                data_to_send = [openparser.OpenParser.SERFRAME_PC2MOTE_COMMAND,
                                command_id,
                                command_len,  # length
                                parameter[0],
                                parameter[1]
                                ]
            else:
                # more than two bytes parameter, error
                print "============================================="
                print "Paramter Wrong! (Available: 0x0000~0xffff)\n"
                return [outcome, data_to_send]

        # the command is legal if I got here
        data_to_send[2] = len(data_to_send) - 3
        outcome = True
        return [outcome, data_to_send]

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
                data=''.join([chr(c) for c in data_to_send])
            )

        except socket.error as err:
            log.error(err)
