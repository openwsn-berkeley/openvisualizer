# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
from multiprocessing import get_logger

from openvisualizer.simulator.bspemulator.bspmodule import BspModule


class BspEui64(BspModule):
    """ Emulates the 'eui64' BSP module """

    def __init__(self, mote):

        # initialize the parent
        super(BspEui64, self).__init__(mote)

        # logging

        self.logger = get_logger()
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

    # ======================== public ==========================================

    # === commands

    def cmd_get(self):
        """ Emulates: void eui64_get(uint8_t* addressToWrite)"""

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_get')

        # get my 16-bit ID
        my_id = self.mote.mote_id

        # format my EUI64
        my_eui64 = [0x14, 0x15, 0x92, 0xcc, 0x00, 0x00, ((my_id >> 8) & 0xff), ((my_id >> 0) & 0xff)]

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('returning ' + str(my_eui64))

        # respond
        return my_eui64

    # ======================== private =========================================
