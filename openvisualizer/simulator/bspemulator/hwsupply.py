# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
from multiprocessing import get_logger

from openvisualizer.simulator.bspemulator.hwmodule import HwModule


class HwSupply(HwModule):
    """ Emulates the mote's power supply """

    def __init__(self, mote):
        # initialize the parent
        super(HwSupply, self).__init__(mote)

        # logging
        self.logger = get_logger()
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

        # local variables
        self.mote_on = False

    # ======================== public ==========================================

    def switch_on(self):

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('switchOn')

        # filter error
        if self.mote_on:
            raise RuntimeError('mote already on')

        # change local variable
        self.mote_on = True

        # have the crystal start now
        self.mote.hw_crystal.start()

        # send command to mote
        self.mote.mote.supply_on()

    def switch_off(self):

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('switchOff')

        # filter error
        if not self.mote_on:
            raise RuntimeError('mote already off')

        # change local variable
        self.mote_on = False

        # send command to mote
        self.mote.mote.supply_off()

    def is_on(self):
        return self.mote_on

    # ======================== private =========================================
