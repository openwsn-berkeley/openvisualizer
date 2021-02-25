from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from multiprocessing.queues import Queue


class Link:
    """ Module that describes the link quality between two motes"""

    def __init__(self, pdr: int, rx: 'Queue'):
        self.pdr = pdr
        self.rx = rx
