#!/usr/bin/python
# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import random
from multiprocessing import get_logger
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from openvisualizer.simulator.emulatedmote import EmulatedMote


class LocationManager:
    """ The module which assigns locations to the motes. """

    def __init__(self, mote: 'EmulatedMote'):
        # local variables

        # logging
        self.logger = get_logger()
        self.logger.addHandler(mote.handler)
        self.logger.setLevel(logging.INFO)

        # get random location around Cory Hall, UC Berkeley
        self.lat = 37.875095 - 0.0005 + random.random() * 0.0010
        self.lon = -122.257473 - 0.0005 + random.random() * 0.0010

    # ======================== public ==========================================

    @property
    def location(self) -> Tuple[float, float]:
        # debug
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug('assigning location ({0} {1})'.format(self.lat, self.lon))

        return self.lat, self.lon

    # ======================== private =========================================
