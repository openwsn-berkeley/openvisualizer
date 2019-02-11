# Copyright (c) 2019, Inria.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
'''
Implements the OpenBenchmark Agent component needed to automatically benchmark the implementation in a testbed.
OpenBenchmark APIs are specified at https://benchmark.6tis.ch/docs
'''

import logging
import json
import re
import time
import os
import binascii
import paho.mqtt.client as mqtt
from time import gmtime, strftime

import threading

log = logging.getLogger('openBenchmarkAgent')
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())

from openvisualizer.eventBus      import eventBusClient

# a special logger that writes to a separate file: each log line is a JSON string corresponding to network events
# with information sufficient to calculate network-wide KPIs
networkEventLogger = logging.getLogger('networkEventLogger')
networkEventLogger.setLevel(logging.INFO)

class OpenBenchmarkAgent(eventBusClient.eventBusClient):

    OPENBENCHMARK_API_VERSION            = '0.0.1'

    # MQTT topics
    OPENBENCHMARK_STARTBENCHMARK_REQUEST_TOPIC = 'openbenchmark/command/startBenchmark'
    OPENBENCHMARK_STARTBENCHMARK_RESPONSE_TOPIC = 'openbenchmark/response/startBenchmark'

    OPENBENCHMARK_RESP_STATUS_TIMEOUT    = 10
    OPENBENCHMARK_MAX_RETRIES            = 3

    def __init__(self, mqttBroker, firmware, testbed, portNames, scenario):
        '''
        :param mqttBroker:
            Address of the MQTT broker where to connect with OpenBenchmark
        :param firmware:
            Local identifier of the firmware
        :param testbed:
            Identifier of the testbed, 'simulation' for OV in simulation mode, or 'local' for OV with locally-connected
            motes
        :param portNames:
            List of port names. If the mote is in testbed, expects 'testbed_{{TESTBED}}_{{HOST}}_{{EUI-64}},
            where {{TESTBED}} is the testbed identifier, {{HOST}} is the identifier of the remote machine in the testbed
            where the mote is connected to, and {{EUI-64}} is the EUI-64 address of the mote.
        :param scenario:
            Identifier of the requested scenario to benchmark the performance.
        '''

        # store params
        self.mqttBroker = mqttBroker
        self.firmware = firmware
        self.testbed = testbed
        self.portNames = portNames
        self.scenario = scenario

        # state
        self.experimentId = None

        # sync primitive for mutual exclusion
        self.resourceLockEvent = threading.Event()

        self.mqttClient = None
        self.experimentRequestResponse = None
        self.nodes = []

        # OV is running in simulation mode
        if self.testbed is 'simulation':
            for port in portNames:
                self.nodes += ('simulation', port)
        # Motes are attached locally on the physical port
        elif self.testbed is 'local':
            for port in portNames:
                self.nodes += ('local', port)
        # General case, motes are in testbed connected over OpenTestbed software
        else:
            for port in portNames:
                m = re.search('testbed_(.+)_(.+)_(.+)', port)
                if m:
                    # (testbed_host, eui64)
                    assert m.group(1) == self.testbed
                    self.nodes += (m.group(2), m.group(3))

        log.info('Initializing OpenBenchmark with options:\n\t{0}'.format(
            '\n    '.join(['mqttBroker          = {0}'.format(self.mqttBroker),
                           'firmware            = {0}'.format(self.firmware),
                           'testbed             = {0}'.format(self.testbed),
                           'portNames           = {0}'.format(self.portNames),
                           'scenario            = {0}'.format(self.scenario),
                           'nodes               = {0}'.format(self.nodes)]
                          )))

        # mqtt client
        self.mqttClient = mqtt.Client('openBenchmarkAgent')
        self.mqttClient.on_connect = self._on_mqtt_connect
        self.mqttClient.on_message = self._on_mqtt_message
        self.mqttClient.connect(self.mqttBroker)
        self.mqttClient.loop_start()

        # block until client is connected, or give up after 60 seconds
        self.resourceLockEvent.wait(60)

        self.experimentId = self._openbenchmark_start_benchmark(self.mqttClient)

        # subscribe to eventBus events only if startBenchmark was successful
        if self.experimentId:

            log.info("Experiment #{0} successfuly started".format(self.experimentId))

            # subscribe to eventBus events
            eventBusClient.eventBusClient.__init__(
                self,
                name='openBenchmarkAgent',
                registrations=[
                ]
            )
        else:
            log.info("Experiment start failed, giving up.")
            self.close()

    # ======================== public ==========================================

    def close(self):
        self.mqttClient.loop_stop()

    # ======================== private =========================================

    def _openbenchmark_start_benchmark(self, mqttClient):
        '''
        :param mqttClient:
            paho MQTT client object to use to issue startBenchmark request
        :returns: Experiment identifier assigned by OpenBenchmark on success, None on failure.
        '''

        # count the number of attempts
        attempt = 0
        experimentId = None

        # generate a random token
        tokenGenerated = binascii.b2a_hex(os.urandom(8))

        payload = {
            'api_version': self.OPENBENCHMARK_API_VERSION,
            'token': tokenGenerated,
            'date': strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()),
            'firmware': self.firmware,
            'testbed': self.testbed,
            'nodes': self.nodes,
            'scenario': self.scenario
        }

        mqttClient.subscribe(self.OPENBENCHMARK_STARTBENCHMARK_RESPONSE_TOPIC)

        while attempt < self.OPENBENCHMARK_MAX_RETRIES:

            try:

                mqttClient.publish(
                    topic=self.OPENBENCHMARK_STARTBENCHMARK_REQUEST_TOPIC,
                    payload=json.dumps(payload),
                )

                # wait for a while to gather the response
                time.sleep(self.OPENBENCHMARK_RESP_STATUS_TIMEOUT)

                # assume response is received
                assert self.experimentRequestResponse, "No response from OpenBenchmark"

                # parse it
                payload = json.loads(self.experimentRequestResponse)
                tokenReceived = payload['token']
                success = payload['success']

                # assume tokens match
                assert tokenGenerated is tokenReceived, "Token does not match"
                # assume success
                assert success is True, "Fail indicated"

                experimentId = payload['experimentId']

            # Retry for all exceptions, including assertions
            except Exception as e:
                log.info(str(e) + ", retrying...")
                attempt += 1
                self.experimentRequestResponse = None
                continue

        mqttClient.unsubscribe(self.OPENBENCHMARK_STARTBENCHMARK_RESPONSE_TOPIC)

        return experimentId

    # ==== mqtt callback functions

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        # signal to the other thread that we are connected
        self.resourceLockEvent.set()

    def _on_mqtt_message(self, client, userdata, message):
        if message.topic is self.OPENBENCHMARK_STARTBENCHMARK_RESPONSE_TOPIC:
            self.experimentRequestResponse = message.payload
        else:
            pass
