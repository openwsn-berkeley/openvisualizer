# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
from multiprocessing import get_logger

from openvisualizer.simulator.bspemulator.bspmodule import BspModule


class BspDebugPins(BspModule):
    """ Emulates the 'debugpins' BSP module. """

    def __init__(self, mote):
        # initialize the parent
        super(BspDebugPins, self).__init__(mote)

        # logging

        self.logger = get_logger()
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

        # local variables
        self.frame_pin_high = False
        self.slot_pin_high = False
        self.fsm_pin_high = False
        self.task_pin_high = False
        self.isr_pin_high = False
        self.radio_pin_high = False
        self.ka_pin_high = False
        self.sync_packet_pin_high = False
        self.sync_ack_pin_high = False
        self.debug_pin_high = False

    # ======================== public ==========================================

    # === commands

    def cmd_init(self):
        """Emulates: void debugpins_init() """

        # log the activity
        self.logger.debug('cmd_init')

        # remember that module has been initialized
        self.is_initialized = True

    # frame

    def cmd_frame_toggle(self):
        """ Emulates: void debugpins_frame_toggle() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_frame_toggle')

        # change the internal state
        self.frame_pin_high = not self.frame_pin_high

    def cmd_frame_clr(self):
        """ Emulates: void debugpins_frame_clr() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_frame_clr')

        # change the internal state
        self.frame_pin_high = False

    def cmd_frame_set(self):
        """ Emulates: void debugpins_frame_set() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_frame_set')

        # change the internal state
        self.frame_pin_high = True

    # slot

    def cmd_slot_toggle(self):
        """ Emulates: void debugpins_slot_toggle() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_slot_toggle')

        # change the internal state
        self.slot_pin_high = not self.slot_pin_high

    def cmd_slot_clr(self):
        """ Emulates: void debugpins_slot_clr() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_slot_clr')

        # change the internal state
        self.slot_pin_high = False

    def cmd_slot_set(self):
        """ Emulates: void debugpins_slot_set() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_slot_set')

        # change the internal state
        self.slot_pin_high = True

    # fsm

    def cmd_fsm_toggle(self):
        """ Emulates: void debugpins_fsm_toggle() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_fsm_toggle')

        # change the internal state
        self.fsm_pin_high = not self.fsm_pin_high

    def cmd_fsm_clr(self):
        """ Emulates: void debugpins_fsm_clr() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_fsm_clr')

        # change the internal state
        self.fsm_pin_high = False

    def cmd_fsm_set(self):
        """ Emulates: void debugpins_fsm_set() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_fsm_set')

        # change the internal state
        self.fsm_pin_high = True

    # task

    def cmd_task_toggle(self):
        """ Emulates: void debugpins_task_toggle() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_task_toggle')

        # change the internal state
        self.task_pin_high = not self.task_pin_high

    def cmd_task_clr(self):
        """ Emulates: void debugpins_task_clr() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_task_clr')

        # change the internal state
        self.task_pin_high = False

    def cmd_task_set(self):
        """ Emulates: void debugpins_task_set() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_task_set')

        # change the internal state
        self.task_pin_high = True

    # isr

    def cmd_isr_toggle(self):
        """ Emulates: void debugpins_isr_toggle() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_isr_toggle')

        # change the internal state
        self.isr_pin_high = not self.isr_pin_high

    def cmd_isr_clr(self):
        """ Emulates: void debugpins_isr_clr() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_isr_clr')

        # change the internal state
        self.isr_pin_high = False

    def cmd_isr_set(self):
        """ Emulates: void debugpins_isr_set() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_isr_set')

        # change the internal state
        self.isr_pin_high = True

    # radio

    def cmd_radio_toggle(self):
        """ Emulates: void debugpins_radio_toggle() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_radio_toggle')

        # change the internal state
        self.radio_pin_high = not self.radio_pin_high

    def cmd_radio_clr(self):
        """ Emulates: void debugpins_radio_clr()"""

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_radio_clr')

        # change the internal state
        self.radio_pin_high = False

    def cmd_radio_set(self):
        """ Emulates: void debugpins_radio_set() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_radio_set')

        # change the internal state
        self.radio_pin_high = True

    # ka

    def cmd_ka_clr(self):
        """ Emulates: void debugpins_ka_clr() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_ka_clr')

        # change the internal state
        self.ka_pin_high = False

    def cmd_ka_set(self):
        """ Emulates: void debugpins_ka_set() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_ka_set')

        # change the internal state
        self.ka_pin_high = True

    # syncPacket

    def cmd_sync_packet_clr(self):
        """ Emulates: void debugpins_syncPacket_clr() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_sync_packet_clr')

        # change the internal state
        self.sync_packet_pin_high = False

    def cmd_sync_packet_set(self):
        """ Emulates: void debugpins_syncPacket_set() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_sync_packet_set')

        # change the internal state
        self.sync_packet_pin_high = True

    # syncAck

    def cmd_sync_ack_clr(self):
        """ Emulates: void debugpins_syncAck_clr() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_sync_ack_clr')

        # change the internal state
        self.sync_ack_pin_high = False

    def cmd_sync_ack_set(self):
        """ Emulates: void debugpins_syncAck_set() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_sync_ack_set')

        # change the internal state
        self.sync_ack_pin_high = True

    # debug

    def cmd_debug_clr(self):
        """ Emulates: void debugpins_debug_clr() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_debug_clr')

        # change the internal state
        self.debug_pin_high = False

    def cmd_debug_set(self):
        """ Emulates: void debugpins_debug_set() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_debug_set')

        # change the internal state
        self.debug_pin_high = True

    # === getters

    def get_frame_pin_high(self):
        return self.frame_pin_high

    def get_slot_pin_high(self):
        return self.slot_pin_high

    def get_fsm_pin_high(self):
        return self.fsm_pin_high

    def get_isr_pin_high(self):
        return self.isr_pin_high

    def get_radio_pin_high(self):
        return self.radio_pin_high

    def get_ka_pin_high(self):
        return self.ka_pin_high

    def get_sync_packet_pin_high(self):
        return self.sync_packet_pin_high

    def get_sync_ack_pin_high(self):
        return self.sync_ack_pin_high

    def get_debug_pin_high(self):
        return self.debug_pin_high

    # ======================== private =========================================
