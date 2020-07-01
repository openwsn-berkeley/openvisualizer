import json
import logging
from math import ceil

from openvisualizer.client.plugins.plugin import Plugin
from openvisualizer.client.view import View
from openvisualizer.motehandler.motestate.motestate import MoteState


@Plugin.record_view("schedule")
class Schedule(View):
    COLOR_LINE_MARGIN = 15
    COLOR_HDR_MARGIN = 7.5

    def __init__(self, proxy, mote_id, refresh_rate):
        super(Schedule, self).__init__(proxy, mote_id, refresh_rate)

        self.title = 'schedule'

    def render(self, ms=None):
        yb = self.term.bold_yellow
        n = self.term.normal

        columns = []
        columns += ['|' + yb + '  Type  ' + n]
        columns += ['|' + yb + ' S ' + n]
        # columns += ['|' + yb + ' A ' + n]
        columns += ['|' + yb + '  Nb  ' + n]
        columns += ['|' + yb + ' SlotOf ' + n]
        columns += ['|' + yb + ' ChOf ' + n]
        columns += ['|' + yb + '   last ASN   ' + n]
        columns += ['|' + yb + ' #TX ' + n]
        columns += ['|' + yb + ' #TX-ACK ' + n]
        columns += ['|' + yb + ' #RX ' + n + '|']

        header = ''.join(columns)
        hdr_line = ''.join(['-'] * (len(header) - len(columns) * self.COLOR_LINE_MARGIN))

        super(Schedule, self).render()
        schedule_rows = json.loads(ms[MoteState.ST_SCHEDULE])

        active_cells = []

        for row in schedule_rows:
            if row['type'] != '0 (OFF)':
                active_cells.append(row)

        active_cells.sort(key=lambda x: x['slotOffset'])

        w = int(self.term.width / 2)

        print(hdr_line.rjust(abs(w + int(len(hdr_line) / 2))))
        print(header.rjust(abs(w + int(len(header) / 2) + int(ceil(len(columns) * self.COLOR_HDR_MARGIN)))))
        print(hdr_line.rjust(abs(w + int(len(hdr_line) / 2))))

        for r in active_cells:
            c, shift = self._get_row_color(str(r['type'])[2:])
            # r_str = '|{}{:^8s}{}|{:^3s}|{:^3s}|{:^6s}|{:^8s}|{:^6s}|{:^14s}|{:^5s}|{:^9s}|{:^5s}|'.format(
            r_str = '|{}{:^8s}{}|{:^3s}|{:^6s}|{:^8s}|{:^6s}|{:^14s}|{:^5s}|{:^9s}|{:^5s}|'.format(
                c, str(r['type'])[2:], n,
                'X' if int(r['shared']) else ' ',
                # 'X' if int(r['isAutoCell']) else ' ',
                'ANY' if 'anycast' in str(r['neighbor']) else str(r['neighbor'])[-11:-6].replace('-', ''),
                str(r['slotOffset']),
                str(r['channelOffset']),
                hex(int(str(r['lastUsedAsn']), 16)),
                str(r['numTx']),
                str(r['numTxACK']),
                str(r['numRx']))

            print(r_str.rjust(abs(w + int(len(r_str) / 2) + shift)))

        print(hdr_line.rjust(abs(w + int(len(hdr_line) / 2))))
        print('\n')
        print('{}{}:{}{:>15}'.format(yb, 'S', n, 'Shared cell?'))
        # print('{}{}:{}{:>19}'.format(yb, 'A', n, 'Autonomous cell?'))
        print('{}{}:{}{:>20}'.format(yb, 'Nb', n, '16-bit Neighbor ID'))

    def run(self):
        logging.debug("Enabling blessed fullscreen")
        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            super(Schedule, self).run()
        logging.debug("Exiting blessed fullscreen")

    def _get_row_color(self, cell_type):
        if '(TXRX)' == cell_type:
            return self.term.purple, 12
        elif '(TX)' == cell_type:
            return self.term.blue, 6
        else:
            return self.term.red, 6
