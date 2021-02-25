import logging
import random
import time
from multiprocessing import Process, Barrier, Event
from multiprocessing.process import current_process
from threading import Thread

from openvisualizer.simulator.emulatedmote import create_mote
from openvisualizer.simulator.moteprocess import MoteProcessInterface
from openvisualizer.simulator.topology import Topology


class SimEngine(Thread):
    """ Discrete event simulator. Spawns a process for each emulated mote. """

    KEEP_RUNNING: bool = True
    ADDRESS = ("localhost", 6000)

    def __init__(self, num_of_motes: int, topology: str = 'fully-meshed'):
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

        self.topology_t = Topology(self.mote_interfaces, topology)

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

        self.topology_t.start()

        for mote in self.mote_processes:
            time.sleep(0.2)
            mote.start()

        while self.KEEP_RUNNING:
            time.sleep(0.1)

        self.topology_t.stop()
        self.topology_t.join()

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

    def connections_getter(self):
        retrieved_connections = []
        return_val = []

        for from_mote in self.mote_ids:
            for to_mote in self.mote_ids:
                if (to_mote, from_mote) not in retrieved_connections and to_mote != from_mote and \
                        self.topology_t.connection_matrix[from_mote - 1][to_mote - 1] is not None:
                    return_val += [
                        {
                            'fromMote': from_mote,
                            'toMote': to_mote,
                            'pdr': self.topology_t.connection_matrix[from_mote - 1][to_mote - 1].pdr,
                        },
                    ]
                    retrieved_connections += [(from_mote, to_mote)]

        return return_val

    def connections_setter(self, from_mote: int, to_mote: int, pdr: int):

        if pdr > 0:
            if self.topology_t.connection_matrix[int(from_mote) - 1][int(to_mote) - 1]:
                self.topology_t.connection_matrix[int(from_mote) - 1][int(to_mote) - 1].pdr = int(pdr)
            else:
                self.topology_t.connection_matrix[int(from_mote) - 1][int(to_mote) - 1] = \
                    self.topology_t.create_link(pdr, int(to_mote))
        else:
            self.topology_t.delete_link(from_mote, to_mote)

    def positions_getter(self):
        mote_positions = []
        for m in self.mote_ids:
            mote_positions += \
                [
                    {
                        'id': m,
                        'lat': self.topology_t.position_list[m - 1].lat,
                        'lon': self.topology_t.position_list[m - 1].lon
                    }
                ]

        return mote_positions

    def positions_setter(self, new_positions):
        for m in new_positions:
            self.topology_t.position_list[int(m)].lat = new_positions[m]['lat']
            self.topology_t.position_list[int(m)].lon = new_positions[m]['lon']

    def runtime_getter(self):
        # choose a random mote
        address = random.randint(1, len(self.mote_ids))

        while not self.mote_cmd_ifs[address].empty():
            time.sleep(0.01)

        self.mote_cmd_ifs[address].put('get_runtime')
        self.mote_cmd_ifs[address].join()

        rcv = self.mote_cmd_ifs[address].get()
        self.mote_cmd_ifs[address].task_done()

        return eval(rcv)
