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
from openvisualizer.moteState     import moteState
import openvisualizer.openvisualizer_utils

from   coap   import    coap,                    \
                        coapResource,            \
                        coapDefines as d,        \
                        coapOption as o,         \
                        coapUtils as u,          \
                        coapObjectSecurity as oscoap, \
                        coapException as e

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

    def __init__(self, coapServer, mqttBroker, firmware, testbed, portNames, scenario):
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
        self.coapServer = coapServer
        self.mqttBroker = mqttBroker
        self.firmware = firmware
        self.testbed = testbed
        self.portNames = portNames
        self.scenario = scenario

        # primitive for mutual exclusion
        self.mqttConnectedEvent = threading.Event()
        self.experimentRequestResponseEvent = threading.Event()

        # local vars
        self.experimentId = None
        self.mqttClient = None
        self.experimentRequestResponse = None
        self.performanceEvent = None
        self.dagRootEui64 = None

        # dict with keys being eui64, and value corresponding testbed host identifier
        self.nodes = {}

        # OV is running in simulation mode
        if self.testbed is 'simulation':
            for port in portNames:
                self.nodes[port] = 'simulation'
        # Motes are attached locally on the physical port
        elif self.testbed is 'local':
            for port in portNames:
                self.nodes[port] = 'local'
        # General case, motes are in testbed connected over OpenTestbed software
        else:
            for port in portNames:
                m = re.search('testbed_(.+)_(.+)_(.+)', port)
                if m:
                    # (testbed_host, eui64)
                    assert m.group(1) == self.testbed
                    self.nodes[m.group(3)] = m.group(2)

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

            if not self.experimentId:
                raise ValueError("Unable to start an experiment with OpenBenchmark")

            # subscribe to all topics on a given experiment ID
            self._openbenchmark_subscribe(self.mqttClient, self.experimentId)

            # instantiate performance event handlers from firmware
            self.performanceEvent = PerformanceEvent(self.experimentId, self.mqttClient)

            # everything is ok, start a coap server
            self.openbenchmarkResource = OpenbenchmarkResource(self.performanceEvent, self.dagRootEui64)
            self.coapServer.coapServer.addResource(coapResource)

            # subscribe to eventBus performance-related events
            eventBusClient.eventBusClient.__init__(
                self,
                name='openBenchmarkAgent',
                registrations=[
                    {
                        'sender': self.WILDCARD,
                        'signal': 'fromMote.performanceData',
                        'callback': self.performanceEvent.handle_event,
                    },
                ]
            )

            log.info("Experiment #{0} successfuly started".format(self.experimentId))

        except Exception as e:
            log.warning(e)
            self.close()

    # ======================== public ==========================================

    def close(self):
        if self.mqttClient:
            self.mqttClient.loop_stop()
        if self.coapServer:
            self.coapServer.close()
        if self.performanceEvent:
            self.performanceEvent.close()

    def triggerSendPacket(self, destination, acknowledged, packetsInBurst, packetToken, packetPayloadLen):

        destinationIPv6 = openvisualizer.openvisualizer_utils.formatIPv6Addr((self.networkPrefix + destination))
        options = []

        if not acknowledged:
           options += [o.NoResponse([d.DFLT_OPTION_NORESPONSE_SUPRESS_ALL])]

        with self.clientLock:
            for packetCounter in range (0, packetsInBurst):
                try:
                    # construct the payload of the POST request
                    payload = []
                    payload += [0] * packetPayloadLen
                    payload += [packetCounter]
                    payload += [packetToken[1:]]

                    # the call to POST() is blocking unless no response is expected
                    token = [packetCounter] + packetToken[1:]
                    self.performanceEvent.add_outstanding_packet((token, destination, self.coapServer.COAP_SERVER_DEFAULT_IPv6_HOP_LIMIT))

                    log.debug("Publishing on topic: {0} Payload: {1}".format(topic, returnVal))
                    p = self.coapServer.POST('coap://[{0}:{1}]/b'.format(destinationIPv6, d.DEFAULT_UDP_PORT),
                               confirmable=False,
                               options=options,
                               payload = payload)

                    # TODO log if a response is received
                except e.coapNoResponseExpected:
                    pass

    def encodeSendPacketPayload(self, destination, confirmable, packetsInBurst, packetToken, packetPayloadLen):
        # construct command payload as byte-list:
        # dest_eui64 (8B) || con (1B) || packetsInBurst (1B) || packetToken (5B) || packetPayloadLen (1B)
        buf = []
        buf += u.hex2buf(destination, separator='-')
        buf += [int(confirmable)]
        buf += [int(packetsInBurst)]
        buf += packetToken
        buf += [packetPayloadLen]
        return buf

    def updateDagRootEui64(self, address):
        self.dagRootEui64 = address
        self.openbenchmarkResource.dagRootEui64 = self.dagRootEui64

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

                self.experimentRequestResponse = None

                mqttClient.publish(
                    topic=self.OPENBENCHMARK_STARTBENCHMARK_REQUEST_TOPIC,
                    payload=json.dumps(payload),
                )

                # block until response is received, or give up after the timeout
                self.experimentRequestResponseEvent.wait(self.OPENBENCHMARK_RESP_STATUS_TIMEOUT)

                # assume response is received
                if not self.experimentRequestResponse:
                    raise ValueError("No response from OpenBenchmark")

                # parse it
                payload = json.loads(self.experimentRequestResponse)
                tokenReceived = payload['token']
                success = payload['success']

                # check token match
                if tokenGenerated is not tokenReceived:
                    raise ValueError("Token does not match the one sent in the request")
                # success?
                if success is not True:
                    raise ValueError("Fail indicated")

                experimentId = payload['experimentId']

            # Retry for all ValueErrors
            except ValueError as valErr:
                log.info(str(valErr) + ", retrying...")
                attempt += 1
                self.experimentRequestResponseEvent.clear()
                continue
            # give up
            except Exception as e:
                log.warning(e)
                break

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

    # ==== mqtt and event bus callback functions

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

        sourceStr            = payloadDecoded['source']
        source               = u.hex2buf(sourceStr, separator='-')
        destination          = u.hex2buf(payloadDecoded['destination'], separator='-')
        packetsInBurst       = payloadDecoded['packetsInBurst']
        packetToken          = payloadDecoded['packetToken']
        packetPayloadLen     = payloadDecoded['packetPayloadLen']
        acknowledged         = payloadDecoded['confirmable']

        if self.coapServer.getDagRootEui64() == source: # check if command is for the DAG root whose APP code is implemented here
            self.triggerSendPacket(destination, acknowledged, packetsInBurst, packetToken, packetPayloadLen)

        else: # command is for one of the motes in the mesh, send it over the serial

            # lookup corresponding mote port
            destPort = self.nodes[sourceStr]

            # construct command payload as byte-list:
            # dest_eui64 (8B) || con (1B) || packetsInBurst (1B) || packetToken (5B) || packetPayloadLen (1B)
            commandPayload = []
            commandPayload += destination
            commandPayload += [int(acknowledged)]
            commandPayload += [int(packetsInBurst)]
            commandPayload += packetToken
            commandPayload += [packetPayloadLen]

            if len(commandPayload) != 16:
                return False, returnVal

            action = [moteState.moteState.SET_COMMAND, moteState.moteState.COMMAND_SEND_PACKET, commandPayload]
            # generate an eventbus signal to send a command over serial

            # dispatch
            self.dispatch(
                signal        = 'cmdToMote',
                data          = {
                                    'serialPort':    destPort,
                                    'action':        action,
                                },
            )

        return True, returnVal

    def _mqtt_handler_configureTransmitPower(self, payload):
        returnVal = {}

        # parse the payload
        payloadDecoded = json.loads(payload)

        source        = payloadDecoded['source']
        power         = payload.Decoded['power']

        # lookup corresponding mote port
        destPort = self.nodes[source]
        action = [moteState.moteState.SET_COMMAND, moteState.moteState.COMMAND_SET_TX_POWER, power]

        # generate an eventbus signal to send a command over serial

        # dispatch
        self.dispatch(
            signal        = 'cmdToMote',
            data          = {
                                'serialPort':    destPort,
                                'action':        action,
                            },
        )

        return (True, returnVal)

    def _mqtt_handler_triggerNetworkFormation(self, payload):
        returnVal = {}

        # parse the payload
        payloadDecoded      = json.loads(payload)
        source              = payloadDecoded['source']

        # remember DAG root's EUI64
        self.updateDagRootEui64(source)

        # lookup corresponding mote port
        destPort = self.nodes[source]

        # generate an eventbus signal to send a command over serial
        self.dispatch(
            signal='cmdToMote',
            data={
                'serialPort': destPort,
                'action': moteState.moteState.TRIGGER_DAGROOT,
            },
        )

        return (True, returnVal)

