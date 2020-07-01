# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

from openvisualizer.bspemulator.bspmodule import BspModule


class BspBoard(BspModule):
    """ Emulates the 'board' BSP module """

    _name = 'BspBoard'

    def __init__(self, motehandler):
        # initialize the parent
        super(BspBoard, self).__init__(motehandler)

        # local variables
        self.timeline = self.engine.timeline

    # ======================== public ==========================================

    # === commands

    def cmd_init(self):
        """ Emulates: void board_init() """

        # log the activity
        self.log.debug('cmd_init')

        # remember that module has been initialized
        self.is_initialized = True

    def cmd_sleep(self):
        """ Emulates: void board_init() """

        try:
            # log the activity
            self.log.debug('cmd_sleep')

            self.motehandler.cpu_done.release()

            # block the mote until CPU is released by ISR
            self.motehandler.cpu_running.acquire()

        except Exception as err:
            self.log.critical(err)

    # ======================== private =========================================
