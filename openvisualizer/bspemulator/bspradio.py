# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging

from openvisualizer.bspemulator.bspmodule import BspModule
from openvisualizer.simengine import propagation
from openvisualizer.eventbus.eventbusclient import EventBusClient


class RadioState:
    STOPPED = 'STOPPED'  # Completely stopped.
    RFOFF = 'RFOFF'  # Listening for commands by RF chain is off.
    SETTING_FREQUENCY = 'SETTING_FREQUENCY'  # Configuring the frequency.
    FREQUENCY_SET = 'FREQUENCY_SET'  # Done configuring the frequency.
    LOADING_PACKET = 'LOADING_PACKET'  # Loading packet to send over SPI.
    PACKET_LOADED = 'PACKET_LOADED'  # Packet is loaded in the TX buffer.
    ENABLING_TX = 'ENABLING_TX'  # The RF Tx chaing is being enabled (includes locked the PLL).
    TX_ENABLED = 'TX_ENABLED'  # Radio completely ready to transmit.
    TRANSMITTING = 'TRANSMITTING'  # Busy transmitting bytes.
    ENABLING_RX = 'ENABLING_RX'  # The RF Rx chaing is being enabled (includes locked the PLL).
    LISTENING = 'LISTENING'  # RF chain is on, listening, but no packet received yet.
    RECEIVING = 'RECEIVING'  # Busy receiving bytes.
    TXRX_DONE = 'TXRX_DONE'  # Frame has been sent/received completely.
    TURNING_OFF = 'TURNING_OFF'  # Turning the RF chain off.


