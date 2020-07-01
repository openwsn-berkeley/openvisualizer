# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
import logging
from abc import ABCMeta

from openvisualizer.simengine import simengine


class HwModule(object):
    """ Parent class for all hardware modules. """
    __metaclass__ = ABCMeta

    @property
    def _name(self):
        raise NotImplementedError

    def __init__(self, motehandler):
        # store variables
        self.motehandler = motehandler

        # local variables
        self.engine = simengine.SimEngine()

        # logging
        self.log = logging.getLogger(self._name + '_' + str(self.motehandler.get_id()))
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(logging.NullHandler())
