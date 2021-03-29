import logging
import queue
from random import randint
from threading import Thread
from typing import List, Dict, Optional

from openvisualizer.simulator.link import Link
from openvisualizer.simulator.location import LocationManager
from openvisualizer.simulator.moteprocess import Radio


class Topology(Thread):
    def __init__(self, mote_ifs, topology_name="fully-meshed"):
        super().__init__()

        # Dict [mote-id : radio{tx,rx}]
        self.radio_qs: Dict[int, Radio] = {m_if.mote_id: m_if.radio for m_if in mote_ifs}
        self.mote_ids = self.radio_qs.keys()

        self.go_on = True

        if topology_name in {'fully-meshed', 'linear', 'random'}:
            self.topology_name = topology_name
        else:
            self.topology_name = 'fully-meshed'

        self._connection_matrix: List[List[Optional[Link]]] = [[None for m in self.mote_ids] for n in self.mote_ids]
        self._position_list: List[LocationManager] = [LocationManager() for m in self.mote_ids]

        self.create_topology()

        handler = logging.StreamHandler()
        ft = logging.Formatter(fmt='%(asctime)s [%(name)s:%(levelname)s] %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(ft)
        handler.setLevel(logging.DEBUG)

        self.logger = logging.getLogger("Topology")
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
                            if randint(1, 100) <= link.pdr:
                                link.rx.put([origin, packet, freq])
                                link.rx.join()
                            else:
                                pass

                    # notify sender that message was successfully passed along
                    self.radio_qs[mote].tx.task_done()

                except queue.Empty:
                    continue
                except (EOFError, BrokenPipeError):
                    self.logger.error('Queue closed')
                    self.go_on = False
                    break

        self.logger.info("Exiting propagation loop")

    def create_topology(self):
        if self.topology_name == "fully-meshed":
            for from_mote in self.mote_ids:
                for to_mote in self.mote_ids:
                    if from_mote == to_mote:
                        continue

                    self._connection_matrix[from_mote - 1][to_mote - 1] = self.create_link(100, to_mote)

        elif self.topology_name == "linear":
            for from_mote in self.mote_ids:
                for to_mote in self.mote_ids:
                    if from_mote == to_mote:
                        continue

                    if from_mote + 1 == to_mote or from_mote == to_mote + 1:
                        self._connection_matrix[from_mote - 1][to_mote - 1] = self.create_link(100, to_mote)

        elif self.topology_name == "random":
            for from_mote in self.mote_ids:
                for to_mote in self.mote_ids:
                    if from_mote == to_mote:
                        continue

                    self._connection_matrix[from_mote - 1][to_mote - 1] = self.create_link(randint(0, 100), to_mote)
        else:
            self.logger.error('Unknown topology')

    def create_link(self, pdr: int, to_mote: int) -> 'Link':
        return Link(pdr=pdr, rx=self.radio_qs[to_mote].rx)

    def delete_link(self, from_mote, to_mote) -> None:
        self._connection_matrix[from_mote - 1][to_mote - 1] = None
        self._connection_matrix[to_mote - 1][from_mote - 1] = None

    @property
    def connection_matrix(self):
        return self._connection_matrix

    @property
    def position_list(self):
        return self._position_list

    def stop(self) -> None:
        self.go_on = False
