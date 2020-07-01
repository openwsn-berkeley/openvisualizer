#!/usr/bin/python
# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import threading

from openvisualizer.bspemulator import bspboard
from openvisualizer.bspemulator import bspdebugpins
from openvisualizer.bspemulator import bspeui64
from openvisualizer.bspemulator import bspleds
from openvisualizer.bspemulator import bspradio
from openvisualizer.bspemulator import bspsctimer
from openvisualizer.bspemulator import bspuart
from openvisualizer.bspemulator import hwcrystal
from openvisualizer.bspemulator import hwsupply
from openvisualizer.simengine import simengine

# ============================ get notification IDs ============================
# Contains the list of notifIds used in the following functions.
notif_string = []


def read_notif_ids(header_path):
    """
    Contextual parent must call this method before other use of mote handler.

    ``header_path`` Path to openwsnmodule_obj.h, containing notifIds

    Required since this module cannot know where to find the header file.
    """

    import re

    f = open(header_path)
    lines = f.readlines()
    f.close()

    global notif_string
    for line in lines:
        m = re.search('MOTE_NOTIF_([a-zA-Z0-9_]+)', line)
        if m:
            if m.group(1) not in notif_string:
                notif_string += [m.group(1)]


def notif_id(s):
    assert s in notif_string
    return notif_string.index(s)


# ============================ classes =========================================

