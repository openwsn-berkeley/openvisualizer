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
import paho.mqtt.client as mqtt
from time import gmtime, strftime

log = logging.getLogger('openBenchmarkAgent')
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())

from openvisualizer.eventBus      import eventBusClient

# a special logger that writes to a separate file: each log line is a JSON string corresponding to network events
# with information sufficient to calculate network-wide KPIs
networkEventLogger = logging.getLogger('networkEventLogger')
networkEventLogger.setLevel(logging.INFO)

OPENBENCHMARK_API_VERSION = "0.0.1"

class OpenBenchmarkAgent(eventBusClient.eventBusClient):

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
        self.experimentId = None

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
            '\n    '.join(['mqttBroker         = {0}'.format(self.mqttBroker),
                           'firmware            = {0}'.format(self.firmware),
                           'testbed       = {0}'.format(self.testbed),
                           'portNames          = {0}'.format(self.portNames),
                           'scenario          = {0}'.format(self.scenario),
                           'nodes           = {0}'.format(self.nodes)]
                          )))

        # mqtt client
        self.mqttclient = mqtt.Client('openBenchmarkAgent')
        self.mqttclient.on_connect = self._on_mqtt_connect
        self.mqttclient.on_message = self._on_mqtt_message
        self.mqttclient.connect(self.mqttBroker)
        self.mqttclient.loop_start()

        # initialize parent class
        eventBusClient.eventBusClient.__init__(
            self,
            name='openBenchmarkAgent',
            registrations=[
            ]
        )

    # ======================== public ==========================================

    # ======================== private =========================================

    # ==== mqtt callback functions

    def _on_mqtt_connect(self, client, userdata, flags, rc):

        # TODO send startBenchmark command

        payload = {
            'api_version'        :      OPENBENCHMARK_API_VERSION,
            'token'              :      123,
            'date'               :      strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()),
            'firmware'           :      self.firmware,
            'testbed'            :      self.testbed,
            'nodes'              :      self.nodes,
            'scenario'           :      self.scenario
        }

        client.publish(
            topic   = 'openbenchmark/command/startBenchmark'.format(self.testbed),
            payload = json.dumps(payload),
        )

        # TODO add timeout and parse response in on_message
        # TODO start the network
        # FIXME what to do with DAg root

        # TODO subscribe to all topics with a given experimentId
        client.subscribe(
            'openbenchmark/experimentId/{0}/#'.format(self.experimentId))

    def _on_mqtt_message(self, client, userdata, message):
        pass