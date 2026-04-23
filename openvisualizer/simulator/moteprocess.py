import multiprocessing
from collections import namedtuple
from typing import TYPE_CHECKING
from multiprocessing import Manager

if TYPE_CHECKING:
    from multiprocessing import Barrier, Event

Radio = namedtuple('Radio', ['tx', 'rx'])
Uart = namedtuple('Uart', ['tx', 'rx'])


class MoteProcessInterface(object):

    def __init__(self, mote_id: int, slot_b: 'Barrier', msg_b: 'Barrier', ack_b: 'Barrier', pause_event: 'Event'):
        self.mote_id = mote_id
        self.slot_barrier = slot_b
        self.msg_barrier = msg_b
        self.ack_barrier = ack_b
        self.pause_event = pause_event

        # communication channels
        manager = Manager()
        self.uart = Uart(manager.Queue(), manager.Queue())
        self.radio = Radio(manager.Queue(), manager.Queue())
        self.cmd_if = multiprocessing.JoinableQueue()
