import json
import time
from abc import ABCMeta

from openvisualizer.motehandler.motestate.opentype import TypeAsn, OpenType, TypeCellType, TypeAddr, TypeComponent, \
    TypeRssi


class StateElem(object):
    """ Abstract superclass for internal mote state classes. """
    __metaclass__ = ABCMeta

    def __init__(self):
        self.meta = [{}]
        self.data = []

        self.meta[0]['numUpdates'] = 0
        self.meta[0]['lastUpdated'] = None

    # ======================== public ==========================================

    def update(self):
        self.meta[0]['lastUpdated'] = time.time()
        self.meta[0]['numUpdates'] += 1

    def to_json(self, aspect='all', is_pretty_print=False):
        """
        Dumps state to JSON.

        :param aspect:
               The particular aspect of the state object to dump, or the
               default 'all' for all aspects. Aspect names:
               'meta' -- Metadata collected about the state;
               'data' -- State data itself
        :param is_pretty_print:
               If evaluates true, provides more readable output by sorting
               keys and indenting members.
        :returns: JSON representing the object. If aspect is 'all',
                the JSON is a dictionary, with sub-dictionaries
                for the meta and data aspects. Otherwise, the JSON
                is a list of the selected aspect's content.
        """

        if aspect == 'all':
            content = self._to_dict()
        elif aspect == 'data':
            content = self._elem_to_dict(self.data)
        elif aspect == 'meta':
            content = self._elem_to_dict(self.meta)
        else:
            raise ValueError('No aspect named {0}'.format(aspect))

        return json.dumps(content, sort_keys=bool(is_pretty_print), indent=4 if is_pretty_print else None)

    def __str__(self):
        return self.to_json(is_pretty_print=True)

    # ======================== private =========================================

    def _to_dict(self):
        return_val = {'meta': StateElem._elem_to_dict(self.meta), 'data': StateElem._elem_to_dict(self.data)}
        return return_val

    @classmethod
    def _elem_to_dict(cls, elem):
        return_val = []
        for row_num in range(len(elem)):
            if isinstance(elem[row_num], dict):
                return_val.append({})
                for k, v in elem[row_num].items():
                    if isinstance(v, (list, tuple)):
                        return_val[-1][k] = [m._to_dict() for m in v]
                    else:
                        if isinstance(v, OpenType):
                            return_val[-1][k] = str(v)
                        elif isinstance(v, type):
                            return_val[-1][k] = v.__name__
                        else:
                            return_val[-1][k] = v
            elif isinstance(elem[row_num], StateElem):
                parsed_row = elem[row_num]._to_dict()
                assert ('data' in parsed_row)
                assert (len(parsed_row['data']) < 2)
                if len(parsed_row['data']) == 1:
                    return_val.append(parsed_row['data'][0])
            else:
                raise SystemError("can not parse elem of type {0}".format(type(elem[row_num])))
        return return_val


class StateOutputBuffer(StateElem):
    def update(self, notif=None, creator=None, owner=None):
        super(StateOutputBuffer, self).update()

        assert notif

        if len(self.data) == 0:
            self.data.append({})

        self.data[0]['index_write'] = notif.index_write
        self.data[0]['index_read'] = notif.index_read


class StateAsn(StateElem):
    def update(self, notif=None, creator=None, owner=None):
        super(StateAsn, self).update()

        assert notif

        if len(self.data) == 0:
            self.data.append({})
        if 'asn' not in self.data[0]:
            self.data[0]['asn'] = TypeAsn()

        self.data[0]['asn'].update(notif.asn_0_1, notif.asn_2_3, notif.asn_4)


class StateJoined(StateElem):
    def update(self, notif=None, creator=None, owner=None):
        super(StateJoined, self).update()

        assert notif

        if len(self.data) == 0:
            self.data.append({})
        if 'joinedAsn' not in self.data[0]:
            self.data[0]['joinedAsn'] = TypeAsn()

        self.data[0]['joinedAsn'].update(notif.joinedAsn_0_1, notif.joinedAsn_2_3, notif.joinedAsn_4)


class StateMacStats(StateElem):
    def update(self, notif=None, creator=None, owner=None):
        super(StateMacStats, self).update()

        assert notif

        if len(self.data) == 0:
            self.data.append({})

        self.data[0]['numSyncPkt'] = notif.numSyncPkt
        self.data[0]['numSyncAck'] = notif.numSyncAck
        self.data[0]['minCorrection'] = notif.minCorrection
        self.data[0]['maxCorrection'] = notif.maxCorrection
        self.data[0]['numDeSync'] = notif.numDeSync

        if notif.numTicsTotal != 0:
            duty_cycle = (float(notif.numTicsOn) / float(notif.numTicsTotal)) * 100
            self.data[0]['dutyCycle'] = '{0:.02f}%'.format(duty_cycle)
        else:
            self.data[0]['dutyCycle'] = '?'


