from collections import namedtuple
from typing import TYPE_CHECKING
from multiprocessing import Manager

if TYPE_CHECKING:
    from multiprocessing import Barrier, Event

Radio = namedtuple('Radio', ['tx', 'rx'])
Uart = namedtuple('Uart', ['tx', 'rx'])


class MoteProcessInterface:
    def __init__(self, mote_id: int,
                 slot_barrier: 'Barrier',
                 msg_barrier: 'Barrier',
                 ack_barrier: 'Barrier',
                 pause_event: 'Event'):
        self.mote_id = mote_id
        self.slot_barrier = slot_barrier
        self.msg_barrier = msg_barrier
        self.ack_barrier = ack_barrier
        self.pause_event = pause_event

        # communication channels
        manager = Manager()
        self.uart = Uart(manager.Queue(), manager.Queue())
        self.radio = Radio(manager.Queue(), manager.Queue())
        self.cmd_if = manager.Queue()
