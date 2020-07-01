# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
import logging
import threading

import yappi

log = logging.getLogger('OVtracer')
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class OVtracer(object):
    TRACING_INTERVAL = 30

    def __init__(self):
        yappi.start()
        self.timer = threading.Timer(self.TRACING_INTERVAL, self._log_tracing_stats)
        self.timer.start()

    def _log_tracing_stats(self):
        threads = yappi.get_thread_stats()
        for t in threads:
            self._log_thread_stat(t)
        self.timer = threading.Timer(self.TRACING_INTERVAL, self._log_tracing_stats)
        self.timer.start()

    @staticmethod
    def _log_thread_stat(stat_entry):
        log.info("Thread Trace: {0}".format(stat_entry))

    @staticmethod
    def _log_function_stat(stat_entry):
        log.info("Function Trace: {0}".format(stat_entry))