# ================= Implementation of Experiments Performance Events API =====================

class PerformanceEvent(object):

    # period for measurement polling
    PERFORMANCE_EVENT_MEASUREMENT_PERIOD              = 3

    # asynchronous event               #name                         #id    #openbenchmark ID
    EV_PACKET_SENT                  = ['packetSent',                  0,    'packetSent'                ]
    EV_PACKET_RECEIVED              = ['packetReceived',              1,    'packetReceived'            ]
    EV_SYNCHRONIZATION_COMPLETED    = ['synchronizationCompleted',    2,    'synchronizationCompleted'  ]
    EV_SECURE_JOIN_COMPLETED        = ['secureJoinCompleted',         3,    'secureJoinCompleted'       ]
    EV_BANDWIDTH_ASSIGNED           = ['bandwidthAssigned',           4,   'bandwidthAssigned'          ]
    EV_PACKET_SENT_DAGROOT          = ['packetSentDagRoot',           5,    'packetSent'                ] # special event to precisely get the ASN when dag root sent a packet
    EV_NETWORK_FORMATION_COMPLETED  = ['networkFormationCompleted',   257,  'networkFormationCompleted' ]

    EV_ASYNC_ALL = [
        EV_PACKET_SENT,
        EV_PACKET_RECEIVED,
        EV_SECURE_JOIN_COMPLETED,
        EV_BANDWIDTH_ASSIGNED,
        EV_SYNCHRONIZATION_COMPLETED,
        EV_PACKET_SENT_DAGROOT,
        EV_NETWORK_FORMATION_COMPLETED,
    ]

    PERFORMANCE_EVENT_HANDLER_NAME = "_handler_event_"

    def __init__(self, experimentId, mqttClient):

        #assert experimentId
        #assert mqttClient

        # params
        self.experimentId = experimentId
        self.mqttClient = mqttClient
        self.outstandingPacketsFromDagRoot = []

        # start poller thread for periodic measurements
        self.performanceUpdatePoller = PerformanceUpdatePoller(self.experimentId, self.mqttClient,
                                                               self.PERFORMANCE_EVENT_MEASUREMENT_PERIOD)

    # ======================== public =========================================

    def handle_event(self, sender, signal, data):
        (source, event, timestamp, buf) = data

        returnVal = {}


        log.debug(
            "sender: {0}\n signal: {1}\n source: {2}\n event: {3}\n timestamp: {4}\n data: {5}".format(sender, signal,
                                                                                                       source, event,
                                                                                                       timestamp, data))
        try:

            # find the event
            handler_name = None
            for ev in self.EV_ASYNC_ALL:
                if ev[1] == event:
                    handler_name = ev[0]
                    event_name   = ev[2]
                    break

            assert handler_name, "Unhandled event, ignoring: {0}".format(event)

            # find the handler
            event_handler = getattr(self, '{0}{1}'.format(self.PERFORMANCE_EVENT_HANDLER_NAME, handler_name, None))

            assert event_handler, "Event recognized but cannot find handler, event: {0}".format(event)

            # call the handler to return dictionary with handler-specific fields in the response
            # handler return is in format (success, dict), with:
            #   - success, as a boolean
            #   - dict, dictionary containing fields to include in the response or None on failure
            (success, dict) = event_handler(buf)

            if success:
                self.publish_event(event=event_name, timestamp=str(timestamp), source=source, eventSpecificFields=dict)

        except Exception as err:
            log.exception("Exception while executing {0}".format(event))
            log.exception(err)
            log.exception(traceback.format_exc())

    def close(self):
        if self.performanceUpdatePoller:
            self.performanceUpdatePoller.close()

    def publish_event(self, event, timestamp, source, eventSpecificFields):
        payload = {}

        payload['event']        = event
        payload['timestamp']    = timestamp
        payload['source']       = source

        # update the payload with event specific fields
        payload.update(eventSpecificFields)

        topic = 'openbenchmark/experimentId/{0}/nodeId/{1}/performanceData'.format(self.experimentId, source)

        log.debug("Publishing on topic: {0} Payload: {1}".format(topic, payload))

        self.mqttClient.publish(
         topic=topic,
         payload=json.dumps(returnVal),
        )

    def add_outstanding_packet(self, packet):
        if len(self.outstandingPacketsFromDagRoot) > 10:
            self.outstandingPacketsFromDagRoot.pop(0)
        self.outstandingPacketsFromDagRoot.append(packet)

    # ======================== private =========================================

    # packetSent
    def _handler_event_packetSent(self, buf):
        returnVal = {}

        packetToken = buf[:5]
        destBuf = buf[5:13]
        dest = openvisualizer.openvisualizer_utils.formatAddr(destBuf)
        hopLimit = buf[13]

        returnVal['packetToken'] = packetToken
        returnVal['destination'] = dest
        returnVal['hopLimit']    = hopLimit

        return (True, returnVal)

    def _handler_event_packetSentDagRoot(self, buf):
        receivedToken = buf
        newBuf = []

        for packet in self.outstandingPacketsFromDagRoot:
            (token, destination, hopLimit) = packet
            if receivedToken == token:
                # we have a hit, remove it from outstanding packets
                log.debug("packetSentDagRoot event: hit for packet {0}".format(packet))
                self.outstandingPacketsFromDagRoot.remove(packet)

                # construct the missing fields from the saved values
                newBuf += token
                newBuf += destination
                newBuf += [hopLimit]
                return self._handler_event_packetSent(newBuf)
        # not found, not all packets sent by dag root are originated by openbenchmark: ignore it
        log.debug("packetSentDagRoot event: miss for token {0}".format(receivedToken))
        return (False, {})

    # packetReceived, same syntax as packetSent
    def _handler_event_packetReceived(self, buf):
        return self._handler_event_packetSent(buf)

    # synchronizationCompleted
    def _handler_event_synchronizationCompleted(self, buf):
        return (True, {})

    # secureJoinCompleted
    def _handler_event_secureJoinCompleted(self, buf):
        return (True, {})

    # bandwidthAssigned
    def _handler_event_bandwidthAssigned(self, buf):
        return (True, {})

    # networkFormationCompleted
    def _handler_event_networkFormationCompleted(self, buf):
        # TODO
        return (True, {})

