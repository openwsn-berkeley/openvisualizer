import logging
import time
from multiprocessing import get_logger
from multiprocessing.process import current_process
from threading import Thread
from typing import TYPE_CHECKING, Tuple

from openvisualizer.simulator.bspemulator.bspboard import BspBoard
from openvisualizer.simulator.bspemulator.bspdebugpins import BspDebugPins
from openvisualizer.simulator.bspemulator.bspeui64 import BspEui64
from openvisualizer.simulator.bspemulator.bspleds import BspLeds
from openvisualizer.simulator.bspemulator.bspradio import BspRadio
from openvisualizer.simulator.bspemulator.bspsctimer import BspSctimer
from openvisualizer.simulator.bspemulator.bspuart import BspUart
from openvisualizer.simulator.bspemulator.hwcrystal import HwCrystal
from openvisualizer.simulator.bspemulator.hwsupply import HwSupply

if TYPE_CHECKING:
    from openvisualizer.simulator.moteprocess import Uart, Radio
    from openvisualizer.simulator.simengine import MoteProcessInterface
    from multiprocessing import Barrier, Event

try:
    import colorama as c

    color = True
    c.init()
except ImportError:
    color = False


class EmulatedMote:

    def __init__(self, mote, mote_interface: 'MoteProcessInterface'):
        super(EmulatedMote, self).__init__()

        # Emulated mote process ID
        self.mote_id = mote_interface.mote_id

        self.mote = mote

        self.uart: 'Uart' = mote_interface.uart
        self.radio: 'Radio' = mote_interface.radio
        self.cmd_if = mote_interface.cmd_if

        self.slot_barrier: 'Barrier' = mote_interface.slot_barrier
        self.msg_barrier: 'Barrier' = mote_interface.msg_barrier
        self.ack_barrier: 'Barrier' = mote_interface.ack_barrier
        self.pause_event: 'Event' = mote_interface.pause_event

        self.cmd_listener_t = Thread(target=self.listener, args=())
        self.cmd_listener_t.setDaemon(True)
        self.cmd_listener_t.start()

        self.start_time = time.time()

        # logging functions
        self.handler = logging.StreamHandler()
        ft = logging.Formatter(fmt='%(asctime)s [%(name)s:%(levelname)s] %(message)s', datefmt='%H:%M:%S')
        self.handler.setFormatter(ft)
        self.handler.setLevel(logging.DEBUG)

        self.logger = get_logger()
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

        # initialize Python BSP backend
        self.hw_supply = HwSupply(self)
        self.hw_crystal = HwCrystal(self)
        self.bsp_board = BspBoard(self)
        self.bsp_debugpins = BspDebugPins(self)
        self.bsp_eui64 = BspEui64(self)
        self.bsp_leds = BspLeds(self)
        self.bsp_sctimer = BspSctimer(self)
        self.bsp_radio = BspRadio(self)
        self.bsp_uart = BspUart(self)

        # install BSP callback functions
        self.mote.set_callback(self.mote.MOTE_NOTIF_board_init, self.bsp_board.cmd_init)
        self.mote.set_callback(self.mote.MOTE_NOTIF_board_sleep, self.bsp_board.cmd_sleep)
        self.mote.set_callback(self.mote.MOTE_NOTIF_board_slot_sync, self.bsp_board.cmd_barrier_slot_sync)
        self.mote.set_callback(self.mote.MOTE_NOTIF_board_msg_sync, self.bsp_board.cmd_barrier_msg_sync)
        self.mote.set_callback(self.mote.MOTE_NOTIF_board_ack_sync, self.bsp_board.cmd_barrier_ack_sync)
        # debugpins
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_init, self.bsp_debugpins.cmd_init)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_frame_toggle, self.bsp_debugpins.cmd_frame_toggle)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_frame_clr, self.bsp_debugpins.cmd_frame_clr)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_frame_set, self.bsp_debugpins.cmd_frame_set)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_slot_toggle, self.bsp_debugpins.cmd_slot_toggle)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_slot_clr, self.bsp_debugpins.cmd_slot_clr)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_slot_set, self.bsp_debugpins.cmd_slot_set)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_fsm_toggle, self.bsp_debugpins.cmd_fsm_toggle)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_fsm_clr, self.bsp_debugpins.cmd_fsm_clr)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_fsm_set, self.bsp_debugpins.cmd_fsm_set)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_task_toggle, self.bsp_debugpins.cmd_task_toggle)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_task_clr, self.bsp_debugpins.cmd_task_clr)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_task_set, self.bsp_debugpins.cmd_task_set)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_isr_toggle, self.bsp_debugpins.cmd_isr_toggle)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_isr_clr, self.bsp_debugpins.cmd_isr_clr)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_isr_set, self.bsp_debugpins.cmd_isr_set)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_radio_toggle, self.bsp_debugpins.cmd_radio_toggle)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_radio_clr, self.bsp_debugpins.cmd_radio_clr)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_radio_set, self.bsp_debugpins.cmd_radio_set)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_ka_clr, self.bsp_debugpins.cmd_ka_clr)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_ka_set, self.bsp_debugpins.cmd_ka_set)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_syncPacket_clr, self.bsp_debugpins.cmd_sync_packet_clr)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_syncPacket_set, self.bsp_debugpins.cmd_sync_packet_set)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_syncAck_clr, self.bsp_debugpins.cmd_sync_ack_clr)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_syncAck_set, self.bsp_debugpins.cmd_sync_ack_set)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_debug_clr, self.bsp_debugpins.cmd_debug_clr)
        self.mote.set_callback(self.mote.MOTE_NOTIF_debugpins_debug_set, self.bsp_debugpins.cmd_debug_set)
        # eui64
        self.mote.set_callback(self.mote.MOTE_NOTIF_eui64_get, self.bsp_eui64.cmd_get)
        # leds
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_init, self.bsp_leds.cmd_init)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_error_on, self.bsp_leds.cmd_error_on)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_error_off, self.bsp_leds.cmd_error_off)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_error_toggle, self.bsp_leds.cmd_error_toggle)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_error_isOn, self.bsp_leds.cmd_error_is_on)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_radio_on, self.bsp_leds.cmd_radio_on)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_radio_off, self.bsp_leds.cmd_radio_off)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_radio_toggle, self.bsp_leds.cmd_radio_toggle)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_radio_isOn, self.bsp_leds.cmd_radio_is_on)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_sync_on, self.bsp_leds.cmd_sync_on)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_sync_off, self.bsp_leds.cmd_sync_off)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_sync_toggle, self.bsp_leds.cmd_sync_toggle)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_sync_isOn, self.bsp_leds.cmd_sync_is_on)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_debug_on, self.bsp_leds.cmd_debug_on)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_debug_off, self.bsp_leds.cmd_debug_off)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_debug_toggle, self.bsp_leds.cmd_debug_toggle)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_debug_isOn, self.bsp_leds.cmd_debug_is_on)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_all_on, self.bsp_leds.cmd_all_on)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_all_off, self.bsp_leds.cmd_all_off)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_all_toggle, self.bsp_leds.cmd_all_toggle)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_circular_shift, self.bsp_leds.cmd_circular_shift)
        self.mote.set_callback(self.mote.MOTE_NOTIF_leds_increment, self.bsp_leds.cmd_increment)
        # radio
        self.mote.set_callback(self.mote.MOTE_NOTIF_radio_init, self.bsp_radio.cmd_init)
        self.mote.set_callback(self.mote.MOTE_NOTIF_radio_reset, self.bsp_radio.cmd_reset)
        self.mote.set_callback(self.mote.MOTE_NOTIF_radio_setFrequency, self.bsp_radio.cmd_set_frequency)
        self.mote.set_callback(self.mote.MOTE_NOTIF_radio_rfOn, self.bsp_radio.cmd_rf_on)
        self.mote.set_callback(self.mote.MOTE_NOTIF_radio_rfOff, self.bsp_radio.cmd_rf_off)
        self.mote.set_callback(self.mote.MOTE_NOTIF_radio_loadPacket, self.bsp_radio.cmd_load_packet)
        self.mote.set_callback(self.mote.MOTE_NOTIF_radio_txEnable, self.bsp_radio.cmd_tx_enable)
        self.mote.set_callback(self.mote.MOTE_NOTIF_radio_txNow, self.bsp_radio.cmd_tx_now)
        self.mote.set_callback(self.mote.MOTE_NOTIF_radio_rxEnable, self.bsp_radio.cmd_rx_enable)
        self.mote.set_callback(self.mote.MOTE_NOTIF_radio_rxNow, self.bsp_radio.cmd_rx_now)
        self.mote.set_callback(self.mote.MOTE_NOTIF_radio_getReceivedFrame, self.bsp_radio.cmd_get_received_frame)
        # sctimer
        self.mote.set_callback(self.mote.MOTE_NOTIF_sctimer_init, self.bsp_sctimer.cmd_init)
        self.mote.set_callback(self.mote.MOTE_NOTIF_sctimer_setCompare, self.bsp_sctimer.cmd_set_compare)
        self.mote.set_callback(self.mote.MOTE_NOTIF_sctimer_readCounter, self.bsp_sctimer.cmd_read_counter)
        self.mote.set_callback(self.mote.MOTE_NOTIF_sctimer_enable, self.bsp_sctimer.cmd_enable)
        self.mote.set_callback(self.mote.MOTE_NOTIF_sctimer_disable, self.bsp_sctimer.cmd_disable)
        # uart
        self.mote.set_callback(self.mote.MOTE_NOTIF_uart_init, self.bsp_uart.cmd_init)
        self.mote.set_callback(self.mote.MOTE_NOTIF_uart_enableInterrupts, self.bsp_uart.cmd_enable_interrupts)
        self.mote.set_callback(self.mote.MOTE_NOTIF_uart_disableInterrupts, self.bsp_uart.cmd_disable_interrupts)
        self.mote.set_callback(self.mote.MOTE_NOTIF_uart_clearRxInterrupts, self.bsp_uart.cmd_clear_rx_interrupts)
        self.mote.set_callback(self.mote.MOTE_NOTIF_uart_clearTxInterrupts, self.bsp_uart.cmd_clear_tx_interrupts)
        self.mote.set_callback(self.mote.MOTE_NOTIF_uart_writeByte, self.bsp_uart.cmd_write_byte)
        self.mote.set_callback(self.mote.MOTE_NOTIF_uart_writeCircularBuffer_FASTSIM,
                               self.bsp_uart.cmd_write_circular_buffer_fastsim)
        self.mote.set_callback(self.mote.MOTE_NOTIF_uart_writeBufferByLen_FASTSIM,
                               self.bsp_uart.uart_write_buffer_by_len_fastsim)
        self.mote.set_callback(self.mote.MOTE_NOTIF_uart_readByte, self.bsp_uart.cmd_read_byte)
        self.mote.set_callback(self.mote.MOTE_NOTIF_uart_setCTS, self.bsp_uart.cmd_set_cts)

    def start(self) -> None:
        self.logger.info(f"Booting mote_{self.mote_id} (PID = {current_process().pid}) ...")

        self.hw_supply.switch_on()

        now = time.time()
        self.logger.info(f"Elapsed time: {now - self.start_time}")
        self.logger.info(f"Simulation time: {self.bsp_board.get_current_time()}")

    def listener(self):
        while True:
            try:
                rcv = self.cmd_if.get()
                self.cmd_if.task_done()

                res = eval('self.' + rcv + '_cmd')()
                self.cmd_if.put(str(res))
                self.cmd_if.join()
            except (EOFError, BrokenPipeError):
                self.logger.error('Queue closed')
                break

    # commands to interact with emulated motes

    def get_runtime_cmd(self) -> Tuple[float, float]:
        now = time.time()
        real = now - self.start_time
        bsp_time = self.bsp_board.get_current_time()
        return real, bsp_time


def create_mote(mote_interface: 'MoteProcessInterface'):
    try:
        import openmote as mote
        EmulatedMote(mote, mote_interface).start()
    except ImportError:
        if color:
            print(c.Back.RED + c.Fore.WHITE + "Could not import python module 'openwsn'" + c.Style.RESET_ALL)
            print(c.Back.RED + c.Fore.WHITE + "Failed to instantiate emulated mote" + c.Style.RESET_ALL)
            print(c.Back.RED + c.Fore.WHITE + "Kill simulation with CTRL-C" + c.Style.RESET_ALL + "\n")
        else:
            print("Could not import python module 'openwsn'")
            print("Failed to instantiate emulated mote")
            print("Kill simulation with CTRL-C\n")
