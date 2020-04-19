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

from openvisualizer.eventbus import eventbusclient

log = logging.getLogger('Topology')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


class Topology(eventbusclient.EventBusClient):

    def __init__(self):

        # local variables
        self.dataLock = threading.Lock()
        self.parents = {}
        self.parentsLastSeen = {}
        self.NODE_TIMEOUT_THRESHOLD = 900

        super(Topology, self).__init__(
            name='Topology',
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
            ]
        )

    # ======================== public ==========================================

    def get_parents(self, sender, signal, data):
        return self.parents

    def get_dag(self):
        states = []
        edges = []
        motes = []

        with self.dataLock:
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
        with self.dataLock:
            # data[0] == source address, data[1] == list of parents
            self.parents.update({data[0]: data[1]})
            self.parentsLastSeen.update({data[0]: time.time()})

        self._clear_node_timeout()

    def _clear_node_timeout(self):
        threshold = time.time() - self.NODE_TIMEOUT_THRESHOLD
        with self.dataLock:
            for node in self.parentsLastSeen.keys():
                if self.parentsLastSeen[node] < threshold:
                    if node in self.parents:
                        del self.parents[node]
                    del self.parentsLastSeen[node]

    # ======================== private =========================================

    # ======================== helpers =========================================
