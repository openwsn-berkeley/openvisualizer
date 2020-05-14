from __future__ import print_function

import json
import logging
import sys
from collections import deque

from openvisualizer.client.plugins.plugin import Plugin
from openvisualizer.client.view import View
from openvisualizer.motehandler.motestate.motestate import MoteState


@Plugin.record_view("pktqueue")
class PktQueue(View):
    def __init__(self, proxy, mote_id, refresh_rate, graphic=False):
        super(PktQueue, self).__init__(proxy, mote_id, refresh_rate)

        self.title = 'pktqueue'
        self.graphic = graphic

        # graphical view
        self.pkt_history = None
        self._build_pkt_history()

    def run(self):
        logging.debug("Enabling blessed fullscreen")
        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            super(PktQueue, self).run()
        logging.debug("Exiting blessed fullscreen")

    def _build_pkt_history(self):
        self.prv_width = self.term.width

        logging.info('Change in size terminal, recalculate figures')

        if self.pkt_history is None:
            self.pkt_history = deque([0] * (self.term.width - 10))

        elif len(self.pkt_history) < self.term.width - 10:
            logging.debug("Appending to history: {}".format(self.term.width - 10 - len(self.pkt_history)))
            old = len(self.pkt_history)
            for i in range(self.term.width - 10 - len(self.pkt_history)):
                self.pkt_history.appendleft(0)
            logging.debug("Old {} vs new {}".format(old, len(self.pkt_history)))

        elif len(self.pkt_history) > self.term.width - 10:
            logging.debug("Popping from history: {}".format(len(self.pkt_history) - (self.term.width - 10)))
            old = len(self.pkt_history)
            for i in range(len(self.pkt_history) - (self.term.width - 10)):
                _ = self.pkt_history.popleft()
            logging.debug("Old {} vs new {}".format(old, len(self.pkt_history)))

        else:
            # they are equal, this should not happen
            pass

        # (re)build axis
        self.axis = ''.join(['-'] * (self.term.width - 10)) + '>'

    def render(self, ms=None):
        super(PktQueue, self).render()
        queue = json.loads(ms[MoteState.ST_QUEUE])

        if not self.graphic:
            width = int(self.term.width / 2)
            print('{:>{}}    {}    {}'.format('OWNER', width - 5, '|', 'CREATOR'))

            bar = '----------------------------'
            print('{:>{}}'.format(bar, width + int(len(bar) / 2)))
            for row in queue:
                print('{:>{}}    {}    {}'.format(row['owner'], width - 5, '|', row['creator']))

        else:
            if self.term.width != self.prv_width:
                self._build_pkt_history()

            pkt_count = 0
            for row in queue:
                if row['creator'] != '0 (NULL)':
                    logging.debug('Occupied buffer space')
                    pkt_count += 1

            self.pkt_history.popleft()
            self.pkt_history.append(pkt_count)
            logging.info("PktQueue history: {}".format(self.pkt_history))

            grid = self._build_grid(len(queue))

            print(self.term.bold + ' Every cursor block \'_\' represents: {}s'.format(
                self.refresh_rate) + self.term.normal)
            print('\n', end='')
            for row in grid:
                line = ''.join([' ' if x == 0 else self.term.on_green + ' ' + self.term.normal for x in row])
                if max(row) > 0:
                    print(self.term.move_right(4) + line.rjust(int(self.term.width / 2) + int(len(line) / 2)))

            print(self.axis.rjust(int(self.term.width / 2) + int(len(self.axis) / 2)))
            axis_text = '<-- time frame: {}s -->'.format(len(self.axis) * self.refresh_rate)
            print(axis_text.rjust(int(self.term.width / 2) + int(len(axis_text) / 2)))

            sys.stdout.flush()

    def _build_grid(self, queue_depth):
        grid = [[0 for x in range(len(self.pkt_history))] for y in range(queue_depth)]
        for x, pc in enumerate(self.pkt_history):
            if pc > 0:
                for i in range(pc):
                    grid[len(grid) - 1 - i][x] = 1
        return grid
