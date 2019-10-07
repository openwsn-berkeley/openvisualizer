# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
'''
Contains the moteState container class, as well as contained classes that
structure the mote data. Contained classes inherit from the abstract
StateElem class.
'''
import logging
log = logging.getLogger('moteState')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


import copy
import time
import threading
import json

from openvisualizer.moteConnector import ParserStatus
from openvisualizer.eventBus      import eventBusClient
from openvisualizer.openType      import openType,         \
                                         typeAsn,          \
                                         typeAddr,         \
                                         typeCellType,     \
                                         typeComponent,    \
                                         typeRssi

from openvisualizer import openvisualizer_utils as u

class OpenEncoder(json.JSONEncoder):
    def default(self, obj):
        if   isinstance(obj, (StateElem,openType.openType)):
            return { obj.__class__.__name__: obj.__dict__ }
        else:
            return super(OpenEncoder, self).default(obj)

class StateElem(object):
    '''
    Abstract superclass for internal mote state classes.
    '''
    
    def __init__(self):
        self.meta                      = [{}]
        self.data                      = []
        
        self.meta[0]['numUpdates']     = 0
        self.meta[0]['lastUpdated']    = None
    
    #======================== public ==========================================
    
    def update(self):
        self.meta[0]['lastUpdated']    = time.time()
        self.meta[0]['numUpdates']    += 1
    
    def toJson(self, aspect='all', isPrettyPrint=False):
        '''
        Dumps state to JSON.
        
        :param aspect: 
               The particular aspect of the state object to dump, or the 
               default 'all' for all aspects. Aspect names:
               'meta' -- Metadata collected about the state;
               'data' -- State data itself
        :param isPrettyPrint:
               If evaluates true, provides more readable output by sorting 
               keys and indenting members.
        :returns: JSON representing the object. If aspect is 'all', 
                the JSON is a dictionary, with sub-dictionaries
                for the meta and data aspects. Otherwise, the JSON
                is a list of the selected aspect's content.
        '''
        content = None
        if aspect   == 'all':
            content = self._toDict()
        elif aspect == 'data':
            content = self._elemToDict(self.data)
        elif aspect == 'meta':
            content = self._elemToDict(self.meta)
        else:
            raise ValueError('No aspect named {0}'.format(aspect))
        
        return json.dumps(content,
                          sort_keys = bool(isPrettyPrint),
                          indent    = 4 if isPrettyPrint else None)
    
    def __str__(self):
        return self.toJson(isPrettyPrint=True)
    
    #======================== private =========================================
    
    def _toDict(self):
        returnVal = {}
        returnVal['meta'] = self._elemToDict(self.meta)
        returnVal['data'] = self._elemToDict(self.data)
        return returnVal
    
    def _elemToDict(self,elem):
        returnval = []
        for rowNum in range(len(elem)):
            if   isinstance(elem[rowNum],dict):
                returnval.append({})
                for k,v in elem[rowNum].items():
                    if isinstance(v,(list, tuple)):
                        returnval[-1][k]    = [m._toDict() for m in v]
                    else:
                        if   isinstance(v,openType.openType):
                           returnval[-1][k] = str(v)
                        elif isinstance(v,type):
                           returnval[-1][k] = v.__name__
                        else:
                           returnval[-1][k] = v
            elif isinstance(elem[rowNum],StateElem):
                parsedRow = elem[rowNum]._toDict()
                assert('data' in parsedRow)
                assert(len(parsedRow['data'])<2)
                if len(parsedRow['data'])==1:
                    returnval.append(parsedRow['data'][0])
            else:
                raise SystemError("can not parse elem of type {0}".format(type(elem[rowNum])))
        return returnval

class StateOutputBuffer(StateElem):
    
    def update(self,data):
        (moteInfo, notif) = data
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['index_write']         = notif.index_write
        self.data[0]['index_read']          = notif.index_read

