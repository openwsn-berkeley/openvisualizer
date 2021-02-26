# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import threading
from multiprocessing import get_logger

from openvisualizer.simulator.bspemulator.bspmodule import BspModule


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


class BspRadio(BspModule):
    """ Emulates the 'radio' BSP module """

    INTR_STARTOFFRAME_MOTE = 'radio.startofframe_fromMote'
    INTR_ENDOFFRAME_MOTE = 'radio.endofframe_fromMote'
    INTR_STARTOFFRAME_PROPAGATION = 'radio.startofframe_fromPropagation'
    INTR_ENDOFFRAME_PROPAGATION = 'radio.endofframe_fromPropagation'

    def __init__(self, mote):

        # initialize the parents
        BspModule.__init__(self, mote)

        # local variables

        # local variables
        self.frequency = None  # frequency the radio is tuned to
        self.is_rf_on = False  # radio is off
        self.tx_buf = []
        self.rx_buf = []
        self.delay_tx = 0.000214
        self.rssi = -50
        self.lqi = 100
        self.crc_passes = True

        # logging
        self.logger = get_logger()
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

        # set initial state
        self._change_state(RadioState.STOPPED)

        rx_thread = threading.Thread(target=self._listen_incoming)
        rx_thread.setDaemon(True)
        rx_thread.start()

    # ======================== public ==========================================

    # === commands

    def cmd_init(self):
        """ Emulates: void radio_init() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_init')

        # change state
        self._change_state(RadioState.STOPPED)

        # remember that module has been intialized
        self.is_initialized = True

        # change state
        self._change_state(RadioState.RFOFF)

    def cmd_reset(self):
        """ Emulates: void radio_reset() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_reset')

        # change state
        self._change_state(RadioState.STOPPED)

    def cmd_set_frequency(self, frequency):
        """ Emulates: void radio_setFrequency(uint8_t frequency) """

        # store params
        self.frequency = frequency

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_set_frequency frequency=' + str(self.frequency))

        # change state
        self._change_state(RadioState.SETTING_FREQUENCY)

        # change state
        self._change_state(RadioState.FREQUENCY_SET)

    def cmd_rf_on(self):
        """ Emulates: void radio_rfOn() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_rf_on')

        # update local variable
        self.is_rf_on = True

    def cmd_rf_off(self):
        """ Emulates: void radio_rfOff() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_rf_off')

        # change state
        self._change_state(RadioState.TURNING_OFF)

        # update local variable
        self.is_rf_on = False

        # change state
        self._change_state(RadioState.RFOFF)

        # wiggle de debugpin
        self.mote.bsp_debugpins.cmd_radio_clr()

    def cmd_load_packet(self, packet_to_load):
        """ Emulates: void radio_loadPacket(uint8_t* packet, uint8_t len) """

        # make sure length of params is expected
        assert (len(packet_to_load) <= 127)

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_load_packet len={0}'.format(len(packet_to_load)))

        # change state
        self._change_state(RadioState.LOADING_PACKET)

        # update local variable
        self.tx_buf = [len(packet_to_load)] + packet_to_load

        # log
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('tx_buf={0}'.format(self.tx_buf))

        # change state
        self._change_state(RadioState.PACKET_LOADED)

    def cmd_tx_enable(self):
        """ Emulates: void radio_txEnable() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_tx_enable')

        # change state
        self._change_state(RadioState.ENABLING_TX)

        # change state
        self._change_state(RadioState.TX_ENABLED)

        # wiggle de debugpin
        self.mote.bsp_debugpins.cmd_radio_set()

    def cmd_tx_now(self):
        """ Emulates: void radio_txNow() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_tx_now')

        # change state
        self._change_state(RadioState.TRANSMITTING)

        # get current time
        current_time = self.mote.bsp_board.get_current_time()

        # calculate when the "start of frame" event will take place
        start_of_frame_time = current_time + self.delay_tx

        # schedule "start of frame" event
        self.mote.bsp_board.schedule_intr(
            at_time=start_of_frame_time,
            mote_id=self.mote.mote_id,
            cb=self.intr_start_of_frame_from_mote,
            desc=self.INTR_STARTOFFRAME_MOTE)

    def cmd_rx_enable(self):
        """ Emulates: void radio_rxEnable() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_rx_enable')

        # change state
        self._change_state(RadioState.ENABLING_RX)

        # change state
        self._change_state(RadioState.LISTENING)

        # wiggle de debugpin
        self.mote.bsp_debugpins.cmd_radio_set()

    def cmd_rx_now(self):
        """ Emulates: void radio_rxNow() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_rx_now')

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
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_get_received_frame')

        # ==== prepare response
        rssi = self.rssi
        lqi = self.lqi
        crc = self.crc_passes

        # respond
        return self.rx_buf, rssi, lqi, crc

    # ======================== interrupts ======================================

    def intr_start_of_frame_from_mote(self):

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Sending packet from {self.mote.mote_id}")

        try:
            self.mote.radio.tx.put([self.mote.mote_id, self.tx_buf, self.frequency])
            # wait until we get the 'go' from the propagation thread
            self.mote.radio.tx.join()
        except (EOFError, BrokenPipeError):
            self.logger.error('Queue closed')

        current_time = self.mote.bsp_board.get_current_time()
        end_of_frame_time = current_time + BspRadio._packet_length_to_duration(len(self.tx_buf))

        self.mote.bsp_board.schedule_intr(
            at_time=end_of_frame_time,
            mote_id=self.mote.mote_id,
            cb=self.intr_end_of_frame_from_mote,
            desc=self.INTR_ENDOFFRAME_MOTE,
        )

        # signal start of frame to mote
        counter_val = self.mote.bsp_sctimer.cmd_read_counter()

        # indicate to the mote
        self.mote.mote.radio_isr_startFrame(counter_val)

        # kick the scheduler
        return True

    def intr_start_of_frame_from_propagation(self):

        # signal start of frame to mote
        counter_val = self.mote.bsp_sctimer.cmd_read_counter() + 36

        # log
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('intr_start_of_frame_from_propagation counter_val={0}'.format(counter_val))

        # indicate to mote
        self.mote.mote.radio_isr_startFrame(counter_val)

        # kick the scheduler
        return True

    def intr_end_of_frame_from_mote(self):

        # signal end of frame to mote
        counter_val = self.mote.bsp_sctimer.cmd_read_counter()

        # indicate to the mote
        self.mote.mote.radio_isr_endFrame(counter_val)

        # kick the scheduler
        return True

    def intr_end_of_frame_from_propagation(self):

        # signal end of frame to mote
        counter_val = self.mote.bsp_sctimer.cmd_read_counter()

        # log
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('intr_end_of_frame_from_propagation counter_val={0}'.format(counter_val))

        # indicate to the mote
        self.mote.mote.radio_isr_endFrame(counter_val)

        # kick the scheduler
        return True

    # ======================== indication from Topology =====================

    def _listen_incoming(self):
        while True:
            try:
                origin, packet, channel = self.mote.radio.rx.get()
            except EOFError:
                self.logger.error('Queue closed')
                break

            if self.is_initialized and self.state == RadioState.LISTENING and self.frequency == channel:

                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"Got message from mote_{origin} length {packet[0]} bytes (channel={channel})")

                self.rx_buf = [i[0] for i in packet[1:]]

                # schedule start of frame
                self.mote.bsp_board.schedule_intr(
                    at_time=self.mote.bsp_board.get_current_time(),
                    mote_id=self.mote.mote_id,
                    cb=self.intr_start_of_frame_from_propagation,
                    desc=self.INTR_STARTOFFRAME_PROPAGATION,
                )

                # schedule end of frame
                end_of_frame_time = \
                    self.mote.bsp_board.get_current_time() + BspRadio._packet_length_to_duration(len(self.rx_buf))
                self.mote.bsp_board.schedule_intr(
                    at_time=end_of_frame_time,
                    mote_id=self.mote.mote_id,
                    cb=self.intr_end_of_frame_from_propagation,
                    desc=self.INTR_ENDOFFRAME_PROPAGATION,
                )

            elif self.frequency != channel:
                self.logger.debug(f"Wrong channel: {self.frequency} != {channel}")
            else:
                # just drop the packet
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"[{self.mote.mote_id - 1}] Radio not in correct state: {self.state}")

            # notify the propagation thread that we are done here
            self.mote.radio.rx.task_done()

    # ======================== private =========================================

    @staticmethod
    def _packet_length_to_duration(num_bytes):
        return float(num_bytes * 8) / 250000.0

    def _change_state(self, new_state):
        self.state = new_state
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('state={0}'.format(self.state))
