#!/usr/bin/python
# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging

import simengine


class IdManager(object):
    """ The module which assigns ID to the motes. """

    def __init__(self):
        # store params
        self.engine = simengine.SimEngine()

        # local variables
        self.current_id = 0

        # logging
        self.log = logging.getLogger('IdManager')
        self.log.setLevel(logging.INFO)
        self.log.addHandler(logging.NullHandler())

    # ======================== public ==========================================

    def get_id(self):
        # increment the running ID
        self.current_id += 1

        # debug
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('assigning ID=' + str(self.current_id))

        return self.current_id

    # ======================== private =========================================

    # ======================== helpers =========================================
