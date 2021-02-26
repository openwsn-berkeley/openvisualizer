# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import threading
from multiprocessing import get_logger

from openvisualizer.simulator.bspemulator.bspmodule import BspModule


class BspUart(BspModule):
    """ Emulates the 'uart' BSP module """

    INTR_TX = 'uart.tx'
    INTR_RX = 'uart.rx'
    BAUDRATE = 115200

    XOFF = 0x13
    XON = 0x11
    XONXOFF_ESCAPE = 0x12
    XONXOFF_MASK = 0x10

    def __init__(self, mote):
        # initialize the parent
        super(BspUart, self).__init__(mote)

        # logging
        self.logger = get_logger()
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

        # local variables
        self.interrupts_enabled = False
        self.tx_interrupt_flag = False
        self.rx_interrupt_flag = False

        self.uart_tx_buffer = []  # the bytes to be sent over UART
        self.uart_tx_next = None  # the byte that was just signaled to mote
        self.uart_tx_buffer_lock = threading.Lock()

        self.f_xon_xoff_escaping = False
        self.xon_xoff_escaped_byte = 0

        rx_thread = threading.Thread(target=self._listen_incoming)
        rx_thread.setDaemon(True)
        rx_thread.start()

    # ======================== public ==========================================

    # === commands

    def cmd_init(self):
        """ Emulates: void uart_init() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_init')

        # remember that module has been initialized
        self.is_initialized = True

    def cmd_enable_interrupts(self):
        """ Emulates: void uart_enableInterrupts() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_enable_interrupts')

        # update variables
        self.interrupts_enabled = True

    def cmd_disable_interrupts(self):
        """ Emulates: void cmd_disable_interrupts() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_disableInterrupts')

        # update variables
        self.interrupts_enabled = False

    def cmd_clear_rx_interrupts(self):
        """ Emulates: void uart_clearRxInterrupts() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_clear_rx_interrupts')

        # update variables
        self.rx_interrupt_flag = False

    def cmd_clear_tx_interrupts(self):
        """ Emulates: void uart_clearTxInterrupts() """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_clear_tx_interrupts')

        # update variables
        self.tx_interrupt_flag = False

    def cmd_write_byte(self, byte_to_write):
        """ Emulates: void uart_writeByte(uint8_t byte_to_write) """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_write_byte byte_to_write=' + str(byte_to_write))

        # set tx interrupt flag
        self.tx_interrupt_flag = True

        # calculate the time at which the byte will have been sent
        done_sending_time = self.mote.bsp_board.get_current_time() + float(1.0 / float(self.BAUDRATE))

        # schedule uart TX interrupt in 1/BAUDRATE seconds
        self.mote.bsp_board.schedule_intr(
            at_time=done_sending_time,
            mote_id=self.mote.mote_id,
            cb=self.intr_tx,
            desc=self.INTR_TX)

        if byte_to_write == self.XON or byte_to_write == self.XOFF or byte_to_write == self.XONXOFF_ESCAPE:
            self.f_xon_xoff_escaping = True
            self.xon_xoff_escaped_byte = byte_to_write

        try:
            self.mote.uart.tx.put([byte_to_write])
        except (EOFError, BrokenPipeError):
            self.logger.error('Queue closed')

    def cmd_set_cts(self, state):
        """ Emulates: void uart_setCTS(bool state) """
        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_set_cts state=' + str(state))

        # set tx interrupt flag
        self.tx_interrupt_flag = True

        # calculate the time at which the byte will have been sent
        done_sending_time = self.mote.bsp_board.get_current_time() + float(1.0 / float(self.BAUDRATE))

        # schedule uart TX interrupt in 1/BAUDRATE seconds
        self.mote.bsp_board.schedule_intr(
            at_time=done_sending_time,
            mote_id=self.mote.mote_id,
            cb=self.intr_tx,
            desc=self.INTR_TX)

        try:
            if state:
                self.mote.uart.tx.put([self.XON])
            else:
                self.mote.uart.tx.put([self.XOFF])
        except (EOFError, BrokenPipeError):
            self.logger.error('Queue closed')

    def cmd_write_circular_buffer_fastsim(self, buf):
        """ Emulates: void uart_writeCircularBuffer_FASTSIM(uint8_t* buffer, uint8_t len) """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_write_circular_buffer_fastsim buffer=' + str(buf))

        self._write_buffer(buf)

    def uart_write_buffer_by_len_fastsim(self, buf):
        """ Emulates: void uart_writeBufferByLen_FASTSIM(uint8_t* buffer, uint8_t len) """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('uart_write_buffer_by_len_fastsim buffer=' + str(buf))

        self._write_buffer(buf)

    def _write_buffer(self, buf):
        # set tx interrupt flag
        self.tx_interrupt_flag = True

        # calculate the time at which the buffer will have been sent
        done_sending_time = self.mote.bsp_board.get_current_time() + float(float(len(buf)) / float(self.BAUDRATE))

        # schedule uart TX interrupt in len(buffer)/BAUDRATE seconds
        self.mote.bsp_board.schedule_intr(
            at_time=done_sending_time,
            mote_id=self.mote.mote_id,
            cb=self.intr_tx,
            desc=self.INTR_TX)

        # add to receive buffer
        i = 0
        temp_buf = []

        while i != len(buf):
            if buf[i] == self.XON or buf[i] == self.XOFF or buf[i] == self.XONXOFF_ESCAPE:
                new_item = (self.XONXOFF_ESCAPE, buf[i] ^ self.XONXOFF_MASK)
                temp_buf.append(new_item[0])
                temp_buf.append(new_item[1])
            else:
                temp_buf.append(buf[i])
            i += 1

        try:
            self.mote.uart.tx.put([temp_buf])
        except (EOFError, BrokenPipeError):
            self.logger.error('Queue closed')

    def cmd_read_byte(self):
        """ Emulates: uint8_t uart_readByte()"""

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('cmd_read_byte')

        # retrieve the byte last sent
        with self.uart_tx_buffer_lock:
            return self.uart_tx_next

    # ======================== interrupts ======================================

    def intr_tx(self):
        """ Mote is done sending a byte over the UART. """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('intr_tx')

        if self.f_xon_xoff_escaping:
            self.f_xon_xoff_escaping = False

            # set tx interrupt flag
            self.tx_interrupt_flag = True

            # calculate the time at which the byte will have been sent
            done_sending_time = self.mote.bsp_board.get_current_time() + float(1.0 / float(self.BAUDRATE))

            # schedule uart TX interrupt in 1/BAUDRATE seconds
            self.mote.bsp_board.schedule_intr(
                at_time=done_sending_time,
                mote_id=self.mote.mote_id,
                cb=self.intr_tx,
                desc=self.INTR_TX)

            # add to receive buffer
            try:
                self.mote.uart.tx.put([self.xon_xoff_escaped_byte ^ self.XONXOFF_MASK])
            except (EOFError, BrokenPipeError):
                self.logger.error('Queue closed')

        else:
            # send interrupt to mote
            self.mote.mote.uart_isr_tx()

        # do *not* kick the scheduler
        return False

    def intr_rx(self):
        """ Interrupt to indicate to mote it received a byte from the UART. """

        # log the activity
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('intr_rx')

        with self.uart_tx_buffer_lock:

            # make sure there is a byte to TX
            assert len(self.uart_tx_buffer)

            # get the byte that is being transmitted
            self.uart_tx_next = self.uart_tx_buffer.pop(0)

            # schedule the next interrupt, if any bytes left
            if len(self.uart_tx_buffer):
                self._schedule_next_tx()

        # send RX interrupt to mote
        self.mote.mote.uart_isr_rx()

        # do *not* kick the scheduler
        return False

    # ======================== private =========================================

    def _schedule_next_tx(self):
        # calculate time at which byte will get out
        time_next_tx = self.mote.bsp_board.get_current_time() + float(1.0 / float(self.BAUDRATE))

        # schedule that event
        self.mote.bsp_board.schedule_intr(
            at_time=time_next_tx,
            mote_id=self.mote.mote_id,
            cb=self.intr_rx,
            desc=self.INTR_RX,
        )

    def _listen_incoming(self):
        while True:
            try:
                rcv_buf = self.mote.uart.rx.get()
            except (EOFError, BrokenPipeError):
                self.logger.error('Queue closed')
                break

            with self.uart_tx_buffer_lock:
                self.uart_tx_buffer.extend(rcv_buf)

            self._schedule_next_tx()