class StateAsn(StateElem):
    
    def update(self,data):
        (moteInfo, notif) = data
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        if 'asn' not in self.data[0]:
            self.data[0]['asn']             = typeAsn.typeAsn()
        self.data[0]['asn'].update(notif.asn_0_1,
                                   notif.asn_2_3,
                                   notif.asn_4)

    def getAsn(self):
        if len(self.data) != 0:
            return self.data[0]['asn']
        return None

class StateMacStats(StateElem):
    
    def update(self,data):
        (moteInfo, notif) = data
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['numSyncPkt']          = notif.numSyncPkt
        self.data[0]['numSyncAck']          = notif.numSyncAck
        self.data[0]['minCorrection']       = notif.minCorrection
        self.data[0]['maxCorrection']       = notif.maxCorrection
        self.data[0]['numDeSync']           = notif.numDeSync
        if notif.numTicsTotal!=0:
            dutyCycle                       = (float(notif.numTicsOn)/float(notif.numTicsTotal))*100
            self.data[0]['dutyCycle']       = '{0:.02f}%'.format(dutyCycle)
        else:
            self.data[0]['dutyCycle']       = '?'

    def getDutyCycle(self):
        if len(self.data)!=0:
            return self.data[0]['dutyCycle']
        return None

class StateScheduleRow(StateElem):

    def update(self,data):
        (moteInfo, notif) = data
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['slotOffset']          = notif.slotOffset
        if 'type' not in self.data[0]:
            self.data[0]['type']            = typeCellType.typeCellType()
        self.data[0]['type'].update(notif.type)
        self.data[0]['shared']              = notif.shared
        self.data[0]['channelOffset']       = notif.channelOffset
        if 'neighbor' not in self.data[0]:
            self.data[0]['neighbor']        = typeAddr.typeAddr()
        self.data[0]['neighbor'].update(notif.neighbor_type,
                                        notif.neighbor_bodyH,
                                        notif.neighbor_bodyL)
        self.data[0]['numRx']               = notif.numRx
        self.data[0]['numTx']               = notif.numTx
        self.data[0]['numTxACK']            = notif.numTxACK
        if 'lastUsedAsn' not in self.data[0]:
            self.data[0]['lastUsedAsn']     = typeAsn.typeAsn()
        self.data[0]['lastUsedAsn'].update(notif.lastUsedAsn_0_1,
                                           notif.lastUsedAsn_2_3,
                                           notif.lastUsedAsn_4)

    def getType(self):
        return self.data[0]['type']

class StateBackoff(StateElem):
    
    def update(self,data):
        (moteInfo, notif) = data
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['backoffExponent']     = notif.backoffExponent
        self.data[0]['backoff']             = notif.backoff

class StateQueueRow(StateElem):
    
    def update(self,creator,owner):
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        
        if 'creator' not in self.data[0]:
            self.data[0]['creator']         = typeComponent.typeComponent()
        self.data[0]['creator'].update(creator)
        if 'owner' not in self.data[0]:
            self.data[0]['owner']           = typeComponent.typeComponent()
        self.data[0]['owner'].update(owner)

class StateQueue(StateElem):
    
    def __init__(self):
        StateElem.__init__(self)
        
        for i in range(20):
            self.data.append(StateQueueRow())
    
    def update(self,data):
        (moteInfo, notif) = data
        StateElem.update(self)
        self.data[0].update(notif.creator_0,notif.owner_0)
        self.data[1].update(notif.creator_1,notif.owner_1)
        self.data[2].update(notif.creator_2,notif.owner_2)
        self.data[3].update(notif.creator_3,notif.owner_3)
        self.data[4].update(notif.creator_4,notif.owner_4)
        self.data[5].update(notif.creator_5,notif.owner_5)
        self.data[6].update(notif.creator_6,notif.owner_6)
        self.data[7].update(notif.creator_7,notif.owner_7)
        self.data[8].update(notif.creator_8,notif.owner_8)
        self.data[9].update(notif.creator_9,notif.owner_9)
        self.data[10].update(notif.creator_10,notif.owner_10)
        self.data[11].update(notif.creator_11,notif.owner_11)
        self.data[12].update(notif.creator_12,notif.owner_12)
        self.data[13].update(notif.creator_13,notif.owner_13)
        self.data[14].update(notif.creator_14,notif.owner_14)
        self.data[15].update(notif.creator_15,notif.owner_15)
        self.data[16].update(notif.creator_16,notif.owner_16)
        self.data[17].update(notif.creator_17,notif.owner_17)
        self.data[18].update(notif.creator_18,notif.owner_18)
        self.data[19].update(notif.creator_19,notif.owner_19)

