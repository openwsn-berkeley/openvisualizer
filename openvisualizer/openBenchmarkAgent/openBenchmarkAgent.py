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
log = logging.getLogger('openBenchmarkAgent')
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())

from openvisualizer.eventBus      import eventBusClient

# a special logger that writes to a separate file: each log line is a JSON string corresponding to network events
# with information sufficient to calculate network-wide KPIs
networkEventLogger = logging.getLogger('networkEventLogger')
networkEventLogger.setLevel(logging.INFO)

OPENBENCHMARK_EXPERIMENT_CONTROL_COMMANDS_API_VERSION = "0.0.1"
OPENBENCHMARK_EXPERIMENT_PERFORMANCE_EVENTS_API_VERSION = "0.0.1"


class OpenBenchmarkAgent(eventBusClient.eventBusClient):
    def __init__(self, mqttBroker, firmware, testbed, nodes, scenario):
        self.mqttBroker = mqttBroker
        self.firmware = firmware
        self.testbed = testbed
        self.nodes = nodes
        self.scenario = scenario
        pass