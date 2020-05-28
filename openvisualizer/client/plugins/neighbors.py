from __future__ import print_function

import json
import logging
from math import ceil

from openvisualizer.client.plugins.plugin import Plugin
from openvisualizer.client.view import View
from openvisualizer.motehandler.motestate.motestate import MoteState


@Plugin.record_view("neighbors")
class Neighbors(View):
    COLOR_HDR_MARGIN = 7.5
    COLOR_LINE_MARGIN = 15

    def __init__(self, proxy, mote_id, refresh_rate):
        super(Neighbors, self).__init__(proxy, mote_id, refresh_rate)

        self.title = 'neighbors'

    def render(self, ms=None):
        super(Neighbors, self).render()
        neighbors = json.loads(ms[MoteState.ST_NEIGHBORS])
        neighbor_rows = []
        neighbor_info = {}

        yb = self.term.bold_yellow
        n = self.term.normal
        w = int(self.term.width / 2)

        for nb in neighbors:
            if int(nb['used']):
                neighbor_rows.append(nb)

        if len(neighbor_rows) == 0:
            print(self.term.red_bold + 'No neighbors for this mote' + self.term.normal)
            return

        addr_headers, stable_neighbor, join_prio = [], [], []
        secure, rssi, backoff, dagrank = [], [], [], []

        for neighbor in neighbor_rows:
            addr_headers.append('|{}{:^13s}{}'.format(yb, str(neighbor['addr'][-11:-5]).replace('-', ''), n))
            stable_neighbor.append('|{:^13s}'.format('Y' if int((neighbor['stableNeighbor'])) else 'N'))
            secure.append('|{:^13s}'.format('Y' if not int((neighbor['insecure'])) else 'N'))
            rssi.append('|{:^13s}'.format(str((neighbor['rssi']))))
            backoff.append('|{:^13s}'.format(str((neighbor['backoffExponent']))))
            dagrank.append('|{:^13s}'.format(str((neighbor['DAGrank']))))
            join_prio.append('|{:^13s}'.format(str((neighbor['joinPrio']))))

        header = ''.join(addr_headers) + '|'
        line = ''.join(['-'] * (len(header) - len(addr_headers) * self.COLOR_LINE_MARGIN))
        neighbor_info['Stable '] = ''.join(stable_neighbor) + '|'
        neighbor_info['Secure '] = ''.join(secure) + '|'
        neighbor_info['RSSI '] = ''.join(rssi) + '|'
        neighbor_info['BackOff Exponent '] = ''.join(backoff) + '|'
        neighbor_info['DAGrank '] = ''.join(dagrank) + '|'
        neighbor_info['Join Priority '] = ''.join(join_prio) + '|'

        print(line.rjust(abs(w + int(len(line) / 2))))
        print(header.rjust(abs(w + int(len(header) / 2) + int(ceil(len(addr_headers) * self.COLOR_HDR_MARGIN) - 1))))
        print(line.rjust(abs(w + int(len(line) / 2))))

        for k, v in neighbor_info.items():
            print(k.rjust(abs(w - int(len(v) / 2) - 1)), end='')
            print(v.rjust(abs(int(len(v) / 2))))

        print(line.rjust(abs(w + int(len(line) / 2))))

    def run(self):
        logging.debug("Enabling blessed fullscreen")
        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            super(Neighbors, self).run()
        logging.debug("Exiting blessed fullscreen")
