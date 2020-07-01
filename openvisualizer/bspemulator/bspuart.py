# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import threading

from openvisualizer.bspemulator.bspmodule import BspModule


class BspUart(BspModule):
    """ Emulates the 'uart' BSP module """

    _name = 'BspUart'

    INTR_TX = 'uart.tx'
    INTR_RX = 'uart.rx'
    BAUDRATE = 115200

    XOFF = 0x13
    XON = 0x11
    XONXOFF_ESCAPE = 0x12
    XONXOFF_MASK = 0x10

    def __init__(self, motehandler):
        # initialize the parent
        super(BspUart, self).__init__(motehandler)

        # local variables
        self.timeline = self.engine.timeline
        self.interrupts_enabled = False
        self.tx_interrupt_flag = False
        self.rx_interrupt_flag = False
        self.uart_rx_buffer = []
        self.uart_rx_buffer_sem = threading.Semaphore()
        self.uart_rx_buffer_sem.acquire()
        self.uart_rx_buffer_lock = threading.Lock()
        self.uart_tx_buffer = []  # the bytes to be sent over UART
        self.uart_tx_next = None  # the byte that was just signaled to mote
        self.uart_tx_buffer_lock = threading.Lock()
        self.wait_for_done_reading = threading.Lock()
        self.wait_for_done_reading.acquire()
        self.f_xon_xoff_escaping = False
        self.xon_xoff_escaped_byte = 0

    # ======================== public ==========================================

    # === interact with UART

    def read(self):
        """ Read a byte from the mote. """

        # wait for something to appear in the RX buffer
        self.uart_rx_buffer_sem.acquire()

        # copy uart_rx_buffer
        with self.uart_rx_buffer_lock:
            assert len(self.uart_rx_buffer) > 0
            return_val = [chr(b) for b in self.uart_rx_buffer]
            self.uart_rx_buffer = []

        # return that element
        return return_val

    def write(self, bytes_to_write):
        """ Write a string of bytes to the mote. """

        assert len(bytes_to_write)

        if len(self.uart_tx_buffer) != 0:
            return 0

        with self.uart_tx_buffer_lock:
            self.uart_tx_buffer = [ord(b) for b in bytes_to_write]

        self.engine.pause()
        self._schedule_next_tx()
        self.engine.resume()

        return len(bytes_to_write)

    def done_reading(self):
        self.wait_for_done_reading.release()

    # === commands

    def cmd_init(self):
        """ Emulates: void uart_init() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_init')

        # remember that module has been intialized
        self.is_initialized = True

    def cmd_enable_interrupts(self):
        """ Emulates: void uart_enableInterrupts() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_enable_interrupts')

        # update variables
        self.interrupts_enabled = True

    def cmd_disable_interrupts(self):
        """ Emulates: void cmd_disable_interrupts() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_disableInterrupts')

        # update variables
        self.interrupts_enabled = False

    def cmd_clear_rx_interrupts(self):
        """ Emulates: void uart_clearRxInterrupts() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_clear_rx_interrupts')

        # update variables
        self.rx_interrupt_flag = False

    def cmd_clear_tx_interrupts(self):
        """ Emulates: void uart_clearTxInterrupts() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_clear_tx_interrupts')

        # update variables
        self.tx_interrupt_flag = False

    def cmd_write_byte(self, byte_to_write):
        """ Emulates: void uart_writeByte(uint8_t byte_to_write) """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_write_byte byte_to_write=' + str(byte_to_write))

        # set tx interrupt flag
        self.tx_interrupt_flag = True

        # calculate the time at which the byte will have been sent
        done_sending_time = self.timeline.get_current_time() + float(1.0 / float(self.BAUDRATE))

        # schedule uart TX interrupt in 1/BAUDRATE seconds
        self.timeline.schedule_event(done_sending_time, self.motehandler.get_id(), self.intr_tx, self.INTR_TX)

        if byte_to_write == self.XON or byte_to_write == self.XOFF or byte_to_write == self.XONXOFF_ESCAPE:
            self.f_xon_xoff_escaping = True
            self.xon_xoff_escaped_byte = byte_to_write
            # add to receive buffer
            with self.uart_rx_buffer_lock:
                self.uart_rx_buffer += [self.XONXOFF_ESCAPE]
        else:
            # add to receive buffer
            with self.uart_rx_buffer_lock:
                self.uart_rx_buffer += [byte_to_write]

        # release the semaphore indicating there is something in RX buffer
        self.uart_rx_buffer_sem.release()

        # wait for the moteProbe to be done reading
        self.wait_for_done_reading.acquire()

    def cmd_set_cts(self, state):
        """ Emulates: void uart_setCTS(bool state) """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_set_cts state=' + str(state))

        # set tx interrupt flag
        self.tx_interrupt_flag = True

        # calculate the time at which the byte will have been sent
        done_sending_time = self.timeline.get_current_time() + float(1.0 / float(self.BAUDRATE))

        # schedule uart TX interrupt in 1/BAUDRATE seconds
        self.timeline.schedule_event(done_sending_time, self.motehandler.get_id(), self.intr_tx, self.INTR_TX)

        # add to receive buffer
        with self.uart_rx_buffer_lock:
            if state:
                self.uart_rx_buffer += [self.XON]
            else:
                self.uart_rx_buffer += [self.XOFF]

        # release the semaphore indicating there is something in RX buffer
        self.uart_rx_buffer_sem.release()

        # wait for the moteProbe to be done reading
        self.wait_for_done_reading.acquire()

    def cmd_write_circular_buffer_fastsim(self, buf):
        """ Emulates: void uart_writeCircularBuffer_FASTSIM(uint8_t* buffer, uint8_t len) """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_write_circular_buffer_fastsim buffer=' + str(buf))

        self._write_buffer(buf)

    def uart_write_buffer_by_len_fastsim(self, buf):
        """ Emulates: void uart_writeBufferByLen_FASTSIM(uint8_t* buffer, uint8_t len) """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('uart_write_buffer_by_len_fastsim buffer=' + str(buf))

        self._write_buffer(buf)

    def _write_buffer(self, buf):
        # set tx interrupt flag
        self.tx_interrupt_flag = True

        # calculate the time at which the buffer will have been sent
        done_sending_time = self.timeline.get_current_time() + float(float(len(buf)) / float(self.BAUDRATE))

        # schedule uart TX interrupt in len(buffer)/BAUDRATE seconds
        self.timeline.schedule_event(done_sending_time, self.motehandler.get_id(), self.intr_tx, self.INTR_TX)

        # add to receive buffer
        with self.uart_rx_buffer_lock:
            i = 0
            while i != len(buf):
                if buf[i] == self.XON or buf[i] == self.XOFF or buf[i] == self.XONXOFF_ESCAPE:
                    new_item = (self.XONXOFF_ESCAPE, buf[i] ^ self.XONXOFF_MASK)
                    buf[i:i + 1] = new_item
                i += 1
            self.uart_rx_buffer += buf

        # release the semaphore indicating there is something in RX buffer
        self.uart_rx_buffer_sem.release()

        # wait for the moteProbe to be done reading
        self.wait_for_done_reading.acquire()

    def cmd_read_byte(self):
        """ Emulates: uint8_t uart_readByte()"""

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_read_byte')

        # retrieve the byte last sent
        with self.uart_tx_buffer_lock:
            return self.uart_tx_next

    # ======================== interrupts ======================================

    def intr_tx(self):
        """ Mote is done sending a byte over the UART. """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('intr_tx')

        if self.f_xon_xoff_escaping:
            self.f_xon_xoff_escaping = False

            # set tx interrupt flag
            self.tx_interrupt_flag = True

            # calculate the time at which the byte will have been sent
            done_sending_time = self.timeline.get_current_time() + float(1.0 / float(self.BAUDRATE))

            # schedule uart TX interrupt in 1/BAUDRATE seconds
            self.timeline.schedule_event(done_sending_time, self.motehandler.get_id(), self.intr_tx, self.INTR_TX)

            # add to receive buffer
            with self.uart_rx_buffer_lock:
                self.uart_rx_buffer += [self.xon_xoff_escaped_byte ^ self.XONXOFF_MASK]

            # release the semaphore indicating there is something in RX buffer
            self.uart_rx_buffer_sem.release()

            # wait for the moteProbe to be done reading
            self.wait_for_done_reading.acquire()

        else:
            # send interrupt to mote
            self.motehandler.mote.uart_isr_tx()

        # do *not* kick the scheduler
        return False

    def intr_rx(self):
        """ Interrupt to indicate to mote it received a byte from the UART. """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('intr_rx')

        with self.uart_tx_buffer_lock:

            # make sure there is a byte to TX
            assert len(self.uart_tx_buffer)

            # get the byte that is being transmitted
            self.uart_tx_next = self.uart_tx_buffer.pop(0)

            # schedule the next interrupt, if any bytes left
            if len(self.uart_tx_buffer):
                self._schedule_next_tx()

        # send RX interrupt to mote
        self.motehandler.mote.uart_isr_rx()

        # do *not* kick the scheduler
        return False

    # ======================== private =========================================

    def _schedule_next_tx(self):

        # calculate time at which byte will get out
        time_next_tx = self.timeline.get_current_time() + float(1.0 / float(self.BAUDRATE))

        # schedule that event
        self.timeline.schedule_event(
            time_next_tx,
            self.motehandler.get_id(),
            self.intr_rx,
            self.INTR_RX,
        )