class BspRadio(BspModule, EventBusClient):
    """ Emulates the 'radio' BSP module """

    _name = 'BspRadio'

    INTR_STARTOFFRAME_MOTE = 'radio.startofframe_fromMote'
    INTR_ENDOFFRAME_MOTE = 'radio.endofframe_fromMote'
    INTR_STARTOFFRAME_PROPAGATION = 'radio.startofframe_fromPropagation'
    INTR_ENDOFFRAME_PROPAGATION = 'radio.endofframe_fromPropagation'

    def __init__(self, motehandler):

        # initialize the parents
        BspModule.__init__(self, motehandler)
        EventBusClient.__init__(self, name='BspRadio_{0}'.format(self.motehandler.get_id()), registrations=[])

        # local variables
        self.timeline = self.engine.timeline
        self.propagation = self.engine.propagation
        self.sctimer = self.motehandler.bsp_sctimer

        # local variables
        self.frequency = None  # frequency the radio is tuned to
        self.is_rf_on = False  # radio is off
        self.tx_buf = []
        self.rx_buf = []
        self.delay_tx = 0.000214
        self.rssi = -50
        self.lqi = 100
        self.crc_passes = True

        # set initial state
        self._change_state(RadioState.STOPPED)

    # ======================== public ==========================================

    # === commands

    def cmd_init(self):
        """ Emulates: void radio_init() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_init')

        # change state
        self._change_state(RadioState.STOPPED)

        # remember that module has been intialized
        self.is_initialized = True

        # change state
        self._change_state(RadioState.RFOFF)

    def cmd_reset(self):
        """ Emulates: void radio_reset() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_reset')

        # change state
        self._change_state(RadioState.STOPPED)

    def cmd_set_frequency(self, frequency):
        """ Emulates: void radio_setrequency(uint8_t frequency) """

        # store params
        self.frequency = frequency

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_set_frequency frequency=' + str(self.frequency))

        # change state
        self._change_state(RadioState.SETTING_FREQUENCY)

        # change state
        self._change_state(RadioState.FREQUENCY_SET)

    def cmd_rf_on(self):
        """ Emulates: void radio_rfOn() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_rf_on')

        # update local variable
        self.is_rf_on = True

    def cmd_rf_off(self):
        """ Emulates: void radio_rfOff() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_rf_off')

        # change state
        self._change_state(RadioState.TURNING_OFF)

        # update local variable
        self.is_rf_on = False

        # change state
        self._change_state(RadioState.RFOFF)

        # wiggle de debugpin
        self.motehandler.bsp_debugpins.cmd_radio_clr()

    def cmd_load_packet(self, packet_to_load):
        """ Emulates: void radio_loadPacket(uint8_t* packet, uint8_t len) """

        # make sure length of params is expected
        assert (len(packet_to_load) <= 127)

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_load_packet len={0}'.format(len(packet_to_load)))

        # change state
        self._change_state(RadioState.LOADING_PACKET)

        # update local variable
        self.tx_buf = [len(packet_to_load)] + packet_to_load

        # log
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('tx_buf={0}'.format(self.tx_buf))

        # change state
        self._change_state(RadioState.PACKET_LOADED)

    def cmd_tx_enable(self):
        """ Emulates: void radio_txEnable() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_tx_enable')

        # change state
        self._change_state(RadioState.ENABLING_TX)

        # change state
        self._change_state(RadioState.TX_ENABLED)

        # wiggle de debugpin
        self.motehandler.bsp_debugpins.cmd_radio_set()

    def cmd_tx_now(self):
        """ Emulates: void radio_txNow() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_tx_now')

        # change state
        self._change_state(RadioState.TRANSMITTING)

        # get current time
        current_time = self.timeline.get_current_time()

        # calculate when the "start of frame" event will take place
        start_of_frame_time = current_time + self.delay_tx

        # schedule "start of frame" event
        self.timeline.schedule_event(start_of_frame_time,
                                     self.motehandler.get_id(),
                                     self.intr_start_of_frame_from_mote,
                                     self.INTR_STARTOFFRAME_MOTE)

    def cmd_rx_enable(self):
        """ Emulates: void radio_rxEnable() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_rx_enable')

        # change state
        self._change_state(RadioState.ENABLING_RX)

        # change state
        self._change_state(RadioState.LISTENING)

        # wiggle de debugpin
        self.motehandler.bsp_debugpins.cmd_radio_set()

    def cmd_rx_now(self):
        """ Emulates: void radio_rxNow() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_rx_now')

        # change state
        self._change_state(RadioState.LISTENING)

    def cmd_get_received_frame(self):
        """ Emulates:
           void radio_getReceivedFrame(
           uint8_t* pBufRead,
           uint8_t* pLenRead,
           uint8_t  maxBufLen,
           int8_t*  pRssi,
           uint8_t* pLqi,
           uint8_t* pCrc) """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_get_received_frame')

        # ==== prepare response
        rx_buffer = self.rx_buf[1:]
        rssi = self.rssi
        lqi = self.lqi
        crc = self.crc_passes

        # respond
        return rx_buffer, rssi, lqi, crc

    # ======================== interrupts ======================================

    def intr_start_of_frame_from_mote(self):

        # indicate transmission starts on eventBus
        self.dispatch(
            signal=propagation.Propagation.SIGNAL_WIRELESSTXSTART,
            data=(self.motehandler.get_id(), self.tx_buf, self.frequency),
        )

        # schedule the "end of frame" event
        current_time = self.timeline.get_current_time()
        end_of_frame_time = current_time + BspRadio._packet_length_to_duration(len(self.tx_buf))
        self.timeline.schedule_event(
            end_of_frame_time,
            self.motehandler.get_id(),
            self.intr_end_of_frame_from_mote,
            self.INTR_ENDOFFRAME_MOTE,
        )

        # signal start of frame to mote
        counter_val = self.sctimer.cmd_read_counter()

        # indicate to the mote
        self.motehandler.mote.radio_isr_startFrame(counter_val)

        # kick the scheduler
        return True

    def intr_start_of_frame_from_propagation(self):

        # signal start of frame to mote
        counter_val = self.sctimer.cmd_read_counter()

        # indicate to the mote
        self.motehandler.mote.radio_isr_startFrame(counter_val)

        # do NOT kick the scheduler
        return True

    def intr_end_of_frame_from_mote(self):

        # indicate transmission ends on eventBus
        self.dispatch(
            signal=propagation.Propagation.SIGNAL_WIRELESSTXEND,
            data=self.motehandler.get_id(),
        )

        # signal end of frame to mote
        counter_val = self.sctimer.cmd_read_counter()

        # indicate to the mote
        self.motehandler.mote.radio_isr_endFrame(counter_val)

        # kick the scheduler
        return True

    def intr_end_of_frame_from_propagation(self):

        # signal end of frame to mote
        counter_val = self.sctimer.cmd_read_counter()

        # log
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('intr_end_of_frame_from_propagation counter_val={0}'.format(counter_val))

        # indicate to the mote
        self.motehandler.mote.radio_isr_endFrame(counter_val)

        # do NOT kick the scheduler
        return True

    # ======================== indication from Propagation =====================

    def indicate_tx_start(self, mote_id, packet, channel):

        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug(
                'indicate_tx_start from mote_id={0} channel={1} len={2}'.format(mote_id, channel, len(packet)))

        if self.is_initialized and self.state == RadioState.LISTENING and self.frequency == channel:
            self._change_state(RadioState.RECEIVING)

            self.rx_buf = packet

            # log
            if self.log.isEnabledFor(logging.DEBUG):
                self.log.debug('rx_buf={0}'.format(self.rx_buf))

            # schedule start of frame
            self.timeline.schedule_event(
                self.timeline.get_current_time(),
                self.motehandler.get_id(),
                self.intr_start_of_frame_from_propagation,
                self.INTR_STARTOFFRAME_PROPAGATION,
            )

    def indicate_tx_end(self, mote_id):

        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('indicate_tx_end from mote_id={0}'.format(mote_id))

        if self.is_initialized and self.state == RadioState.RECEIVING:
            self._change_state(RadioState.LISTENING)

            # schedule end of frame
            self.timeline.schedule_event(
                self.timeline.get_current_time(),
                self.motehandler.get_id(),
                self.intr_end_of_frame_from_propagation,
                self.INTR_ENDOFFRAME_PROPAGATION,
            )

    # ======================== private =========================================

    @staticmethod
    def _packet_length_to_duration(num_bytes):
        return float(num_bytes * 8) / 250000.0

    def _change_state(self, new_state):
        self.state = new_state
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('state={0}'.format(self.state))