class StateScheduleRow(StateElem):
    def update(self, notif=None, creator=None, owner=None):
        super(StateScheduleRow, self).update()

        assert notif

        if len(self.data) == 0:
            self.data.append({})

        self.data[0]['slotOffset'] = notif.slotOffset

        if 'type' not in self.data[0]:
            self.data[0]['type'] = TypeCellType()

        self.data[0]['type'].update(notif.type)
        self.data[0]['shared'] = notif.shared
        self.data[0]['channelOffset'] = notif.channelOffset

        if 'neighbor' not in self.data[0]:
            self.data[0]['neighbor'] = TypeAddr()

        self.data[0]['neighbor'].update(notif.neighbor_type, notif.neighbor_bodyH, notif.neighbor_bodyL)
        self.data[0]['numRx'] = notif.numRx
        self.data[0]['numTx'] = notif.numTx
        self.data[0]['numTxACK'] = notif.numTxACK

        if 'lastUsedAsn' not in self.data[0]:
            self.data[0]['lastUsedAsn'] = TypeAsn()

        self.data[0]['lastUsedAsn'].update(notif.lastUsedAsn_0_1, notif.lastUsedAsn_2_3, notif.lastUsedAsn_4)


class StateBackoff(StateElem):
    def update(self, notif=None, creator=None, owner=None):
        super(StateBackoff, self).update()

        assert notif

        if len(self.data) == 0:
            self.data.append({})

        self.data[0]['backoffExponent'] = notif.backoffExponent
        self.data[0]['backoff'] = notif.backoff


class StateQueueRow(StateElem):
    def update(self, notif=None, creator=None, owner=None):
        super(StateQueueRow, self).update()

        if len(self.data) == 0:
            self.data.append({})

        if 'creator' not in self.data[0]:
            self.data[0]['creator'] = TypeComponent()
        self.data[0]['creator'].update(creator)
        if 'owner' not in self.data[0]:
            self.data[0]['owner'] = TypeComponent()
        self.data[0]['owner'].update(owner)


class StateQueue(StateElem):

    def __init__(self):
        super(StateQueue, self).__init__()

        for i in range(20):
            self.data.append(StateQueueRow())

    def update(self, notif=None, creator=None, owner=None):
        super(StateQueue, self).update()

        assert notif

        self.data[0].update(notif.creator_0, notif.owner_0)
        self.data[1].update(notif.creator_1, notif.owner_1)
        self.data[2].update(notif.creator_2, notif.owner_2)
        self.data[3].update(notif.creator_3, notif.owner_3)
        self.data[4].update(notif.creator_4, notif.owner_4)
        self.data[5].update(notif.creator_5, notif.owner_5)
        self.data[6].update(notif.creator_6, notif.owner_6)
        self.data[7].update(notif.creator_7, notif.owner_7)
        self.data[8].update(notif.creator_8, notif.owner_8)
        self.data[9].update(notif.creator_9, notif.owner_9)
        self.data[10].update(notif.creator_10, notif.owner_10)
        self.data[11].update(notif.creator_11, notif.owner_11)
        self.data[12].update(notif.creator_12, notif.owner_12)
        self.data[13].update(notif.creator_13, notif.owner_13)
        self.data[14].update(notif.creator_14, notif.owner_14)
        self.data[15].update(notif.creator_15, notif.owner_15)
        self.data[16].update(notif.creator_16, notif.owner_16)
        self.data[17].update(notif.creator_17, notif.owner_17)
        self.data[18].update(notif.creator_18, notif.owner_18)
        self.data[19].update(notif.creator_19, notif.owner_19)


