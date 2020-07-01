#!/usr/bin/python
# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import threading
import time

from openvisualizer.simengine import timeline, propagation, idmanager, locationmanager


class SimEngineStats(object):
    def __init__(self):
        self.durationRunning = 0
        self.running = False
        self.txStart = None

    def indicate_start(self):
        self.txStart = time.time()
        self.running = True

    def indicate_stop(self):
        if self.txStart:
            self.durationRunning += time.time() - self.txStart
            self.running = False

    def get_duration_running(self):
        if self.running:
            return self.durationRunning + (time.time() - self.txStart)
        else:
            return self.durationRunning


class SimEngine(object):
    """ The main simulation engine. """

    # ======================== singleton pattern ===============================

    _instance = None
    _init = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SimEngine, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    # ======================== main ============================================

    def __init__(self, sim_topology='', log_handler=logging.StreamHandler(), log_level=logging.WARNING):

        # don't re-initialize an instance (singleton pattern)
        if self._init:
            return
        self._init = True

        # store params
        self.log_handler = log_handler
        self.log_handler.setFormatter(
            logging.Formatter(fmt='%(asctime)s [%(name)s:%(levelname)s] %(message)s', datefmt='%H:%M:%S'))

        # local variables
        self.moteHandlers = []
        self.timeline = timeline.TimeLine()
        self.propagation = propagation.Propagation(sim_topology)
        self.id_manager = idmanager.IdManager()
        self.location_manager = locationmanager.LocationManager()
        self.pauseSem = threading.Lock()
        self.isPaused = False
        self.stopAfterSteps = None
        self.delay = 0
        self.stats = SimEngineStats()

        # logging this module
        self.log = logging.getLogger('SimEngine')
        self.log.setLevel(logging.INFO)
        self.log.addHandler(logging.NullHandler())

        # logging core modules
        for logger_name in ['SimEngine', 'Timeline', 'Propagation', 'IdManager', 'LocationManager']:
            temp = logging.getLogger(logger_name)
            temp.setLevel(log_level)
            temp.addHandler(log_handler)

    def start(self):

        # log
        self.log.info('starting')

        # start timeline
        self.timeline.start()

    # ======================== public ==========================================

    # === controlling execution speed

    def set_delay(self, delay):
        self.delay = delay

    def pause(self):
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('pause')
        if not self.isPaused:
            self.pauseSem.acquire()
            self.isPaused = True
            self.stats.indicate_stop()

    def step(self, num_steps):
        self.stopAfterSteps = num_steps
        if self.isPaused:
            self.pauseSem.release()
            self.isPaused = False

    def resume(self):
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('resume')
        self.stopAfterSteps = None
        if self.isPaused:
            self.pauseSem.release()
            self.isPaused = False
            self.stats.indicate_start()

    def pause_or_delay(self):
        if self.isPaused:
            if self.log.isEnabledFor(logging.DEBUG):
                self.log.debug('pauseOrDelay: pause')
            self.pauseSem.acquire()
            self.pauseSem.release()
        else:
            if self.log.isEnabledFor(logging.DEBUG):
                self.log.debug('pauseOrDelay: delay {0}'.format(self.delay))
            time.sleep(self.delay)

        if self.stopAfterSteps is not None:
            if self.stopAfterSteps > 0:
                self.stopAfterSteps -= 1
            if self.stopAfterSteps == 0:
                self.pause()

        assert (self.stopAfterSteps is None or self.stopAfterSteps >= 0)

    def is_running(self):
        return not self.isPaused

    # === called from the main script

    def indicate_new_mote(self, new_mote_handler):

        # add this mote to my list of motes
        self.moteHandlers.append(new_mote_handler)

        # create connections to already existing motes
        for mh in self.moteHandlers[:-1]:
            self.propagation.create_connection(
                from_mote=new_mote_handler.get_id(),
                to_mote=mh.get_id(),
            )

    # === called from timeline

    def indicate_first_event_passed(self):
        self.stats.indicate_start()

    # === getting information about the system

    def get_num_motes(self):
        return len(self.moteHandlers)

    def get_mote_handler(self, rank):
        return self.moteHandlers[rank]

    def get_mote_handler_by_id(self, mote_id):
        return_val = None
        for h in self.moteHandlers:
            if h.get_id() == mote_id:
                return_val = h
                break
        assert return_val
        return return_val

    def get_stats(self):
        return self.stats

    # ======================== private =========================================

    # ======================== helpers =========================================