class StateNeighborsRow(StateElem):
    
    def update(self,data):
        (moteInfo, notif) = data
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['used']                     = notif.used
        self.data[0]['insecure']                 = notif.insecure
        self.data[0]['parentPreference']         = notif.parentPreference
        self.data[0]['stableNeighbor']           = notif.stableNeighbor
        self.data[0]['switchStabilityCounter']   = notif.switchStabilityCounter
        self.data[0]['joinPrio']                 = notif.joinPrio
        if 'addr' not in self.data[0]:
            self.data[0]['addr']                 = typeAddr.typeAddr()
        self.data[0]['addr'].update(notif.addr_type,
                                    notif.addr_bodyH,
                                    notif.addr_bodyL)
        self.data[0]['DAGrank']                  = notif.DAGrank
        if 'rssi' not in self.data[0]:
            self.data[0]['rssi']                 = typeRssi.typeRssi()
        self.data[0]['rssi'].update(notif.rssi)
        self.data[0]['numRx']                    = notif.numRx
        self.data[0]['numTx']                    = notif.numTx
        self.data[0]['numTxACK']                 = notif.numTxACK
        self.data[0]['numWraps']                 = notif.numWraps
        if 'asn' not in self.data[0]:
            self.data[0]['asn']                  = typeAsn.typeAsn()
        self.data[0]['asn'].update(notif.asn_0_1,
                                   notif.asn_2_3,
                                   notif.asn_4)
        self.data[0]['f6PNORES']                 = notif.f6PNORES
        self.data[0]['sixtopSeqNum']             = notif.sixtopSeqNum
        self.data[0]['backoffExponent']          = notif.backoffExponent
        self.data[0]['backoff']                  = notif.backoff

class StateIsSync(StateElem):
    
    def update(self,data):
        (moteInfo, notif) = data
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['isSync']              = notif.isSync

class StateIdManager(StateElem):
    
    def __init__(self,eventBusClient,moteConnector):
        StateElem.__init__(self)
        self.eventBusClient  = eventBusClient
        self.moteConnector   = moteConnector
        self.isDAGroot       = None
    
    def get16bAddr(self):
        try:
            return self.data[0]['my16bID'].addr[:]
        except IndexError:
            return []

    def get64bAddr(self):
        try:
            return self.data[0]['my64bID'].addr[:]
        except IndexError:
            return []

    def get_serial(self):
        return self.moteConnector.serialport

    def get_info(self):
        return {
            '64bAddr'   : u.formatAddr(self.get64bAddr()),
            '16bAddr'   : u.formatAddr(self.get16bAddr()),
            'isDAGroot' : self.isDAGroot,
            'serial'    : self.get_serial(),
        }

    def update(self,data):

        (moteInfo, notif) = data
    
        # update state
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        
        self.data[0]['isDAGroot']           = notif.isDAGroot
        
        if 'myPANID' not  in self.data[0]:
            self.data[0]['myPANID']         = typeAddr.typeAddr()
            self.data[0]['myPANID'].desc    = 'panId'
        self.data[0]['myPANID'].addr        = [
            notif.myPANID_0,
            notif.myPANID_1,
        ]
        
        if 'my16bID' not  in self.data[0]:
            self.data[0]['my16bID']         = typeAddr.typeAddr()
            self.data[0]['my16bID'].desc    = '16b'
        self.data[0]['my16bID'].addr        = [
            notif.my16bID_0,
            notif.my16bID_1,
        ]
        
        if 'my64bID' not  in self.data[0]:
            self.data[0]['my64bID']         = typeAddr.typeAddr()
            self.data[0]['my64bID'].desc    = '64b'
        self.data[0]['my64bID'].addr        = [
            notif.my64bID_0,
            notif.my64bID_1,
            notif.my64bID_2,
            notif.my64bID_3,
            notif.my64bID_4,
            notif.my64bID_5,
            notif.my64bID_6,
            notif.my64bID_7
        ]
        
        if 'myPrefix' not  in self.data[0]:
            self.data[0]['myPrefix']        = typeAddr.typeAddr()
            self.data[0]['myPrefix'].desc   = 'prefix'
        self.data[0]['myPrefix'].addr       = [
            notif.myPrefix_0,
            notif.myPrefix_1,
            notif.myPrefix_2,
            notif.myPrefix_3,
            notif.myPrefix_4,
            notif.myPrefix_5,
            notif.myPrefix_6,
            notif.myPrefix_7,
        ]
        
        # announce information about the DAG root to the eventBus
        if  self.isDAGroot!=self.data[0]['isDAGroot']:
            
            # dispatch
            self.eventBusClient.dispatch(
                signal        = 'infoDagRoot',
                data          = {
                                    'isDAGroot':    self.data[0]['isDAGroot'],
                                    'eui64':        self.data[0]['my64bID'].addr,
                                    'serialPort':   self.moteConnector.serialport,
                                },
            )
        
        # record isDAGroot
        self.isDAGroot = self.data[0]['isDAGroot']