class StateNeighborsRow(StateElem):
    def update(self, notif=None, creator=None, owner=None):
        super(StateNeighborsRow, self).update()

        assert notif

        if len(self.data) == 0:
            self.data.append({})
        self.data[0]['used'] = notif.used
        self.data[0]['insecure'] = notif.insecure
        self.data[0]['parentPreference'] = notif.parentPreference
        self.data[0]['stableNeighbor'] = notif.stableNeighbor
        self.data[0]['switchStabilityCounter'] = notif.switchStabilityCounter
        self.data[0]['joinPrio'] = notif.joinPrio

        if 'addr' not in self.data[0]:
            self.data[0]['addr'] = TypeAddr()

        self.data[0]['addr'].update(notif.addr_type, notif.addr_bodyH, notif.addr_bodyL)
        self.data[0]['DAGrank'] = notif.DAGrank

        if 'rssi' not in self.data[0]:
            self.data[0]['rssi'] = TypeRssi()

        self.data[0]['rssi'].update(notif.rssi)
        self.data[0]['numRx'] = notif.numRx
        self.data[0]['numTx'] = notif.numTx
        self.data[0]['numTxACK'] = notif.numTxACK
        self.data[0]['numWraps'] = notif.numWraps

        if 'asn' not in self.data[0]:
            self.data[0]['asn'] = TypeAsn()
        self.data[0]['asn'].update(notif.asn_0_1, notif.asn_2_3, notif.asn_4)

        self.data[0]['f6PNORES'] = notif.f6PNORES
        self.data[0]['sixtopSeqNum'] = notif.sixtopSeqNum
        self.data[0]['backoffExponent'] = notif.backoffExponent
        self.data[0]['backoff'] = notif.backoff


class StateIsSync(StateElem):
    def update(self, notif=None, creator=None, owner=None):
        super(StateIsSync, self).update()

        assert notif

        if len(self.data) == 0:
            self.data.append({})

        self.data[0]['isSync'] = notif.isSync


class StateIdManager(StateElem):

    def __init__(self, event_bus_client, mote_connector):
        super(StateIdManager, self).__init__()
        self.ebc = event_bus_client
        self.mote_connector = mote_connector
        self.is_dagroot = None

    def get_16b_addr(self):
        try:
            return self.data[0]['my16bID'].addr[:]
        except IndexError:
            return None

    def update(self, notif=None, creator=None, owner=None):
        super(StateIdManager, self).update()

        assert notif

        # update state
        if len(self.data) == 0:
            self.data.append({})

        self.data[0]['isDAGroot'] = notif.isDAGroot

        if 'myPANID' not in self.data[0]:
            self.data[0]['myPANID'] = TypeAddr()
            self.data[0]['myPANID'].desc = 'panId'

        self.data[0]['myPANID'].addr = [notif.myPANID_0, notif.myPANID_1]

        if 'my16bID' not in self.data[0]:
            self.data[0]['my16bID'] = TypeAddr()
            self.data[0]['my16bID'].desc = '16b'

        self.data[0]['my16bID'].addr = [notif.my16bID_0, notif.my16bID_1]

        if 'my64bID' not in self.data[0]:
            self.data[0]['my64bID'] = TypeAddr()
            self.data[0]['my64bID'].desc = '64b'

        self.data[0]['my64bID'].addr = [
            notif.my64bID_0,
            notif.my64bID_1,
            notif.my64bID_2,
            notif.my64bID_3,
            notif.my64bID_4,
            notif.my64bID_5,
            notif.my64bID_6,
            notif.my64bID_7
        ]

        if 'myPrefix' not in self.data[0]:
            self.data[0]['myPrefix'] = TypeAddr()
            self.data[0]['myPrefix'].desc = 'prefix'

        self.data[0]['myPrefix'].addr = [
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
        if self.is_dagroot != self.data[0]['isDAGroot']:
            # dispatch
            self.ebc.dispatch(
                signal='infoDagRoot',
                data={
                    'isDAGroot': self.data[0]['isDAGroot'],
                    'eui64': self.data[0]['my64bID'].addr,
                    'serialPort': self.mote_connector.serialport,
                },
            )

        # record is_dagroot
        self.is_dagroot = self.data[0]['isDAGroot']


class StateMyDagRank(StateElem):
    def update(self, notif=None, creator=None, owner=None):
        super(StateMyDagRank, self).update()

        assert notif

        if len(self.data) == 0:
            self.data.append({})
        self.data[0]['myDAGrank'] = notif.myDAGrank


class StateKaPeriod(StateElem):
    def update(self, notif=None, creator=None, owner=None):
        super(StateKaPeriod, self).update()

        assert notif

        if len(self.data) == 0:
            self.data.append({})
        self.data[0]['kaPeriod'] = notif.kaPeriod


class StateTable(StateElem):
    def __init__(self, row_class, column_order=None):
        super(StateTable, self).__init__()

        self.meta[0]['row_class'] = row_class

        if column_order:
            self.meta[0]['column_order'] = column_order

        self.data = []

    def update(self, notif=None, creator=None, owner=None):
        super(StateTable, self).update()

        assert notif

        while len(self.data) < notif.row + 1:
            self.data.append(self.meta[0]['row_class']())
        self.data[notif.row].update(notif)
