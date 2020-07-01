#!/usr/bin/python
# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import threading


class TimeLineStats(object):

    def __init__(self):
        self.numEvents = 0

    def increment_events(self):
        self.numEvents += 1

    def get_num_events(self):
        return self.numEvents


class TimeLineEvent(object):

    def __init__(self, mote_id, at_time, cb, desc):
        self.at_time = at_time
        self.mote_id = mote_id
        self.desc = desc
        self.cb = cb

    def __str__(self):
        return '{0} {1}: {2}'.format(self.at_time, self.mote_id, self.desc)


class TimeLine(threading.Thread):
    """ The timeline of the engine. """

    def __init__(self):

        # store params
        from openvisualizer.simengine import simengine
        self.engine = simengine.SimEngine()

        # local variables
        self.current_time = 0  # current time
        self.timeline = []  # list of upcoming events
        self.first_event_passed = False
        self.first_event = threading.Lock()
        self.first_event.acquire()
        self.first_event_lock = threading.Lock()
        self.stats = TimeLineStats()

        # logging
        self.log = logging.getLogger('Timeline')
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(logging.NullHandler())

        # initialize parent class
        super(TimeLine, self).__init__()

        # set thread name
        self.setName('TimeLine')

        # thread daemon mode
        self.setDaemon(True)

    def run(self):
        # log
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('starting')

        # log
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('waiting for first event')

        # wait for the first event to be scheduled
        self.first_event.acquire()
        self.engine.indicate_first_event_passed()

        # log
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('first event scheduled')

        # apply the delay
        self.engine.pause_or_delay()

        while True:
            # detect the end of the simulation
            if len(self.timeline) == 0:
                output = ''
                output += 'end of simulation reached\n'
                output += ' - current_time=' + str(self.get_current_time()) + '\n'
                self.log.warning(output)
                raise StopIteration(output)

            # pop the event at the head of the timeline
            event = self.timeline.pop(0)

            # make sure that this event is later in time than the previous
            if not self.current_time <= event.at_time:
                self.log.critical("Current time {} exceeds event time: {}".format(self.current_time, event))
                assert False

            # record the current time
            self.current_time = event.at_time

            # log
            if self.log.isEnabledFor(logging.DEBUG):
                self.log.debug('\n\nnow {0:.6f}, executing {1}@{2}'.format(event.at_time, event.desc, event.mote_id))

            # call the event's callback
            self.engine.get_mote_handler_by_id(event.mote_id).handle_event(event.cb)

            # update statistics
            self.stats.increment_events()

            # apply the delay
            self.engine.pause_or_delay()

    # ======================== public ==========================================

    def get_current_time(self):
        return self.current_time

    def schedule_event(self, at_time, mote_id, cb, desc):
        """
        Add an event into the timeline

        :param at_time: The time at which this event should be called.
        :param mote_id: Mote identifier
        :param cb: The function to call when this event happens.
        :param desc: A unique description (a string) of this event.
        """

        # log
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('scheduling {0}@{1} at {2:.6f}'.format(desc, mote_id, at_time))

        # make sure that I'm scheduling an event in the future
        try:
            assert (self.current_time <= at_time)
        except AssertionError:
            self.engine.pause()
            output = ""
            output += "current_time: {}\n".format(str(self.current_time))
            output += "at_time:      {}\n".format(str(at_time))
            output += "mote_id:      {}\n".format(mote_id)
            output += "desc:         {}\n".format(str(desc))
            self.log.critical(output)
            raise

        # create a new event
        new_event = TimeLineEvent(mote_id, at_time, cb, desc)

        # remove any event already in the queue with same description
        for i in range(len(self.timeline)):
            if (self.timeline[i].mote_id == mote_id and
                    self.timeline[i].desc == desc):
                self.timeline.pop(i)
                break

        # look for where to put this event
        i = 0
        while i < len(self.timeline):
            if new_event.at_time > self.timeline[i].at_time:
                i += 1
            else:
                break

        # insert the new event
        self.timeline.insert(i, new_event)

        # start the timeline, if applicable
        with self.first_event_lock:
            if not self.first_event_passed:
                self.first_event_passed = True
                self.first_event.release()

    def cancel_event(self, mote_id, desc):
        """
        Cancels all events identified by their description

        :param mote_id: Mote identifier
        :param desc: A unique description (a string) of this event.

        :returns:    The number of events canceled.
        """

        # log
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cancelEvent {0}@{1}'.format(desc, mote_id))

        # initialize return variable
        num_events_canceled = 0

        # remove any event already the queue with same description
        i = 0
        while i < len(self.timeline):
            if self.timeline[i].mote_id == mote_id and self.timeline[i].desc == desc:
                self.timeline.pop(i)
                num_events_canceled += 1
            else:
                i += 1

        # return the number of events canceled
        return num_events_canceled

    def get_events(self):
        return [[ev.at_time, ev.mote_id, ev.desc] for ev in self.timeline]

    def get_stats(self):
        return self.stats

    # ======================== private =========================================

    def _print_timeline(self):
        output = ''
        for event in self.timeline:
            output += '\n' + str(event)
        return output

    # ======================== helpers =========================================
