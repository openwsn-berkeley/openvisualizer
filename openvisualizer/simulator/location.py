#!/usr/bin/python
# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import random
from typing import Tuple


class LocationManager:
    """ The module which assigns locations to the motes. """

    def __init__(self):
        # get random location around Cory Hall, UC Berkeley
        self.lat = 37.875095 - 0.0005 + random.random() * 0.0010
        self.lon = -122.257473 - 0.0005 + random.random() * 0.0010

    # ======================== public ==========================================

    @property
    def location(self) -> Tuple[float, float]:
        # debug
        return self.lat, self.lon

    @location.setter
    def location(self, new_location: Tuple[float, float]):
        self.lat = new_location[0]
        self.lon = new_location[1]

    # ======================== private =========================================
