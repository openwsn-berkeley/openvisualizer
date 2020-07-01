# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging

from openvisualizer.bspemulator import vcdlogger
from openvisualizer.bspemulator.bspmodule import BspModule


class BspDebugPins(BspModule):
    """ Emulates the 'debugpins' BSP module. """

    _name = 'BspDebugPins'

    def __init__(self, motehandler, vcdlog):
        # initialize the parent
        super(BspDebugPins, self).__init__(motehandler)

        # local variables
        self.timeline = self.engine.timeline
        self.framePinHigh = False
        self.slotPinHigh = False
        self.fsmPinHigh = False
        self.taskPinHigh = False
        self.isrPinHigh = False
        self.radioPinHigh = False
        self.kaPinHigh = False
        self.syncPacketPinHigh = False
        self.syncAckPinHigh = False
        self.debugPinHigh = False

        self.vcdlog = vcdlog

        if self.vcdlog:
            self.vcdLogger = vcdlogger.VcdLogger()

    # ======================== public ==========================================

    # === commands

    def cmd_init(self):
        """Emulates: void debugpins_init() """

        # log the activity
        self.log.debug('cmd_init')

        # remember that module has been initialized
        self.is_initialized = True

    # frame

    def cmd_frame_toggle(self):
        """ Emulates: void debugpins_frame_toggle() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_frame_toggle')

        # change the internal state
        self.framePinHigh = not self.framePinHigh

        # log VCD
        self._log_vcd('frame')

    def cmd_frame_clr(self):
        """ Emulates: void debugpins_frame_clr() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_frame_clr')

        # change the internal state
        self.framePinHigh = False

        # log VCD
        self._log_vcd('frame')

    def cmd_frame_set(self):
        """ Emulates: void debugpins_frame_set() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_frame_set')

        # change the internal state
        self.framePinHigh = True

        # log VCD
        self._log_vcd('frame')

    # slot

    def cmd_slot_toggle(self):
        """ Emulates: void debugpins_slot_toggle() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_slot_toggle')

        # change the internal state
        self.slotPinHigh = not self.slotPinHigh

        # log VCD
        self._log_vcd('slot')

    def cmd_slot_clr(self):
        """ Emulates: void debugpins_slot_clr() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_slot_clr')

        # change the internal state
        self.slotPinHigh = False

        # log VCD
        self._log_vcd('slot')

    def cmd_slot_set(self):
        """ Emulates: void debugpins_slot_set() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_slot_set')

        # change the internal state
        self.slotPinHigh = True

        # log VCD
        self._log_vcd('slot')

    # fsm

    def cmd_fsm_toggle(self):
        """ Emulates: void debugpins_fsm_toggle() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_fsm_toggle')

        # change the internal state
        self.fsmPinHigh = not self.fsmPinHigh

        # log VCD
        self._log_vcd('fsm')

    def cmd_fsm_clr(self):
        """ Emulates: void debugpins_fsm_clr() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_fsm_clr')

        # change the internal state
        self.fsmPinHigh = False

        # log VCD
        self._log_vcd('fsm')

    def cmd_fsm_set(self):
        """ Emulates: void debugpins_fsm_set() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_fsm_set')

        # change the internal state
        self.fsmPinHigh = True

        # log VCD
        self._log_vcd('fsm')

    # task

    def cmd_task_toggle(self):
        """ Emulates: void debugpins_task_toggle() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_task_toggle')

        # change the internal state
        self.taskPinHigh = not self.taskPinHigh

        # log VCD
        self._log_vcd('task')

    def cmd_task_clr(self):
        """ Emulates: void debugpins_task_clr() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_task_clr')

        # change the internal state
        self.taskPinHigh = False

        # log VCD
        self._log_vcd('task')

    def cmd_task_set(self):
        """ Emulates: void debugpins_task_set() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_task_set')

        # change the internal state
        self.taskPinHigh = True

        # log VCD
        self._log_vcd('task')

    # isr

    def cmd_isr_toggle(self):
        """ Emulates: void debugpins_isr_toggle() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_isr_toggle')

        # change the internal state
        self.isrPinHigh = not self.isrPinHigh

        # log VCD
        self._log_vcd('isr')

    def cmd_isr_clr(self):
        """ Emulates: void debugpins_isr_clr() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_isr_clr')

        # change the internal state
        self.isrPinHigh = False

        # log VCD
        self._log_vcd('isr')

    def cmd_isr_set(self):
        """ Emulates: void debugpins_isr_set() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_isr_set')

        # change the internal state
        self.isrPinHigh = True

        # log VCD
        self._log_vcd('isr')

    # radio

    def cmd_radio_toggle(self):
        """ Emulates: void debugpins_radio_toggle() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_radio_toggle')

        # change the internal state
        self.radioPinHigh = not self.radioPinHigh

        # log VCD
        self._log_vcd('radio')

    def cmd_radio_clr(self):
        """ Emulates: void debugpins_radio_clr()"""

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_radio_clr')

        # change the internal state
        self.radioPinHigh = False

        # log VCD
        self._log_vcd('radio')

    def cmd_radio_set(self):
        """ Emulates: void debugpins_radio_set() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_radio_set')

        # change the internal state
        self.radioPinHigh = True

        # log VCD
        self._log_vcd('radio')

    # ka

    def cmd_ka_clr(self):
        """ Emulates: void debugpins_ka_clr() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_ka_clr')

        # change the internal state
        self.kaPinHigh = False

        # log VCD
        self._log_vcd('ka')

    def cmd_ka_set(self):
        """ Emulates: void debugpins_ka_set() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_ka_set')

        # change the internal state
        self.kaPinHigh = True

        # log VCD
        self._log_vcd('ka')

    # syncPacket

    def cmd_sync_packet_clr(self):
        """ Emulates: void debugpins_syncPacket_clr() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_sync_packet_clr')

        # change the internal state
        self.syncPacketPinHigh = False

        # log VCD
        self._log_vcd('syncPacket')

    def cmd_sync_packet_set(self):
        """ Emulates: void debugpins_syncPacket_set() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_sync_packet_set')

        # change the internal state
        self.syncPacketPinHigh = True

        # log VCD
        self._log_vcd('syncPacket')

    # syncAck

    def cmd_sync_ack_clr(self):
        """ Emulates: void debugpins_syncAck_clr() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_sync_ack_clr')

        # change the internal state
        self.syncAckPinHigh = False

        # log VCD
        self._log_vcd('syncAck')

    def cmd_sync_ack_set(self):
        """ Emulates: void debugpins_syncAck_set() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_sync_ack_set')

        # change the internal state
        self.syncAckPinHigh = True

        # log VCD
        self._log_vcd('syncAck')

    # debug

    def cmd_debug_clr(self):
        """ Emulates: void debugpins_debug_clr() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_debug_clr')

        # change the internal state
        self.debugPinHigh = False

        # log VCD
        self._log_vcd('debug')

    def cmd_debug_set(self):
        """ Emulates: void debugpins_debug_set() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_debug_set')

        # change the internal state
        self.debugPinHigh = True

        # log VCD
        self._log_vcd('debug')

    # === getters

    def get_frame_pin_high(self):
        return self.framePinHigh

    def get_slot_pin_high(self):
        return self.slotPinHigh

    def get_fsm_pin_high(self):
        return self.fsmPinHigh

    def get_isr_pin_high(self):
        return self.isrPinHigh

    def get_radio_pin_high(self):
        return self.radioPinHigh

    def get_ka_pin_high(self):
        return self.kaPinHigh

    def get_sync_packet_pin_high(self):
        return self.syncPacketPinHigh

    def get_sync_ack_pin_high(self):
        return self.syncAckPinHigh

    def get_debug_pin_high(self):
        return self.debugPinHigh

    # ======================== private =========================================

    def _log_vcd(self, signal):
        if self.vcdlog:
            self.vcdLogger.log(
                ts=self.timeline.get_current_time(),
                mote=self.motehandler.get_id(),
                signal=signal,
                state=getattr(self, '{0}PinHigh'.format(signal)),
            )
