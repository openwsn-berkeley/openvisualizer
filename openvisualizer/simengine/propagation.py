#!/usr/bin/python
# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import random
import threading
from math import radians, cos, sin, asin, sqrt, log10

from openvisualizer.eventbus.eventbusclient import EventBusClient


class Propagation(EventBusClient):
    """ The propagation model of the engine. """

    SIGNAL_WIRELESSTXSTART = 'wirelessTxStart'
    SIGNAL_WIRELESSTXEND = 'wirelessTxEnd'

    FREQUENCY_GHz = 2.4
    TX_POWER_dBm = 0.0
    PISTER_HACK_LOSS = 40.0
    SENSITIVITY_dBm = -101.0
    GREY_AREA_dB = 15.0

    def __init__(self, sim_topology):

        # store params
        from openvisualizer.simengine import simengine
        self.engine = simengine.SimEngine()
        self.sim_topology = sim_topology

        # local variables
        self.data_lock = threading.Lock()
        self.connections = {}
        self.pending_tx_end = []

        # logging
        self.log = logging.getLogger('Propagation')
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(logging.NullHandler())

        # initialize parents class
        super(Propagation, self).__init__(
            name='Propagation',
            registrations=[
                {
                    'sender': self.WILDCARD,
                    'signal': self.SIGNAL_WIRELESSTXSTART,
                    'callback': self._indicate_tx_start,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': self.SIGNAL_WIRELESSTXEND,
                    'callback': self._indicate_tx_end,
                },
            ],
        )

    # ======================== public ==========================================

    def create_connection(self, from_mote, to_mote):

        with self.data_lock:

            if not self.sim_topology:

                # ===== Pister-hack model

                # retrieve position
                mh_from = self.engine.get_mote_handler_by_id(from_mote)
                (lat_from, lon_from) = mh_from.get_location()
                mh_to = self.engine.get_mote_handler_by_id(to_mote)
                (lat_to, lon_to) = mh_to.get_location()

                # compute distance
                lon_from, lat_from, lon_to, lat_to = map(radians, [lon_from, lat_from, lon_to, lat_to])
                d_lon = lon_to - lon_from
                d_lat = lat_to - lat_from
                a = sin(d_lat / 2) ** 2 + cos(lat_from) * cos(lat_to) * sin(d_lon / 2) ** 2
                c = 2 * asin(sqrt(a))
                d_km = 6367 * c

                # compute reception power (first Friis, then apply Pister-hack)
                p_rx = self.TX_POWER_dBm - (20 * log10(d_km) + 20 * log10(self.FREQUENCY_GHz) + 92.45)
                p_rx -= self.PISTER_HACK_LOSS * random.random()

                # turn into PDR
                if p_rx < self.SENSITIVITY_dBm:
                    pdr = 0.0
                elif p_rx > self.SENSITIVITY_dBm + self.GREY_AREA_dB:
                    pdr = 1.0
                else:
                    pdr = (p_rx - self.SENSITIVITY_dBm) / self.GREY_AREA_dB

            elif self.sim_topology == 'linear':

                # linear network
                if from_mote == to_mote + 1:
                    pdr = 1.0
                else:
                    pdr = 0.0

            elif self.sim_topology == 'fully-meshed':

                pdr = 1.0

            else:

                raise NotImplementedError('unsupported sim_topology={0}'.format(self.sim_topology))

            # ==== create, update or delete connection

            if pdr:
                if from_mote not in self.connections:
                    self.connections[from_mote] = {}
                self.connections[from_mote][to_mote] = pdr

                if to_mote not in self.connections:
                    self.connections[to_mote] = {}
                self.connections[to_mote][from_mote] = pdr
            else:
                self.delete_connection(to_mote, from_mote)

    def retrieve_connections(self):

        retrieved_connections = []
        return_val = []
        with self.data_lock:

            for from_mote in self.connections:
                for to_mote in self.connections[from_mote]:
                    if (to_mote, from_mote) not in retrieved_connections:
                        return_val += [
                            {
                                'fromMote': from_mote,
                                'toMote': to_mote,
                                'pdr': self.connections[from_mote][to_mote],
                            },
                        ]
                        retrieved_connections += [(from_mote, to_mote)]

        return return_val

    def update_connection(self, from_mote, to_mote, pdr):

        with self.data_lock:
            self.connections[from_mote][to_mote] = pdr
            self.connections[to_mote][from_mote] = pdr

    def delete_connection(self, from_mote, to_mote):

        with self.data_lock:

            try:
                del self.connections[from_mote][to_mote]
                if not self.connections[from_mote]:
                    del self.connections[from_mote]

                del self.connections[to_mote][from_mote]
                if not self.connections[to_mote]:
                    del self.connections[to_mote]
            except KeyError:
                pass  # did not exist

    # ======================== indication from eventBus ========================

    def _indicate_tx_start(self, sender, signal, data):

        (from_mote, packet, channel) = data

        if from_mote in self.connections:
            for (to_mote, pdr) in self.connections[from_mote].items():
                if random.random() <= pdr:
                    # indicate start of transmission
                    mh = self.engine.get_mote_handler_by_id(to_mote)
                    mh.bsp_radio.indicate_tx_start(from_mote, packet, channel)

                    # remember to signal end of transmission
                    self.pending_tx_end += [(from_mote, to_mote)]

    def _indicate_tx_end(self, sender, signal, data):

        from_mote = data

        if from_mote in self.connections:
            for (to_mote, pdr) in self.connections[from_mote].items():
                try:
                    self.pending_tx_end.remove((from_mote, to_mote))
                except ValueError:
                    pass
                else:
                    mh = self.engine.get_mote_handler_by_id(to_mote)
                    mh.bsp_radio.indicate_tx_end(from_mote)

    # ======================== private =========================================

    # ======================== helpers =========================================
