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
import traceback

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
    OPENBENCHMARK_PREFIX_CMD_HANDLER_NAME = '_mqtt_handler_'

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
        self.mqttConnectedEvent = threading.Event()
        self.experimentRequestResponseEvent = threading.Event()

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
        try:
            # mqtt client
            self.mqttClient = mqtt.Client('openBenchmarkAgent')
            self.mqttClient.on_connect = self._on_mqtt_connect
            self.mqttClient.on_message = self._on_mqtt_message
            self.mqttClient.connect(self.mqttBroker)
            self.mqttClient.loop_start()

            # block until client is connected, or give up after 60 seconds
            self.mqttConnectedEvent.wait(60)

            self.experimentId = self._openbenchmark_start_benchmark(self.mqttClient)

            assert self.experimentId

            # subscribe to all topics on a given experiment ID
            self._openbenchmark_subscribe(self.mqttClient, self.experimentId)

            # subscribe to eventBus events
            eventBusClient.eventBusClient.__init__(
                self,
                name='openBenchmarkAgent',
                registrations=[
                ]
            )

            log.info("Experiment #{0} successfuly started".format(self.experimentId))

        except Exception as e:
            log.exception(e)
            log.info("Experiment start failed, giving up.")
            self.close()

    # ======================== public ==========================================

    def close(self):
        self.mqttClient.loop_stop()

    # ======================== private =========================================

    def _openbenchmark_start_benchmark(self, mqttClient):
        '''
        :param mqttClient: paho MQTT client object to use to issue startBenchmark request
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

                # block until response is received, or give up after the timeout
                self.experimentRequestResponseEvent.wait(self.OPENBENCHMARK_RESP_STATUS_TIMEOUT)

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
                log.exception(str(e) + ", retrying...")
                attempt += 1
                self.experimentRequestResponseEvent.clear()
                self.experimentRequestResponse = None
                continue

        mqttClient.unsubscribe(self.OPENBENCHMARK_STARTBENCHMARK_RESPONSE_TOPIC)

        return experimentId

    def _openbenchmark_subscribe(self, mqttClient, experimentId):
            mqttClient.subscribe("openbenchmark/experimentId/{0}/command/#".format(experimentId))

    # command handling adapted from github.com/openwsn-berkeley/opentestbed
    def _execute_command_safely(self, topic, payload):
        # parse the topic to extract deviceType, deviceId and cmd ([0-9\-]+)
        try:
            m = re.search("openbenchmark/experimentId/{0}/command/([a-z]+)".format(self.experimentId), topic)
            assert m, "Invalid topic, could not parse: '{0}'".format(topic)

            cmd  = m.group(1)

            log.debug("Executing command %s", cmd)
            returnVal = {}

            payload = payload.decode('utf8')
            assert payload, "Could not decode payload"

            tokenReceived = json.loads(payload)['token']

            # Executes the handler of a command in a try/except environment so exception doesn't crash server.
            try:
                # find the handler
                cmd_handler = getattr(self, '{0}{1}'.format(self.OPENBENCHMARK_PREFIX_CMD_HANDLER_NAME, cmd), None)

                assert cmd_handler, "Unhandled command, ignoring: {0}".format(cmd)

                # call the handler to return dictionary with handler-specific fields in the response
                # handler return is in format (success, dict), with:
                #   - success, as a boolean
                #   - dict, dictionary containing fields to include in the response or None on failure
                (success, dict) = cmd_handler(payload)

            except Exception as err:
                log.exception("Exception while executing {0}".format(cmd))
                log.exception(err)
                log.exception(traceback.format_exc())

                returnVal = {
                    'success': False,
                }

            else:
                # update the returnVal dict with handler-specific fields
                if success:
                    returnVal.update(dict)
                returnVal['success'] = success

            finally:
                # echo the token
                returnVal['token'] = tokenReceived

                self.mqttClient.publish(
                    topic='openbenchmark/experimentId/{0}/response/{1}'.format(self.experimentId, cmd),
                    payload=json.dumps(returnVal),
                )

        except Exception as e:
            log.exception(e)

    # ==== mqtt callback functions

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        # signal to the other thread that we are connected
        self.mqttConnectedEvent.set()

    def _on_mqtt_message(self, client, userdata, message):
        # check if this is the startBenchmark response
        if message.topic is self.OPENBENCHMARK_STARTBENCHMARK_RESPONSE_TOPIC:
            self.experimentRequestResponse = message.payload
            self.experimentRequestResponseEvent.set()
        # if not, assume this is a command
        else:
            self._execute_command_safely(message.topic, message.payload)

    # ==== mqtt command handlers

    def _mqtt_handler_echo(self, payload):
        returnVal = {}
        return (True, returnVal)

    def _mqtt_handler_sendPacket(self, payload):
        returnVal = {}

        # parse the payload
        payloadDecoded = json.loads(payload)

        source        = payloadDecoded['source']
        destination   = payloadDecoded['destination']
        packetToken   = payloadDecoded['packetToken']
        packetPayload = payloadDecoded['packetPayload']
        confirmable   = payloadDecoded['confirmable']

        # TODO lookup corresponding mote probe
        # TODO generate an eventbus signal to send a command over serial

        return (True, returnVal)

    def _mqtt_handler_configureTransmitPower(self, payload):
        returnVal = {}

        # parse the payload
        payloadDecoded = json.loads(payload)

        source        = payloadDecoded['source']
        power         = payload.Decoded['power']

        # TODO lookup corresponding mote probe
        # TODO generate an eventbus signal to send a command over serial

        return (True, returnVal)
