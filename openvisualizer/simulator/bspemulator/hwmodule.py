# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

from abc import ABCMeta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openvisualizer.simulator.emulatedmote import EmulatedMote


class HwModule(metaclass=ABCMeta):
    """ Parent class for all hardware modules. """

    def __init__(self, mote: 'EmulatedMote'):
        # store variables
        self.mote = mote
        self.handler = mote.handler
