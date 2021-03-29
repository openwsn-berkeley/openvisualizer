# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
from multiprocessing import get_logger

from openvisualizer.simulator.bspemulator.bspmodule import BspModule


class BspSctimer(BspModule):
    """ Emulates the 'sctimer' BSP module. """

    INTR_COMPARE = 'sctimer.compare'
    INTR_OVERFLOW = 'sctimer.overflow'
    ROLLOVER = 0xffffffff + 1

    LOOP_THRESHOLD = 0xffffff + 1

    def __init__(self, mote):
        # initialize the parent
        super(BspSctimer, self).__init__(mote)

        # logging
        self.logger = get_logger()
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

        # local variables
        self.hw_crystal = self.mote.hw_crystal
        self.running = False
        self.compare_armed = False
        self.time_last_reset = None
        self.time_last_compare = None
        self.int_enabled = True

    # ======================== public ==========================================

    # === commands

    def cmd_init(self):
        """ Emulates: void sctimer_init() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_init')

        # remember the time of last reset
        self.time_last_reset = self.hw_crystal.get_time_last_tick()
        self.time_last_compare = self.time_last_reset

        # calculate time at overflow event (in 'ROLLOVER' ticks)
        overflow_time = self.hw_crystal.get_time_in(self.ROLLOVER)

        # schedule overflow event
        self.mote.bsp_board.schedule_intr(
            at_time=overflow_time,
            mote_id=self.mote.mote_id,
            cb=self.intr_overflow,
            desc=self.INTR_OVERFLOW)

        # the counter is now running
        self.running = True

        # disable interrupt for now
        self.int_enabled = True

        # remember that module has been initialized
        self.is_initialized = True

    def cmd_set_compare(self, compare_value):
        """ Emulates: void sctimer_setCompare(PORT_TIMER_WIDTH compare_value) """

        try:
            # enable interrupt
            self.cmd_enable()

            # log the activity
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug('cmd_set_compare compare_value=' + str(compare_value))

            # get current counter value
            counter_val = self.hw_crystal.get_ticks_since(self.time_last_reset)

            # how many ticks until compare event
            if 0 < counter_val - compare_value < self.LOOP_THRESHOLD:
                # we're already too late, schedule compare event right now
                ticks_before_event = 0
            else:
                ticks_before_event = compare_value - counter_val

            # calculate time at overflow event
            compare_time = self.hw_crystal.get_time_in(ticks_before_event)

            # schedule compare event
            self.mote.bsp_board.schedule_intr(
                at_time=compare_time,
                mote_id=self.mote.mote_id,
                cb=self.intr_compare,
                desc=self.INTR_COMPARE)

            # the compare is now scheduled
            self.compare_armed = True

        except Exception as err:
            self.logger.critical(err)

    def cmd_read_counter(self):
        """ Emulates: uin16_t sctimer_readCounter() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_read_counter')

        # get current counter value
        counter_val = self.hw_crystal.get_ticks_since(self.time_last_reset)

        # respond
        return counter_val

    def cmd_enable(self):
        """ Emulates: void sctimer_enable() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_enable')

        self.int_enabled = True

    def cmd_disable(self):
        """ Emulates: void sctimer_disable() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_disable')

        # disable interrupt
        self.int_enabled = False

    # ======================== interrupts ======================================

    def intr_overflow(self):
        """ An (internal) overflow event happened. """

        # remember the time of this reset; needed internally to schedule further events
        self.time_last_reset = self.hw_crystal.get_time_last_tick()

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('time_last_reset=' + str(self.time_last_reset))
            self.logger.debug('ROLLOVER=' + str(self.ROLLOVER))

        # reschedule the next overflow event
        # Note: the intr_overflow will fire every self.ROLLOVER
        next_overflow_time = self.hw_crystal.get_time_in(self.ROLLOVER)
        self.logger.debug('next_overflow_time=' + str(next_overflow_time))
        self.mote.bsp_board.schedule_intr(
            at_time=next_overflow_time,
            mote_id=self.mote.mote_id,
            cb=self.intr_overflow,
            desc=self.INTR_OVERFLOW)

        # do NOT kick the scheduler
        return False

    def intr_compare(self):
        """ A compare event happened. """

        # remember the time of this comparison.
        self.time_last_compare = self.hw_crystal.get_time_last_tick()

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('time_last_compare=' + str(self.time_last_compare))
            self.logger.debug('ROLLOVER=' + str(self.ROLLOVER))

        if self.int_enabled:
            # send interrupt to mote
            self.mote.mote.sctimer_isr()

        # kick the scheduler
        return True

    # ======================== private =========================================
