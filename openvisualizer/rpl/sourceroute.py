# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

"""
Module which receives DAO messages and calculates source routes.

.. moduleauthor:: Xavi Vilajosana <xvilajosana@eecs.berkeley.edu>
                  January 2013
.. moduleauthor:: Thomas Watteyne <watteyne@eecs.berkeley.edu>
                  April 2013
"""

import logging
import threading

from openvisualizer.eventbus.eventbusclient import EventBusClient

log = logging.getLogger('SourceRoute')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


class SourceRoute(EventBusClient):

    def __init__(self):

        # local variables
        self.dataLock = threading.Lock()
        self.parents = {}

        # initialize parent class
        super(SourceRoute, self).__init__(name='SourceRoute', registrations=[])

    # ======================== public ==========================================

    def get_source_route(self, dest_addr):
        """
        Retrieve the source route to a given mote.

        :param dest_addr: [in] The EUI64 address of the final destination.

        :returns: The source route, a list of EUI64 address, ordered from destination to source.
        """

        source_route = []
        with self.dataLock:
            try:
                parents = self._dispatch_and_get_result(signal='getParents', data=None)
                self._get_source_route_internal(dest_addr, source_route, parents)
            except Exception as err:
                log.error(err)
                raise

        return source_route

    # ======================== private =========================================

    def _get_source_route_internal(self, dest_addr, source_route, parents):

        if not dest_addr:
            # no more parents
            return

        if not parents.get(tuple(dest_addr)):
            # this node does not have a list of parents
            return

        # first time add destination address
        if dest_addr not in source_route:
            source_route += [dest_addr]

        # pick a parent
        parent = parents.get(tuple(dest_addr))[0]

        # avoid loops
        if parent not in source_route:
            source_route += [parent]

            # add non empty parents recursively
            nextparent = self._get_source_route_internal(parent, source_route, parents)

            if nextparent:
                source_route += [nextparent]

    # ======================== helpers =========================================
