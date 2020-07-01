#!/usr/bin/python
# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
import logging

from openvisualizer.bspemulator.hwmodule import HwModule


class HwSupply(HwModule):
    """ Emulates the mote's power supply """

    _name = 'HwModule'

    INTR_SWITCHON = 'hw_supply.switchOn'

    def __init__(self, motehandler):
        # initialize the parent
        super(HwSupply, self).__init__(motehandler)

        # local variables
        self.mote_on = False

    # ======================== public ==========================================

    def switch_on(self):

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('switchOn')

        # filter error
        if self.mote_on:
            raise RuntimeError('mote already on')

        # change local variable
        self.mote_on = True

        # have the crystal start now
        self.motehandler.hw_crystal.start()

        # send command to mote
        self.motehandler.mote.supply_on()

    def switch_off(self):

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('switchOff')

        # filter error
        if not self.mote_on:
            raise RuntimeError('mote already off')

        # change local variable
        self.mote_on = False

    def is_on(self):
        return self.mote_on

    # ======================== private =========================================