class StateMyDagRank(StateElem):
    
    def update(self,data):
        (moteInfo, notif) = data
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['myDAGrank']           = notif.myDAGrank

class StatekaPeriod(StateElem):
    
    def update(self,data):
        (moteInfo, notif) = data
        StateElem.update(self)
        if len(self.data)==0:
            self.data.append({})
        self.data[0]['kaPeriod']            = notif.kaPeriod

# abstract class
class StateTable(StateElem):

    def __init__(self,rowClass,columnOrder=None):
        StateElem.__init__(self)
        self.meta[0]['rowClass']            = rowClass
        if columnOrder:
            self.meta[0]['columnOrder']     = columnOrder
        self.data                           = []

    def update(self,data):
        (moteInfo, notif) = data
        StateElem.update(self)
        while len(self.data)<notif.row+1:
            self.data.append(self.meta[0]['rowClass']())
        self.data[notif.row].update(data)

        if notif.row + 1 == len(self.data):
            self.log(moteInfo)

    def log(self, id):
        raise NotImplementedError

class StateSchedule(StateTable):

    def __init__(self, *args, **kwargs):
        super(StateSchedule, self).__init__(*args, **kwargs)

    def log(self, moteInfo):
        try:
            numCellsTx = sum(row.getType().getCellType() == "TX" for row in self.data)
            numCellsRx = sum(row.getType().getCellType() == "RX" for row in self.data)
            numCellsTxRx = sum(row.getType().getCellType() == "TXRX" for row in self.data)
            numCells = numCellsTx + numCellsRx + numCellsTxRx

            # TODO publish
        except:
            pass

class StateNeighbors(StateTable):
    def __init__(self, *args, **kwargs):
        super(StateNeighbors, self).__init__(*args, **kwargs)

    def log(self,moteInfo):
        pass

