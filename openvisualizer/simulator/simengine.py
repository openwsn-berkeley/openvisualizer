import logging
import time
from multiprocessing import Process, Barrier, Event
from multiprocessing.process import current_process
from threading import Thread

from openvisualizer.simulator.emulatedmote import create_mote
from openvisualizer.simulator.moteprocess import MoteProcessInterface
from openvisualizer.simulator.propagation import Propagation


class SimEngine(Thread):
    """ Discrete event simulator. Spawns a process for each emulated mote. """

    KEEP_RUNNING: bool = True
    ADDRESS = ("localhost", 6000)

    def __init__(self, num_of_motes: int):
        # time line thread
        super(SimEngine, self).__init__()

        self.name = "SimEngine"

        # unpause the simulator
        self._pause_event = Event()
        self._pause_event.set()

        self._start_time = time.time()

        self.num_of_motes = num_of_motes

        # internal objects to synchronize the individual mote processes.
        self._slot_barrier = Barrier(num_of_motes)
        self._msg_barrier = Barrier(num_of_motes)
        self._ack_barrier = Barrier(num_of_motes)

        # create the mote interfaces
        self.mote_interfaces = [
            MoteProcessInterface(
                i,  # mote id
                self._slot_barrier,  # barrier for ASN synchronization
                self._msg_barrier,  # barrier for message synchronization
                self._ack_barrier,  # barrier for acknowledgment synchronization
                self._pause_event)  # pause event
            for i in range(1, self.num_of_motes + 1)]

        self.propagation_t = Propagation(self.mote_interfaces)

        self.mote_processes = [Process(target=create_mote, args=(m_if,)) for m_if in self.mote_interfaces]
        self.mote_cmd_ifs = {m_if.mote_id: m_if.cmd_if for m_if in self.mote_interfaces}

        self.mote_ids = [m_if.mote_id for m_if in self.mote_interfaces]

        # set up logger
        handler = logging.StreamHandler()
        ft = logging.Formatter(fmt='%(asctime)s [%(name)s:%(levelname)s] %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(ft)
        handler.setLevel(logging.DEBUG)

        self.logger = logging.getLogger("SimEngine")
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    def pause(self):
        """ Un/Pause the simulation engine. """
        if self._pause_event.is_set():
            self._pause_event.clear()
            return True
        else:
            self._pause_event.set()
            return False

    def run(self) -> None:
        self.logger.info(f'Starting engine (PID = {current_process().pid})')

        self.propagation_t.start()

        for mote in self.mote_processes:
            time.sleep(0.2)
            mote.start()

        while self.KEEP_RUNNING:
            time.sleep(0.1)

        self.propagation_t.stop()
        self.propagation_t.join()

        # terminate mote processes
        self.logger.info("Terminating and joining mote processes {}".format([p.pid for p in self.mote_processes]))

        time.sleep(1)
        for mote in self.mote_processes:
            if mote.is_alive():
                mote.terminate()
            mote.join()

        self.logger.info("Leaving SimEngine loop")

    def shutdown(self):
        self.KEEP_RUNNING = False

    @property
    def runtime(self):
        now = time.time()
        return now - self._start_time
