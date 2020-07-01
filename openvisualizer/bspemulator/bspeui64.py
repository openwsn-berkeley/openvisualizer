# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging

from openvisualizer.bspemulator.bspmodule import BspModule


class BspEui64(BspModule):
    """ Emulates the 'eui64' BSP module """

    _name = 'BspEui64'

    def __init__(self, motehandler):

        # initialize the parent
        super(BspEui64, self).__init__(motehandler)

    # ======================== public ==========================================

    # === commands

    def cmd_get(self):
        """ Emulates: void eui64_get(uint8_t* addressToWrite)"""

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_get')

        # get my 16-bit ID
        my_id = self.motehandler.get_id()

        # format my EUI64
        my_eui64 = [0x14, 0x15, 0x92, 0xcc, 0x00, 0x00, ((my_id >> 8) & 0xff), ((my_id >> 0) & 0xff)]

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('returning ' + str(my_eui64))

        # respond
        return my_eui64

    # ======================== private =========================================