class MoteHandler(threading.Thread):

    def __init__(self, mote, vcdlog):

        # store params
        self.engine = simengine.SimEngine()
        self.mote = mote

        # === local variables
        self.loghandler = self.engine.log_handler
        # unique identifier of the mote
        self.id = self.engine.id_manager.get_id()
        # position of the mote
        self.location = self.engine.location_manager.get_location()
        # stats
        self.num_rx_commands = 0
        self.num_tx_commands = 0
        # hw
        self.hw_supply = hwsupply.HwSupply(self)
        self.hw_crystal = hwcrystal.HwCrystal(self)
        # bsp
        self.bsp_board = bspboard.BspBoard(self)
        self.bsp_debugpins = bspdebugpins.BspDebugPins(self, vcdlog)
        self.bsp_eui64 = bspeui64.BspEui64(self)
        self.bsp_leds = bspleds.BspLeds(self)
        self.bsp_sctimer = bspsctimer.BspSctimer(self)
        self.bsp_radio = bspradio.BspRadio(self)
        self.bsp_uart = bspuart.BspUart(self)
        # status
        self.booted = False
        self.cpu_running = threading.Lock()
        self.cpu_running.acquire()
        self.cpu_done = threading.Lock()
        self.cpu_done.acquire()

        # === install callbacks
        # board
        mote.set_callback(notif_id('board_init'), self.bsp_board.cmd_init)
        mote.set_callback(notif_id('board_sleep'), self.bsp_board.cmd_sleep)
        # debugpins
        mote.set_callback(notif_id('debugpins_init'), self.bsp_debugpins.cmd_init)
        mote.set_callback(notif_id('debugpins_frame_toggle'), self.bsp_debugpins.cmd_frame_toggle)
        mote.set_callback(notif_id('debugpins_frame_clr'), self.bsp_debugpins.cmd_frame_clr)
        mote.set_callback(notif_id('debugpins_frame_set'), self.bsp_debugpins.cmd_frame_set)
        mote.set_callback(notif_id('debugpins_slot_toggle'), self.bsp_debugpins.cmd_slot_toggle)
        mote.set_callback(notif_id('debugpins_slot_clr'), self.bsp_debugpins.cmd_slot_clr)
        mote.set_callback(notif_id('debugpins_slot_set'), self.bsp_debugpins.cmd_slot_set)
        mote.set_callback(notif_id('debugpins_fsm_toggle'), self.bsp_debugpins.cmd_fsm_toggle)
        mote.set_callback(notif_id('debugpins_fsm_clr'), self.bsp_debugpins.cmd_fsm_clr)
        mote.set_callback(notif_id('debugpins_fsm_set'), self.bsp_debugpins.cmd_fsm_set)
        mote.set_callback(notif_id('debugpins_task_toggle'), self.bsp_debugpins.cmd_task_toggle)
        mote.set_callback(notif_id('debugpins_task_clr'), self.bsp_debugpins.cmd_task_clr)
        mote.set_callback(notif_id('debugpins_task_set'), self.bsp_debugpins.cmd_task_set)
        mote.set_callback(notif_id('debugpins_isr_toggle'), self.bsp_debugpins.cmd_isr_toggle)
        mote.set_callback(notif_id('debugpins_isr_clr'), self.bsp_debugpins.cmd_isr_clr)
        mote.set_callback(notif_id('debugpins_isr_set'), self.bsp_debugpins.cmd_isr_set)
        mote.set_callback(notif_id('debugpins_radio_toggle'), self.bsp_debugpins.cmd_radio_toggle)
        mote.set_callback(notif_id('debugpins_radio_clr'), self.bsp_debugpins.cmd_radio_clr)
        mote.set_callback(notif_id('debugpins_radio_set'), self.bsp_debugpins.cmd_radio_set)
        mote.set_callback(notif_id('debugpins_ka_clr'), self.bsp_debugpins.cmd_ka_clr)
        mote.set_callback(notif_id('debugpins_ka_set'), self.bsp_debugpins.cmd_ka_set)
        mote.set_callback(notif_id('debugpins_syncPacket_clr'), self.bsp_debugpins.cmd_sync_packet_clr)
        mote.set_callback(notif_id('debugpins_syncPacket_set'), self.bsp_debugpins.cmd_sync_packet_set)
        mote.set_callback(notif_id('debugpins_syncAck_clr'), self.bsp_debugpins.cmd_sync_ack_clr)
        mote.set_callback(notif_id('debugpins_syncAck_set'), self.bsp_debugpins.cmd_sync_ack_set)
        mote.set_callback(notif_id('debugpins_debug_clr'), self.bsp_debugpins.cmd_debug_clr)
        mote.set_callback(notif_id('debugpins_debug_set'), self.bsp_debugpins.cmd_debug_set)
        # eui64
        mote.set_callback(notif_id('eui64_get'), self.bsp_eui64.cmd_get)
        # leds
        mote.set_callback(notif_id('leds_init'), self.bsp_leds.cmd_init)
        mote.set_callback(notif_id('leds_error_on'), self.bsp_leds.cmd_error_on)
        mote.set_callback(notif_id('leds_error_off'), self.bsp_leds.cmd_error_off)
        mote.set_callback(notif_id('leds_error_toggle'), self.bsp_leds.cmd_error_toggle)
        mote.set_callback(notif_id('leds_error_isOn'), self.bsp_leds.cmd_error_is_on)
        mote.set_callback(notif_id('leds_radio_on'), self.bsp_leds.cmd_radio_on)
        mote.set_callback(notif_id('leds_radio_off'), self.bsp_leds.cmd_radio_off)
        mote.set_callback(notif_id('leds_radio_toggle'), self.bsp_leds.cmd_radio_toggle)
        mote.set_callback(notif_id('leds_radio_isOn'), self.bsp_leds.cmd_radio_is_on)
        mote.set_callback(notif_id('leds_sync_on'), self.bsp_leds.cmd_sync_on)
        mote.set_callback(notif_id('leds_sync_off'), self.bsp_leds.cmd_sync_off)
        mote.set_callback(notif_id('leds_sync_toggle'), self.bsp_leds.cmd_sync_toggle)
        mote.set_callback(notif_id('leds_sync_isOn'), self.bsp_leds.cmd_sync_is_on)
        mote.set_callback(notif_id('leds_debug_on'), self.bsp_leds.cmd_debug_on)
        mote.set_callback(notif_id('leds_debug_off'), self.bsp_leds.cmd_debug_off)
        mote.set_callback(notif_id('leds_debug_toggle'), self.bsp_leds.cmd_debug_toggle)
        mote.set_callback(notif_id('leds_debug_isOn'), self.bsp_leds.cmd_debug_is_on)
        mote.set_callback(notif_id('leds_all_on'), self.bsp_leds.cmd_all_on)
        mote.set_callback(notif_id('leds_all_off'), self.bsp_leds.cmd_all_off)
        mote.set_callback(notif_id('leds_all_toggle'), self.bsp_leds.cmd_all_toggle)
        mote.set_callback(notif_id('leds_circular_shift'), self.bsp_leds.cmd_circular_shift)
        mote.set_callback(notif_id('leds_increment'), self.bsp_leds.cmd_increment)
        # radio
        mote.set_callback(notif_id('radio_init'), self.bsp_radio.cmd_init)
        mote.set_callback(notif_id('radio_reset'), self.bsp_radio.cmd_reset)
        mote.set_callback(notif_id('radio_setFrequency'), self.bsp_radio.cmd_set_frequency)
        mote.set_callback(notif_id('radio_rfOn'), self.bsp_radio.cmd_rf_on)
        mote.set_callback(notif_id('radio_rfOff'), self.bsp_radio.cmd_rf_off)
        mote.set_callback(notif_id('radio_loadPacket'), self.bsp_radio.cmd_load_packet)
        mote.set_callback(notif_id('radio_txEnable'), self.bsp_radio.cmd_tx_enable)
        mote.set_callback(notif_id('radio_txNow'), self.bsp_radio.cmd_tx_now)
        mote.set_callback(notif_id('radio_rxEnable'), self.bsp_radio.cmd_rx_enable)
        mote.set_callback(notif_id('radio_rxNow'), self.bsp_radio.cmd_rx_now)
        mote.set_callback(notif_id('radio_getReceivedFrame'), self.bsp_radio.cmd_get_received_frame)
        # sctimer
        mote.set_callback(notif_id('sctimer_init'), self.bsp_sctimer.cmd_init)
        mote.set_callback(notif_id('sctimer_setCompare'), self.bsp_sctimer.cmd_set_compare)
        mote.set_callback(notif_id('sctimer_readCounter'), self.bsp_sctimer.cmd_read_counter)
        mote.set_callback(notif_id('sctimer_enable'), self.bsp_sctimer.cmd_enable)
        mote.set_callback(notif_id('sctimer_disable'), self.bsp_sctimer.cmd_disable)
        # uart
        mote.set_callback(notif_id('uart_init'), self.bsp_uart.cmd_init)
        mote.set_callback(notif_id('uart_enableInterrupts'), self.bsp_uart.cmd_enable_interrupts)
        mote.set_callback(notif_id('uart_disableInterrupts'), self.bsp_uart.cmd_disable_interrupts)
        mote.set_callback(notif_id('uart_clearRxInterrupts'), self.bsp_uart.cmd_clear_rx_interrupts)
        mote.set_callback(notif_id('uart_clearTxInterrupts'), self.bsp_uart.cmd_clear_tx_interrupts)
        mote.set_callback(notif_id('uart_writeByte'), self.bsp_uart.cmd_write_byte)
        mote.set_callback(notif_id('uart_writeCircularBuffer_FASTSIM'), self.bsp_uart.cmd_write_circular_buffer_fastsim)
        mote.set_callback(notif_id('uart_writeBufferByLen_FASTSIM'), self.bsp_uart.uart_write_buffer_by_len_fastsim)
        mote.set_callback(notif_id('uart_readByte'), self.bsp_uart.cmd_read_byte)
        mote.set_callback(notif_id('uart_setCTS'), self.bsp_uart.cmd_set_cts)

        # logging this module
        self.log = logging.getLogger('MoteHandler_' + str(self.id))
        self.log.setLevel(logging.INFO)
        self.log.addHandler(logging.NullHandler())

        # logging this mote's modules
        for logger_name in [
            'MoteHandler_' + str(self.id),
            # hw
            'HwSupply_' + str(self.id),
            'HwCrystal_' + str(self.id),
            # bsp
            'BspBoard_' + str(self.id),
            'BspDebugpins_' + str(self.id),
            'BspEui64_' + str(self.id),
            'BspLeds_' + str(self.id),
            'BspSctimer_' + str(self.id),
            'BspRadio_' + str(self.id),
            'BspUart_' + str(self.id),
        ]:
            temp = logging.getLogger(logger_name)
            temp.setLevel(logging.INFO)
            temp.addHandler(self.loghandler)

        # initialize parent class
        super(MoteHandler, self).__init__()

        # give this thread a name
        self.setName('MoteHandler_' + str(self.id))

        # thread daemon mode
        self.setDaemon(True)

        # log
        self.log.info('thread initialized')

    def run(self):

        # log
        self.log.info('thread starting')

        # switch on the mote
        self.hw_supply.switch_on()

        assert 0

    # ======================== public ==========================================

    def get_id(self):
        return self.id

    def get_location(self):
        return self.location

    def set_location(self, lat, lon):
        self.location = (lat, lon)

    def handle_event(self, function_to_call):

        if not self.booted:

            assert function_to_call == self.hw_supply.switch_on

            # I'm not booted
            self.booted = True

            # start the thread's execution
            self.start()

            # wait for CPU to be done
            self.cpu_done.acquire()

        else:
            # call the funcion (mote runs in ISR)
            kick_scheduler = function_to_call()

            assert kick_scheduler in [True, False]

            if kick_scheduler:
                # release the mote's CPU (mote runs in task mode)
                self.cpu_running.release()

                # wait for CPU to be done
                self.cpu_done.acquire()

    # ======================== private =========================================
