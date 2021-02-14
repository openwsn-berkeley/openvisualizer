# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

"""
Module which receives DAO messages and calculates source routes.

.. moduleauthor:: Xavi Vilajosana <xvilajosana@eecs.berkeley.edu>
                  January 2013
.. moduleauthor:: Thomas Watteyne <watteyne@eecs.berkeley.edu>
                  April 2013
"""

import logging
import threading
import time

import struct
import json
import paho.mqtt.client as mqtt

from openvisualizer.eventbus.eventbusclient import EventBusClient

log = logging.getLogger('Topology')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


class Topology(EventBusClient):

    def __init__(self, mqtt_broker):

        # log

        log.debug('create instance')
        # local variables
        self.data_lock = threading.Lock()
        self.parents = {}
        self.parents_last_seen = {}
        self.NODE_TIMEOUT_THRESHOLD = 900

        super(Topology, self).__init__(
            name='topology',
            registrations=[
                {
                    'sender': self.WILDCARD,
                    'signal': 'updateParents',
                    'callback': self.update_parents,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'getParents',
                    'callback': self.get_parents,
                },
            ],
        )

        self.broker = mqtt_broker
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


    def publish_topology(self):
        payload = {'token': 123}
        payload['topology'] = str(self.parents)

        if self.mqtt_connected:
            # publish the cmd message
            self.mqtt_client.publish(topic='opentestbed/openv-server/topology', payload=json.dumps(payload), qos=2)


    # ======================== private =========================================

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        self.mqtt_connected = True

    # ======================== public ==========================================

    def get_parents(self, sender, signal, data):
        return self.parents

    def get_dag(self):
        states = []
        edges = []
        motes = []

        with self.data_lock:
            for src, dsts in self.parents.items():
                src_s = ''.join(['%02X' % x for x in src[-2:]])
                motes.append(src_s)
                for dst in dsts:
                    dst_s = ''.join(['%02X' % x for x in dst[-2:]])
                    edges.append({'u': src_s, 'v': dst_s})
                    motes.append(dst_s)
            motes = list(set(motes))
            for mote in motes:
                d = {'id': mote, 'value': {'label': mote}}
                states.append(d)

        return states, edges

    def update_parents(self, sender, signal, data):
        """ inserts parent information into the parents dictionary """
        with self.data_lock:
            # data[0] == source address, data[1] == list of parents
            self.parents.update({data[0]: data[1]})
            self.parents_last_seen.update({data[0]: time.time()})
        self.publish_topology()
        self._clear_node_timeout()

    def _clear_node_timeout(self):
        threshold = time.time() - self.NODE_TIMEOUT_THRESHOLD
        with self.data_lock:
            for node in self.parents_last_seen.keys():
                if self.parents_last_seen[node] < threshold:
                    if node in self.parents:
                        del self.parents[node]
                    del self.parents_last_seen[node]

    # ======================== private =========================================

    # ======================== helpers =========================================
