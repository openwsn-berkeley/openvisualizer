#!/usr/bin/python
# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import random

from openvisualizer.bspemulator.hwmodule import HwModule


class HwCrystal(HwModule):
    """ Emulates the mote's crystal. """

    _name = 'HwCrystal'

    FREQUENCY = 32768
    MAXDRIFT = 0  # ppm

    def __init__(self, motehandler):
        # initialize the parent
        super(HwCrystal, self).__init__(motehandler)

        # local variables
        self.timeline = self.engine.timeline
        self.frequency = self.FREQUENCY
        self.max_drift = self.MAXDRIFT

        # local variables
        self.drift = float(random.uniform(-self.max_drift, self.max_drift))

        # the duration of one tick. Since it is constant, it is only calculated once by _getPeriod(). Therefore, do not
        # use directly, rather use property period
        self._period = None

        # ts_tick is a timestamp associated with any tick in the past. Since the period is constant, it is used to
        # ensure alignement of timestamps to an integer number of ticks.
        self.ts_tick = None

    # ======================== public ==========================================

    def start(self):
        """ Start the crystal. """

        # get the timestamp of a
        self.ts_tick = self.timeline.get_current_time()

        # log
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('crystal starts at ' + str(self.ts_tick))

    def get_time_last_tick(self):
        """
        Return the timestamp of the last tick.

        :returns: The timestamp of the last tick.
        """

        '''
        self.ts_tick                current_time
          |                          |                   period
          V                          v                <---------->
        -----------------------------------------------------------------------
          |          |   ...    |          |          |          |          |
        -----------------------------------------------------------------------
           <------------------------->
                 time_since_last
                                ^
                                |
                           time_last_tick

        '''

        # make sure crystal has been started
        assert self.ts_tick is not None

        current_time = self.timeline.get_current_time()
        time_since_last = current_time - self.ts_tick

        ticks_since_last = round(float(time_since_last) / float(self.period))
        time_last_tick = self.ts_tick + ticks_since_last * self.period

        self.ts_tick = time_last_tick

        return time_last_tick

    def get_time_in(self, num_ticks):
        """
        Return the time it will be in a given number of ticks.

        :param num_ticks: The number of ticks of interest.
        :returns: The time it will be in a given number of ticks.
        """

        '''
          called here
               |                                                    period
               V                                                 <---------->
        -----------------------------------------------------------------------
          |          |          |          |          |          |          |
        -----------------------------------------------------------------------
          ^          ^          ^          ^
          |          |          |          |
          +----------+----------+--------- +
                  num_ticks ticks
          ^                                ^
          |                                |
        time_last_tick                returned value
        '''

        # make sure crystal has been started
        assert self.ts_tick is not None
        assert num_ticks >= 0

        time_last_tick = self.get_time_last_tick()

        return time_last_tick + num_ticks * self.period

    def get_ticks_since(self, event_time):
        """
        Return the number of ticks since some timestamp.

        :param event_time: The time of the event of interest.
        :returns: The number of ticks since the time passed.
        """

        '''
           eventTime                                   current_time
               |                                           |        period
               V                                           V     <---------->
        -----------------------------------------------------------------------
          |          |          |          |          |          |          |
        -----------------------------------------------------------------------
                                                      ^
                                                      |
                                                 time_last_tick
                     ^          ^          ^          ^
                     |          |          |          |
                     +----------+----------+----------+
        '''

        # make sure crystal has been started
        assert self.ts_tick is not None

        # get the current time
        current_time = self.timeline.get_current_time()

        # make sure that event_time passed is in the past
        assert (event_time <= current_time)

        # get the time of the last tick
        time_last_tick = self.get_time_last_tick()

        # return the number of ticks
        if time_last_tick < event_time:
            return_val = 0
        else:
            return_val = int(float(time_last_tick - event_time) / float(self.period))

        return return_val

    # ======================== private =========================================

    @property
    def period(self):

        if self._period is None:
            self._period = float(1) / float(self.frequency)  # nominal period
            self._period += float(self.drift / 1000000.0) * float(self._period)  # apply drift

        return self._period