# ================= helper class that polls for periodic measurements =====================

class PerformanceUpdatePoller(eventBusClient.eventBusClient, threading.Thread):

    # periodic event names
    EV_RADIO_DUTY_CYCLE_MEASUREMENT = ['radioDutyCycleMeasurement',    258 ]
    EV_CLOCK_DRIFT_MEASUREMENT =      ['clockDriftMeasurement',        259 ]

    EV_SYNC_ALL = [
        EV_RADIO_DUTY_CYCLE_MEASUREMENT,
        EV_CLOCK_DRIFT_MEASUREMENT,
    ]

    def __init__(self, experimentId, mqttClient, period):
        # log
        log.info("creating a thread for periodic polling of performance metrics")

        # params
        self.experimentId = experimentId
        self.mqttClient = mqttClient
        self.period = period

        # local vars
        self.dutyCycleMeasurements = set()
        self.dataLock = threading.Lock()

        # flag to permit exit from infinite loop
        self.goOn = True

        # initialize the parent class
        threading.Thread.__init__(self)

        # give this thread a name
        self.name = 'performanceUpdatePollerThread'

        # subscribe to eventBus performance-related events
        eventBusClient.eventBusClient.__init__(
            self,
            name='performanceUpdatePoller',
            registrations=[
                {
                    'sender': self.WILDCARD,
                    'signal': 'dutyCycleMeasurement',
                    'callback': self.handle_dutyCycleMeasurement,
                },
                # TODO clock drift measurements
            ]
        )
        # start myself
        self.start()

    # ======================== public =========================================

    def run(self):
        try:
            # log
            log.info("start running")

            while self.goOn:

                log.debug("poller is polling")

                # poll moteState for latest measurements
                self.dispatch('getDutyCycleMeasurement', [])

                # wait for a while to gather the response from motes
                time.sleep(1)

                log.debug("Performance Event Poller, received measurements:")
                log.debug(self.dutyCycleMeasurements)

                for measurement in self.dutyCycleMeasurements:

                    # dispatch each as an individual message
                    (source, timestamp, dutyCycle) = measurement

                    topic = 'openbenchmark/experimentId/{0}/nodeId/{1}/performanceData'.format(self.experimentId, source)
                    payload = {
                        'event'     : self.EV_RADIO_DUTY_CYCLE_MEASUREMENT[0],
                        'timestamp' : timestamp,
                        'source'    : source,
                        'dutyCycle' : dutyCycle,
                    }

                    log.debug("Publishing on topic: {0} Payload: {1}".format(topic, payload))

                    self.mqttClient.publish(
                      topic='openbenchmark/experimentId/{0}/nodeId/{0}/performanceData'.format(self.experimentId, source),
                      payload=json.dumps(payload),
                    )

                with self.dataLock:
                    # reset for the next measurement
                    self.dutyCycleMeasurements = set()

                time.sleep(self.period)

        except Exception as err:
            errMsg = u.formatCrashMessage(self.name, err)
            print errMsg
            log.critical(errMsg)
            self.close()
        finally:
            pass

    def close(self):
        self.goOn = False

    def handle_dutyCycleMeasurement(self, sender, signal, data):
        with self.dataLock:
            self.dutyCycleMeasurements.add(
                ( data['source'], data['timestamp'], data['dutyCycle'] )
            )

# ==================== Implementation of CoAP openbenchmark resource =====================

class OpenbenchmarkResource(coapResource.coapResource):

    def __init__(self, performanceEvent, dagRootEui64):

        # params
        self.performanceEvent = performanceEvent
        self.dagRootEui64 = dagRootEui64

        # initialize parent class
        coapResource.coapResource.__init__(
            self,
            path='b',
        )

    def POST(self, options=[], payload=[], metaData={}):
        # token is in the last 5 bytes of payload
        token = payload[-5:]
        timestamp = metaData['generic_1']
        source = self.dagRootEui64

        destination = u.ipv6AddrString2Bytes(metaData['srcIP'])
        destinationEui64String = openvisualizer.openvisualizer_utils.formatAddr(destination[8:])

        log.debug("OpenbenchmarkResource: POST handler received metadata: {0}".format(metaData))

        dict = {
            'packetToken'   : token,
            'destination'   : destinationEui64String,
            'hopLimit'      : metaData['generic_0'],
        }

        self.performanceEvent.publish_event(PerformanceEvent.EV_PACKET_RECEIVED[0], timestamp, source, dict)
        return (d.COAP_RC_2_04_CHANGED, [], [])
