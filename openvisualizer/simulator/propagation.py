import logging
import queue
import random
from collections import namedtuple
from threading import Thread
from typing import List, Dict, Optional

from openvisualizer.simulator.moteprocess import Radio

Link = namedtuple('Link', ['pdr', 'rx'])


class Propagation(Thread):
    def __init__(self, mote_ifs, topology="fully-meshed"):
        super().__init__()

        self.radio_qs: Dict[int, Radio] = {m_if.mote_id: m_if.radio for m_if in mote_ifs}
        self.mote_ids = [m.mote_id for m in mote_ifs]

        self.go_on = True
        self.topology = topology

        self._connection_matrix: List[List[Optional[Link]]] = [[None for m in self.mote_ids] for n in self.mote_ids]

        self.create_topology()

        handler = logging.StreamHandler()
        ft = logging.Formatter(fmt='%(asctime)s [%(name)s:%(levelname)s] %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(ft)
        handler.setLevel(logging.DEBUG)

        self.logger = logging.getLogger("Propagation")
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    def run(self) -> None:
        while self.go_on:
            for mote in self.radio_qs.keys():
                try:
                    origin, packet, freq = self.radio_qs[mote].tx.get_nowait()

                    links: List[Link] = self.connection_matrix[origin - 1]

                    for link in links:
                        if link is not None:
                            if random.randint(1, 100) <= link.pdr:
                                link.rx.put([origin, packet, freq])
                                link.rx.join()
                            else:
                                pass

                    # notify sender that message was successfully passed along
                    self.radio_qs[mote].tx.task_done()

                except queue.Empty:
                    continue
        self.logger.info("Exiting propagation loop")

    def create_topology(self):
        if self.topology == "fully-meshed":
            for from_mote in self.mote_ids:
                for to_mote in self.mote_ids:
                    if from_mote == to_mote:
                        continue

                    self._connection_matrix[from_mote - 1][to_mote - 1] = Link(pdr=100, rx=self.radio_qs[to_mote].rx)
        elif self.topology == "linear":
            for m in range(len(self.mote_ids) - 1):
                self._connection_matrix[m][m + 1] = Link(pdr=100, rx=self.radio_qs[m + 1].rx)
        else:
            self.logger.error('Unknown topology')

    @property
    def connection_matrix(self):
        return self._connection_matrix

    @connection_matrix.setter
    def connection_matrix(self, new_matrix: List[List[Optional[Link]]]):
        self._connection_matrix = new_matrix

    def stop(self) -> None:
        self.go_on = False
