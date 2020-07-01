# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import json
import logging
import struct
import threading

import paho.mqtt.client as mqtt

from openvisualizer.motehandler.moteconnector.openparser import parser

log = logging.getLogger('ParserData')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


class ParserData(parser.Parser):
    HEADER_LENGTH = 2

    UINJECT_MASK = 'uinject'

    def __init__(self, mqtt_broker_address, mote_port):

        # log
        log.debug("create instance")

        # initialize parent class
        super(ParserData, self).__init__(self.HEADER_LENGTH)

        self._asn = [
            'asn_4',  # B
            'asn_2_3',  # H
            'asn_0_1',  # H
        ]

        self.avg_kpi = {}

        self.mote_port = mote_port
        self.broker = mqtt_broker_address
        self.mqtt_connected = False

        if self.broker:

            # connect to MQTT
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self._on_mqtt_connect

            try:
                self.mqtt_client.connect(self.broker)
            except Exception as e:
                log.error("failed to connect to {} with error msg: {}".format(self.broker, e))
            else:
                # start mqtt client
                self.mqtt_thread = threading.Thread(name='mqtt_loop_thread', target=self.mqtt_client.loop_forever)
                self.mqtt_thread.start()

    # ======================== private =========================================

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        log.success("connected to broker ({}) for mote on port: {}".format(self.broker, self.mote_port))

        self.mqtt_connected = True

    # ======================== public ==========================================

    def parse_input(self, data):
        # log
        log.debug("received data {0}".format(data))

        # ensure data not short longer than header
        self._check_length(data)

        _ = data[:2]  # header bytes
        # asn comes in the next 5bytes.

        asn_bytes = data[2:7]
        (self._asn) = struct.unpack('<BHH', ''.join([chr(c) for c in asn_bytes]))

        # source and destination of the message
        dest = data[7:15]

        # source is elided!!! so it is not there.. check that.
        source = data[15:23]

        log.debug("destination address of the packet is {0} ".format("".join(hex(c) for c in dest)))
        log.debug("source address (just previous hop) of the packet is {0} ".format("".join(hex(c) for c in source)))

        # remove asn src and dest and mote id at the beginning.
        # this is a hack for latency measurements... TODO, move latency to an app listening on the corresponding port.
        # inject end_asn into the packet as well
        data = data[23:]

        log.debug("packet without source, dest and asn {0}".format(data))

        # when the packet goes to internet it comes with the asn at the beginning as timestamp.

        # cross layer trick here. capture UDP packet from udpLatency and get ASN to compute latency.
        offset = 0
        if len(data) > 37:
            offset -= 7
            if self.UINJECT_MASK == ''.join(chr(i) for i in data[offset:]):

                pkt_info = \
                    {
                        'asn': 0,
                        'src_id': None,
                        'counter': 0,
                        'latency': 0,
                        'numCellsUsedTx': 0,
                        'numCellsUsedRx': 0,
                        'dutyCycle': 0,
                    }

                offset -= 2
                pkt_info['counter'] = data[offset - 2] + 256 * data[offset - 1]  # counter sent by mote

                pkt_info['asn'] = struct.unpack('<I', ''.join([chr(c) for c in data[offset - 5:offset - 1]]))[0]
                aux = data[offset - 5:offset]  # last 5 bytes of the packet are the ASN in the UDP latency packet
                diff = ParserData._asn_diference(aux, asn_bytes)  # calculate difference
                pkt_info['latency'] = diff  # compute time in slots
                offset -= 5

                pkt_info['numCellsUsedTx'] = data[offset - 1]
                offset -= 1

                pkt_info['numCellsUsedRx'] = data[offset - 1]
                offset -= 1

                pkt_info['src_id'] = ''.join(['%02x' % x for x in [data[offset - 1], data[offset - 2]]])  # mote id
                src_id = pkt_info['src_id']
                offset -= 2

                num_ticks_on = struct.unpack('<I', ''.join([chr(c) for c in data[offset - 4:offset]]))[0]
                offset -= 4

                num_ticks_in_total = struct.unpack('<I', ''.join([chr(c) for c in data[offset - 4:offset]]))[0]
                offset -= 4

                pkt_info['dutyCycle'] = float(num_ticks_on) / float(num_ticks_in_total)  # duty cycle

                # self.avg_kpi:
                if src_id in self.avg_kpi:
                    self.avg_kpi[src_id]['counter'].append(pkt_info['counter'])
                    self.avg_kpi[src_id]['latency'].append(pkt_info['latency'])
                    self.avg_kpi[src_id]['numCellsUsedTx'].append(pkt_info['numCellsUsedTx'])
                    self.avg_kpi[src_id]['numCellsUsedRx'].append(pkt_info['numCellsUsedRx'])
                    self.avg_kpi[src_id]['dutyCycle'].append(pkt_info['dutyCycle'])
                else:
                    self.avg_kpi[src_id] = {
                        'counter': [pkt_info['counter']],
                        'latency': [pkt_info['latency']],
                        'numCellsUsedTx': [pkt_info['numCellsUsedTx']],
                        'numCellsUsedRx': [pkt_info['numCellsUsedRx']],
                        'dutyCycle': [pkt_info['dutyCycle']],
                        'avg_cellsUsage': 0.0,
                        'avg_latency': 0.0,
                        'avg_pdr': 0.0,
                    }

                if self.mqtt_connected:
                    self.publish_kpi(src_id)

                # in case we want to send the computed time to internet..
                # computed=struct.pack('<H', timeinus)#to be appended to the pkt
                # for x in computed:
                # data.append(x)
            else:
                # no udplatency
                # print data
                pass
        else:
            pass

        event_type = 'data'
        # notify a tuple including source as one hop away nodes elide SRC address as can be inferred from MAC layer
        # header
        return event_type, (source, data)

    # ======================== private =========================================

    @staticmethod
    def _asn_diference(init, end):

        asn_init = struct.unpack('<HHB', ''.join([chr(c) for c in init]))
        asn_end = struct.unpack('<HHB', ''.join([chr(c) for c in end]))
        if asn_end[2] != asn_init[2]:  # 'byte4'
            return 0xFFFFFFFF
        else:
            pass

        return 0x10000 * (asn_end[1] - asn_init[1]) + (asn_end[0] - asn_init[0])

    # ========================== mqtt publish ====================================

    def publish_kpi(self, src_id):

        payload = {'token': 123}

        mote_data = self.avg_kpi[src_id]

        self.avg_kpi[src_id]['avg_cellsUsage'] = \
            float(sum(mote_data['numCellsUsedTx']) / len(mote_data['numCellsUsedTx'])) / float(64)

        self.avg_kpi[src_id]['avg_latency'] = \
            sum(self.avg_kpi[src_id]['latency']) / len(self.avg_kpi[src_id]['latency'])

        mote_data['counter'].sort()  # sort the counter before calculating

        self.avg_kpi[src_id]['avg_pdr'] = \
            float(len(set(mote_data['counter']))) / float(1 + mote_data['counter'][-1] - mote_data['counter'][0])

        avg_pdr_all = 0.0
        avg_latency_all = 0.0
        avg_num_cells_usage_all = 0.0

        for mote, data in self.avg_kpi.items():
            avg_pdr_all += data['avg_pdr']
            avg_latency_all += data['avg_latency']
            avg_num_cells_usage_all += data['avg_cellsUsage']

        num_motes = len(self.avg_kpi)
        avg_pdr_all = avg_pdr_all / float(num_motes)
        avg_latency_all = avg_latency_all / float(num_motes)
        avg_num_cells_usage_all = avg_num_cells_usage_all / float(num_motes)

        payload['avg_cellsUsage'] = avg_num_cells_usage_all
        payload['avg_latency'] = avg_latency_all
        payload['avg_pdr'] = avg_pdr_all
        payload['src_id'] = src_id

        if self.mqtt_connected:
            # publish the cmd message
            self.mqtt_client.publish(topic='opentestbed/uinject/arrived', payload=json.dumps(payload), qos=2)
