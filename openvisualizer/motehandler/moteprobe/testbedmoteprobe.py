# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import Queue
import json
import logging
import time

import paho.mqtt.client as mqtt

from moteprobe import MoteProbe

log = logging.getLogger('MoteProbe')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


# ============================ functions ===============================


# ============================ class ===================================

class OpentestbedMoteProbe(MoteProbe):
    BASE_TOPIC = 'opentestbed/deviceType/mote/deviceId'

    def __init__(self, mqtt_broker, testbedmote_eui64):
        self.mqtt_broker = mqtt_broker
        self.testbedmote_eui64 = testbedmote_eui64

        # mqtt client
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.connect(self.mqtt_broker)
        # self.mqtt_client.on_log = self.log_cb

        name = 'opentestbed_{0}'.format(testbedmote_eui64)
        # initialize the parent class
        MoteProbe.__init__(self, portname=name, daemon=True)

    @property
    def serial(self):
        return None

    @staticmethod
    def log_cb(client, userdata, level, buf):
        _, _, _ = client, userdata, level
        log.info(buf)

    # ======================== private =================================

    def _send_data(self, data):
        hdlc_data = self.hdlc.hdlcify(data)
        payload_buffer = {'token': 123, 'serialbytes': [ord(i) for i in hdlc_data]}

        # publish the cmd message
        self.mqtt_client.publish(
            topic='{}/{}/cmd/tomoteserialbytes'.format(self.BASE_TOPIC, self.testbedmote_eui64),
            payload=json.dumps(payload_buffer),
        )

    def _rcv_data(self):
        rx_bytes = self.mqtt_serial_queue.get()
        return [chr(i) for i in rx_bytes]

    def _detach(self):
        pass

    def _attach(self):
        # create queue for receiving serialbytes messages
        self.serialbytes_queue = Queue.Queue(maxsize=10)

        self.mqtt_client.loop_start()

        self.mqtt_serial_queue = self.serialbytes_queue

    # ==== mqtt callback functions =====================================

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        client.subscribe('{}/{}/notif/frommoteserialbytes'.format(self.BASE_TOPIC, self.testbedmote_eui64))

    def _on_mqtt_message(self, client, userdata, message):
        try:
            serial_bytes = json.loads(message.payload)['serialbytes']
        except json.JSONDecodeError:
            log.error("failed to parse message payload {}".format(message.payload))
        else:
            try:
                self.serialbytes_queue.put(serial_bytes, block=False)
            except Queue.Full:
                log.warning("queue overflow/full")


# ============================ class ===========================================

class OpentestbedMoteFinder(object):
    OPENTESTBED_RESP_STATUS_TIMEOUT = 10

    def __init__(self, mqtt_broker):
        self.opentestbed_motelist = set()
        self.mqtt_broker = mqtt_broker

        # create mqtt client
        self.mqtt_client = mqtt.Client('FindMotes')
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.connect(self.mqtt_broker)
        # self.mqtt_client.on_log = log_cb

    def get_opentestbed_motelist(self):
        # start the mqtt client
        self.mqtt_client.loop_start()

        # wait for a while to gather the response from otboxes
        log.info("discovering motes in testbed... (waiting for {}s)".format(self.OPENTESTBED_RESP_STATUS_TIMEOUT))
        time.sleep(self.OPENTESTBED_RESP_STATUS_TIMEOUT)

        # close the client and return the motes list
        self.mqtt_client.loop_stop()

        log.info("discovered {0} motes".format(len(self.opentestbed_motelist)))

        return self.opentestbed_motelist

    @staticmethod
    def log_cb(client, userdata, level, buf):
        log.info(buf)

    def _on_mqtt_connect(self, client, userdata, flags, rc):

        log.success("connected to broker: {0}".format(self.mqtt_broker))

        client.subscribe('opentestbed/deviceType/box/deviceId/+/resp/status')

        payload_status = {'token': 123}
        # publish the cmd message
        client.publish(topic='opentestbed/deviceType/box/deviceId/all/cmd/status', payload=json.dumps(payload_status))

    def _on_mqtt_message(self, client, userdata, message):

        # get the motes list from payload
        payload_status = json.loads(message.payload)

        for mote in payload_status['returnVal']['motes']:
            if 'EUI64' in mote:
                self.opentestbed_motelist.add(mote['EUI64'])
