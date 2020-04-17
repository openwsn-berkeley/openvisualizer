#!/usr/bin/python
# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import threading
import time

import timeline
import idmanager
import locationmanager
import propagation


class SimEngineStats(object):
    def __init__(self):
        self.durationRunning = 0
        self.running = False
        self.txStart = None

    def indicateStart(self):
        self.txStart = time.time()
        self.running = True

    def indicateStop(self):
        if self.txStart:
            self.durationRunning += time.time() - self.txStart
            self.running = False

    def getDurationRunning(self):
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

    def __init__(self, simTopology='', loghandler=logging.NullHandler()):

        # don't re-initialize an instance (singleton pattern)
        if self._init:
            return
        self._init = True

        # store params
        self.loghandler = loghandler

        # local variables
        self.moteHandlers = []
        self.timeline = timeline.TimeLine()
        self.propagation = propagation.Propagation(simTopology)
        self.idmanager = idmanager.IdManager()
        self.locationmanager = locationmanager.LocationManager()
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
        for loggerName in [
            'SimEngine',
            'Timeline',
            'Propagation',
            'IdManager',
            'LocationManager',
            'SimCli',
        ]:
            temp = logging.getLogger(loggerName)
            temp.setLevel(logging.INFO)
            temp.addHandler(loghandler)

    def start(self):

        # log
        self.log.info('starting')

        # start timeline
        self.timeline.start()

    # ======================== public ==========================================

    # === controlling execution speed

    def setDelay(self, delay):
        self.delay = delay

    def pause(self):
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('pause')
        if not self.isPaused:
            self.pauseSem.acquire()
            self.isPaused = True
            self.stats.indicateStop()

    def step(self, numSteps):
        self.stopAfterSteps = numSteps
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
            self.stats.indicateStart()

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

    def isRunning(self):
        return not self.isPaused

    # === called from the main script

    def indicateNewMote(self, newMoteHandler):

        # add this mote to my list of motes
        self.moteHandlers.append(newMoteHandler)

        # create connections to already existing motes
        for mh in self.moteHandlers[:-1]:
            self.propagation.create_connection(
                from_mote=newMoteHandler.get_id(),
                to_mote=mh.get_id(),
            )

    # === called from timeline

    def indicate_first_event_passed(self):
        self.stats.indicateStart()

    # === getting information about the system

    def getNumMotes(self):
        return len(self.moteHandlers)

    def getMoteHandler(self, rank):
        return self.moteHandlers[rank]

    def get_mote_handler_by_id(self, moteId):
        returnVal = None
        for h in self.moteHandlers:
            if h.get_id() == moteId:
                returnVal = h
                break
        assert returnVal
        return returnVal

    def getStats(self):
        return self.stats

    # ======================== private =========================================

    # ======================== helpers =========================================
