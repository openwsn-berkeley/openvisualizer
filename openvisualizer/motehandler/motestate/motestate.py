# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
"""
Contains the motestate container class, as well as contained classes that
structure the mote data. Contained classes inherit from the abstract
StateElem class.
"""

import logging
import threading

from elements import StateOutputBuffer, StateAsn, StateJoined, StateMacStats, StateTable, StateScheduleRow, \
    StateBackoff, StateQueue, StateNeighborsRow, StateIsSync, StateIdManager, StateMyDagRank, StateKaPeriod
from openvisualizer.eventBus.eventBusClient import eventBusClient
from openvisualizer.motehandler.moteconnector.openparser import parserstatus

log = logging.getLogger('MoteState')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


class MoteState(eventBusClient):
    ST_OUPUTBUFFER = 'OutputBuffer'
    ST_ASN = 'Asn'
    ST_MACSTATS = 'MacStats'
    ST_SCHEDULEROW = 'ScheduleRow'
    ST_SCHEDULE = 'Schedule'
    ST_BACKOFF = 'Backoff'
    ST_QUEUEROW = 'QueueRow'
    ST_QUEUE = 'Queue'
    ST_NEIGHBORSROW = 'NeighborsRow'
    ST_NEIGHBORS = 'Neighbors'
    ST_ISSYNC = 'IsSync'
    ST_IDMANAGER = 'IdManager'
    ST_MYDAGRANK = 'MyDagRank'
    ST_KAPERIOD = 'kaPeriod'
    ST_JOINED = 'Joined'
    ST_ALL = [
        ST_OUPUTBUFFER,
        ST_ASN,
        ST_MACSTATS,
        ST_SCHEDULE,
        ST_BACKOFF,
        ST_QUEUE,
        ST_NEIGHBORS,
        ST_ISSYNC,
        ST_IDMANAGER,
        ST_MYDAGRANK,
        ST_KAPERIOD,
        ST_JOINED,
    ]

    TRIGGER_DAGROOT = 'DAGroot'
    SET_COMMAND = 'imageCommand'

    # command for golgen image       name,             id length
    COMMAND_SET_EBPERIOD = ['ebPeriod', 0, 1]
    COMMAND_SET_CHANNEL = ['channel', 1, 1]
    COMMAND_SET_KAPERIOD = ['kaPeriod', 2, 2]
    COMMAND_SET_DIOPERIOD = ['dioPeriod', 3, 2]
    COMMAND_SET_DAOPERIOD = ['daoPeriod', 4, 2]
    COMMAND_SET_DAGRANK = ['dagrank', 5, 2]
    COMMAND_SET_SECURITY_STATUS = ['security', 6, 1]
    COMMAND_SET_SLOTFRAMELENGTH = ['slotframeLength', 7, 2]
    COMMAND_SET_ACK_STATUS = ['ackReply', 8, 1]
    COMMAND_SET_6P_ADD = ['6pAdd', 9, 16]
    COMMAND_SET_6P_DELETE = ['6pDelete', 10, 8]
    COMMAND_SET_6P_RELOCATE = ['6pRelocate', 11, 24]
    COMMAND_SET_6P_COUNT = ['6pCount', 12, 3]
    COMMAND_SET_6P_LIST = ['6pList', 13, 7]
    COMMAND_SET_6P_CLEAR = ['6pClear', 14, 0]
    COMMAND_SET_SLOTDURATION = ['slotDuration', 15, 2]
    COMMAND_SET_6PRESPONSE = ['6pResponse', 16, 1]
    COMMAND_SET_UINJECTPERIOD = ['uinjectPeriod', 17, 1]
    COMMAND_SET_ECHO_REPLY_STATUS = ['echoReply', 18, 1]
    COMMAND_SET_JOIN_KEY = ['joinKey', 19, 16]
    COMMAND_ALL = [
        COMMAND_SET_EBPERIOD,
        COMMAND_SET_CHANNEL,
        COMMAND_SET_KAPERIOD,
        COMMAND_SET_DIOPERIOD,
        COMMAND_SET_DAOPERIOD,
        COMMAND_SET_DAGRANK,
        COMMAND_SET_SECURITY_STATUS,
        COMMAND_SET_SLOTFRAMELENGTH,
        COMMAND_SET_ACK_STATUS,
        COMMAND_SET_6P_ADD,
        COMMAND_SET_6P_DELETE,
        COMMAND_SET_6P_RELOCATE,
        COMMAND_SET_6P_COUNT,
        COMMAND_SET_6P_LIST,
        COMMAND_SET_6P_CLEAR,
        COMMAND_SET_SLOTDURATION,
        COMMAND_SET_6PRESPONSE,
        COMMAND_SET_UINJECTPERIOD,
        COMMAND_SET_ECHO_REPLY_STATUS,
        COMMAND_SET_JOIN_KEY,
    ]

    TRIGGER_ALL = [
        TRIGGER_DAGROOT,
    ]

    def __init__(self, mote_connector):

        # log
        log.info("create instance")

        # store params
        self.mote_connector = mote_connector

        # local variables
        self.parser_status = parserstatus.ParserStatus()
        self.state_lock = threading.Lock()
        self.state = {}

        self.state[self.ST_OUPUTBUFFER] = StateOutputBuffer()
        self.state[self.ST_ASN] = StateAsn()
        self.state[self.ST_JOINED] = StateJoined()
        self.state[self.ST_MACSTATS] = StateMacStats()
        self.state[self.ST_SCHEDULE] = StateTable(
            StateScheduleRow,
            column_order='.'.join(
                [
                    'slotOffset',
                    'type',
                    'shared',
                    'channelOffset',
                    'neighbor',
                    'numRx',
                    'numTx',
                    'numTxACK',
                    'lastUsedAsn',
                ]
            )
        )
        self.state[self.ST_BACKOFF] = StateBackoff()
        self.state[self.ST_QUEUE] = StateQueue()
        self.state[self.ST_NEIGHBORS] = StateTable(
            StateNeighborsRow,
            column_order='.'.join(
                [
                    'used',
                    'insecure',
                    'parentPreference',
                    'stableNeighbor',
                    'switchStabilityCounter',
                    'addr',
                    'DAGrank',
                    'rssi',
                    'numRx',
                    'numTx',
                    'numTxACK',
                    'numWraps',
                    'asn',
                    'joinPrio',
                    'f6PNORES',
                    'sixtopSeqNum',
                    'backoffExponent',
                    'backoff',
                ]
            ))
        self.state[self.ST_ISSYNC] = StateIsSync()
        self.state[self.ST_IDMANAGER] = StateIdManager(
            self,
            self.mote_connector
        )
        self.state[self.ST_MYDAGRANK] = StateMyDagRank()
        self.state[self.ST_KAPERIOD] = StateKaPeriod()

        self.notif_handlers = {
            self.parser_status.named_tuple[self.ST_OUPUTBUFFER]:
                self.state[self.ST_OUPUTBUFFER].update,
            self.parser_status.named_tuple[self.ST_ASN]:
                self.state[self.ST_ASN].update,
            self.parser_status.named_tuple[self.ST_MACSTATS]:
                self.state[self.ST_MACSTATS].update,
            self.parser_status.named_tuple[self.ST_SCHEDULEROW]:
                self.state[self.ST_SCHEDULE].update,
            self.parser_status.named_tuple[self.ST_BACKOFF]:
                self.state[self.ST_BACKOFF].update,
            self.parser_status.named_tuple[self.ST_QUEUEROW]:
                self.state[self.ST_QUEUE].update,
            self.parser_status.named_tuple[self.ST_NEIGHBORSROW]:
                self.state[self.ST_NEIGHBORS].update,
            self.parser_status.named_tuple[self.ST_ISSYNC]:
                self.state[self.ST_ISSYNC].update,
            self.parser_status.named_tuple[self.ST_IDMANAGER]:
                self.state[self.ST_IDMANAGER].update,
            self.parser_status.named_tuple[self.ST_MYDAGRANK]:
                self.state[self.ST_MYDAGRANK].update,
            self.parser_status.named_tuple[self.ST_KAPERIOD]:
                self.state[self.ST_KAPERIOD].update,
            self.parser_status.named_tuple[self.ST_JOINED]:
                self.state[self.ST_JOINED].update,

        }

        self.mote_connector.received_status_notif = self._received_status_notif

        # initialize parent class
        super(MoteState, self).__init__(
            name='motestate@{0}'.format(self.mote_connector.serialport),
            registrations=[
                {
                    'sender': 'mote_connector@{0}'.format(self.mote_connector.serialport),
                    'signal': 'fromMote.status',
                    'callback': self._received_status_notif,
                },
            ]
        )

    # ======================== public ==========================================

    def get_state_elem_names(self):

        with self.state_lock:
            return_val = self.state.keys()

        return return_val

    def get_state_elem(self, element_name):

        if element_name not in self.state:
            raise ValueError('No state called {0}'.format(element_name))

        with self.state_lock:
            return_val = self.state[element_name]

        return return_val

    def trigger_action(self, action):

        # dispatch
        self.dispatch(
            signal='cmdToMote',
            data={'serialPort': self.mote_connector.serialport, 'action': action}
        )

    # ======================== private =========================================

    def _received_status_notif(self, data):
        # log
        log.debug("received {0}".format(data))

        # lock the state data
        with self.state_lock:
            # call handler
            found = False
            for k, v in self.notif_handlers.items():
                if self._is_namedtuple_instance(data, k):
                    found = True
                    v(data)
                    break

        if not found:
            raise SystemError("No handler for data {0}".format(data))

    def _is_namedtuple_instance(self, var, tuple_instance):
        return var._fields == tuple_instance._fields