class moteState(eventBusClient.eventBusClient):
    
    ST_OUPUTBUFFER                 = 'OutputBuffer'
    ST_ASN                         = 'Asn'
    ST_MACSTATS                    = 'MacStats'
    ST_SCHEDULEROW                 = 'ScheduleRow'
    ST_SCHEDULE                    = 'Schedule'
    ST_BACKOFF                     = 'Backoff'
    ST_QUEUEROW                    = 'QueueRow'
    ST_QUEUE                       = 'Queue'
    ST_NEIGHBORSROW                = 'NeighborsRow'
    ST_NEIGHBORS                   = 'Neighbors'
    ST_ISSYNC                      = 'IsSync'
    ST_IDMANAGER                   = 'IdManager'
    ST_MYDAGRANK                   = 'MyDagRank'
    ST_KAPERIOD                    = 'kaPeriod'
    ST_ALL              = [
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
    ]
    
    TRIGGER_DAGROOT     = 'DAGroot'
    SET_COMMAND         = 'imageCommand'

    # command for golgen image       name,             id length
    COMMAND_SET_EBPERIOD          = ['ebPeriod',       0, 1]
    COMMAND_SET_CHANNEL           = ['channel',        1, 1]
    COMMAND_SET_KAPERIOD          = ['kaPeriod',       2, 2]
    COMMAND_SET_DIOPERIOD         = ['dioPeriod',      3, 2]
    COMMAND_SET_DAOPERIOD         = ['daoPeriod',      4, 2]
    COMMAND_SET_DAGRANK           = ['dagrank',        5, 2]
    COMMAND_SET_SECURITY_STATUS   = ['security',       6, 1]
    COMMAND_SET_SLOTFRAMELENGTH   = ['slotframeLength',7, 2]
    COMMAND_SET_ACK_STATUS        = ['ackReply',       8, 1]
    COMMAND_SET_6P_ADD            = ['6pAdd',          9,16] # maxium three candidate cells, length could be shorter
    COMMAND_SET_6P_DELETE         = ['6pDelete',      10, 8] # only one cell to delete
    COMMAND_SET_6P_RELOCATE       = ['6pRelocate',    11,24] # one cell to relocate, three candidate cells , length could be shorter
    COMMAND_SET_6P_COUNT          = ['6pCount',       12, 3]
    COMMAND_SET_6P_LIST           = ['6pList',        13, 7]
    COMMAND_SET_6P_CLEAR          = ['6pClear',       14, 0]
    COMMAND_SET_SLOTDURATION      = ['slotDuration',  15, 2]
    COMMAND_SET_6PRESPONSE        = ['6pResponse',    16, 1]
    COMMAND_SET_UINJECTPERIOD     = ['uinjectPeriod', 17, 1]
    COMMAND_SET_ECHO_REPLY_STATUS = ['echoReply',     18, 1]
    COMMAND_SET_JOIN_KEY          = ['joinKey',       19,16]
    COMMAND_SET_TX_POWER          = ['txPower',       20, 1]
    COMMAND_SEND_PACKET           = ['sendPacket',    21, 16] # dest_eui64 (8B) || con (1B) || packetsInBurst (1B) || packetToken (5B) || packetPayloadLen (1B)
    COMMAND_ALL                   = [
        COMMAND_SET_EBPERIOD ,
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
        COMMAND_SET_TX_POWER,
        COMMAND_SEND_PACKET,
    ]

    TRIGGER_ALL         = [
        TRIGGER_DAGROOT,
    ]
    
    def __init__(self,moteConnector):
        
        # log
        log.info("create instance")
        
        # store params
        self.moteConnector   = moteConnector
        
      
        # local variables
        self.parserStatus                   = ParserStatus.ParserStatus()
        self.stateLock                      = threading.Lock()
        self.state                          = {}
        
        self.state[self.ST_OUPUTBUFFER]     = StateOutputBuffer()
        self.state[self.ST_ASN]             = StateAsn()
        self.state[self.ST_MACSTATS]        = StateMacStats()
        self.state[self.ST_SCHEDULE]        = StateSchedule(
                                                StateScheduleRow,
                                                columnOrder = '.'.join(
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
        self.state[self.ST_BACKOFF]         = StateBackoff()
        self.state[self.ST_QUEUE]           = StateQueue()
        self.state[self.ST_NEIGHBORS]       = StateNeighbors(
                                                StateNeighborsRow,
                                                columnOrder = '.'.join(
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
        self.state[self.ST_ISSYNC]          = StateIsSync()
        self.state[self.ST_IDMANAGER]       = StateIdManager(
                                                self,
                                                self.moteConnector
                                              )
        self.state[self.ST_MYDAGRANK]       = StateMyDagRank()
        self.state[self.ST_KAPERIOD]        = StatekaPeriod()
        
        self.notifHandlers = {
            self.parserStatus.named_tuple[self.ST_OUPUTBUFFER]:
                self.state[self.ST_OUPUTBUFFER].update,
            self.parserStatus.named_tuple[self.ST_ASN]:
                self.state[self.ST_ASN].update,
            self.parserStatus.named_tuple[self.ST_MACSTATS]:
                self.state[self.ST_MACSTATS].update,
            self.parserStatus.named_tuple[self.ST_SCHEDULEROW]:
                self.state[self.ST_SCHEDULE].update,
            self.parserStatus.named_tuple[self.ST_BACKOFF]:
                self.state[self.ST_BACKOFF].update,
            self.parserStatus.named_tuple[self.ST_QUEUEROW]:
                self.state[self.ST_QUEUE].update,
            self.parserStatus.named_tuple[self.ST_NEIGHBORSROW]:
                self.state[self.ST_NEIGHBORS].update,
            self.parserStatus.named_tuple[self.ST_ISSYNC]:
                self.state[self.ST_ISSYNC].update,
            self.parserStatus.named_tuple[self.ST_IDMANAGER]:
                self.state[self.ST_IDMANAGER].update,
            self.parserStatus.named_tuple[self.ST_MYDAGRANK]:
                self.state[self.ST_MYDAGRANK].update,
            self.parserStatus.named_tuple[self.ST_KAPERIOD]:
                self.state[self.ST_KAPERIOD].update,
        }
        
        # initialize parent class
        eventBusClient.eventBusClient.__init__(
            self,
            name             = 'moteState@{0}'.format(self.moteConnector.serialport),
            registrations    = [
                {
                    'sender'      : 'moteConnector@{0}'.format(self.moteConnector.serialport),
                    'signal'      : 'fromMote.status',
                    'callback'    : self._receivedStatus_notif,
                },
                {
                    'sender':  self.WILDCARD,
                    'signal': 'getDutyCycleMeasurement',
                    'callback': self._getDutyCycle,
                },
            ]
        )

        self.moteConnector.receivedStatus_notif  = self._receivedStatus_notif
    
    #======================== public ==========================================
    
    def getStateElemNames(self):
        
        self.stateLock.acquire()
        returnVal = self.state.keys()
        self.stateLock.release()
        
        return returnVal
    
    def getStateElem(self,elemName):
        
        if elemName not in self.state:
            raise ValueError('No state called {0}'.format(elemName))
        
        self.stateLock.acquire()
        returnVal = self.state[elemName]
        self.stateLock.release()
        
        return returnVal
    
    def triggerAction(self,action):
        
        # dispatch
        self.dispatch(
            signal        = 'cmdToMote',
            data          = {
                                'serialPort':    self.moteConnector.serialport,
                                'action':        action,
                            },
        )
    
    #======================== private =========================================
    
    def _receivedStatus_notif(self,data):
        
        # log
        if log.isEnabledFor(logging.DEBUG):
            log.debug("received {0}".format(data))
        
        # lock the state data
        self.stateLock.acquire()

        # call handler
        found = False
        for k,v in self.notifHandlers.items():
            if self._isnamedtupleinstance(data,k):
                found = True
                try:
                    moteInfo = self.state[self.ST_IDMANAGER].get_info()
                except:
                    moteInfo = ''
                v((moteInfo, data))
                break
        
        # unlock the state data
        self.stateLock.release()
        
        if not found:
            raise SystemError("No handler for data {0}".format(data))
    
    def _isnamedtupleinstance(self,var,tupleInstance):
        return var._fields==tupleInstance._fields

    def _getDutyCycle(self, sender, signal, data):

        # source
        source = self.state[self.ST_IDMANAGER].get_info()
        # get last duty cycle measurement
        dutyCycle = self.state[self.ST_MACSTATS].getDutyCycle()
        # asn of the dutyCycle measurement is an approximation as the exact timestamp is not available
        timestamp = self.state[self.ST_ASN].getAsn()
        if timestamp:
            timestamp = str(timestamp)
        else:
            timestamp = '0'

        if source and dutyCycle and timestamp:
            data = {
                'source'    : source['64bAddr'],
                'timestamp' : timestamp,
                'dutyCycle' : dutyCycle,
            }

            # dispatch
            self.dispatch('dutyCycleMeasurement', data)
