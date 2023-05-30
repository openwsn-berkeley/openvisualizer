# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import time
from multiprocessing import get_logger
from threading import Lock, BrokenBarrierError
from typing import Callable

from openvisualizer.simulator.bspemulator.bspmodule import BspModule


class Interrupt:
    __slots__ = ('mote_id', 'at_time', 'cb', 'desc')

    def __init__(self, mote_id, at_time, cb, desc):
        self.at_time: int = at_time
        self.mote_id: int = mote_id
        self.cb: Callable = cb
        self.desc: str = desc

    def __repr__(self):
        return f"<Interrupt: mote={self.mote_id} time={self.at_time} desc={self.desc}>"


class BspBoard(BspModule):
    """ Emulates the 'board' BSP module """

    def __init__(self, mote):
        # initialize the parent
        super(BspBoard, self).__init__(mote)

        self.current_time = 0

        self.intr_lock = Lock()
        self.pending_intr = []

        # logging
        self.logger = get_logger()
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

    # ======================== public ==========================================

    # === commands

    def cmd_init(self):
        """ Emulates: void board_init() """

        # log the activity
        self.logger.debug('cmd_init')

        # remember that module has been initialized
        self.is_initialized = True

    def cmd_sleep(self):
        """ Emulates: void board_sleep() """

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("cmd_sleep")

        self._handle_intr()

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.info("cmd_wakeup")

    def cmd_barrier_slot_sync(self):

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("cmd_slot_sync")

        # check if paused
        self.mote.pause_event.wait()

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.info(f'[{self.mote.mote_id}] Waiting at slot_barrier')
        try:
            self.mote.slot_barrier.wait()
        except BrokenBarrierError:
            self.logger.info("Exiting at slot_barrier ...")
            time.sleep(100)

    def cmd_barrier_msg_sync(self):

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("cmd_msg_sync")

        # check if paused
        self.mote.pause_event.wait()

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f'[{self.mote.mote_id}] Waiting at msg_barrier')
        try:
            self.mote.msg_barrier.wait()
        except BrokenBarrierError:
            self.logger.info("Exiting at msg_barrier ...")
            time.sleep(100)

    def cmd_barrier_ack_sync(self):

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("cmd_ack_sync")

        # check if paused
        self.mote.pause_event.wait()

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f'[{self.mote.mote_id}] Waiting at ack_barrier')
        try:
            self.mote.ack_barrier.wait()
        except BrokenBarrierError:
            self.logger.info("Exiting at ack_barrier ...")
            time.sleep(100)

    def schedule_intr(self, at_time, mote_id, cb, desc):

        interrupt = Interrupt(at_time=at_time, mote_id=mote_id, cb=cb, desc=desc)

        with self.intr_lock:
            try:
                assert self.current_time <= interrupt.at_time
            except AssertionError:
                output = ["\nCannot schedule an event in the past ..."]
                output += [f"\t - Current time: {self.current_time}"]
                output += [f"\t - Event time:   {interrupt.at_time}"]
                self.logger.critical("\n".join(output))

            # if this event already exists, remove the old one and add the new one
            for i in range(len(self.pending_intr)):
                if self.pending_intr[i].mote_id == mote_id and self.pending_intr[i].desc == desc:
                    self.pending_intr.pop(i)
                    break

            i = 0
            while i < len(self.pending_intr):
                if interrupt.at_time > self.pending_intr[i].at_time:
                    i += 1
                else:
                    break

            self.pending_intr.insert(i, interrupt)

    def get_current_time(self):
        with self.intr_lock:
            ct = self.current_time

        return ct

    # ======================== private =========================================

    def _handle_intr(self):

        self.intr_lock.acquire()
        try:
            interrupt: Interrupt = self.pending_intr.pop(0)
        except IndexError:
            self.intr_lock.release()
            return

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("cmd_isr_start")

        assert interrupt.at_time >= self.current_time
        self.current_time = interrupt.at_time
        self.intr_lock.release()

        interrupt.cb()

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("cmd_isr_done")
