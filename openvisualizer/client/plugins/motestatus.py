from __future__ import print_function

import json
import logging

from openvisualizer.client.plugins.plugin import Plugin
from openvisualizer.client.utils import transform_into_ipv6
from openvisualizer.client.view import View
from openvisualizer.motehandler.motestate.motestate import MoteState


@Plugin.record_view("motestatus")
class MoteStatus(View):
    def __init__(self, proxy, mote_id, refresh_rate):
        super(MoteStatus, self).__init__(proxy, mote_id, refresh_rate)

        self.title = 'motestatus'

    def render(self, ms=None):
        super(MoteStatus, self).render()

        is_sync = json.loads(ms[MoteState.ST_ISSYNC])[0]
        dagrank = json.loads(ms[MoteState.ST_MYDAGRANK])[0]
        id_manager = json.loads(ms[MoteState.ST_IDMANAGER])[0]
        joined = json.loads(ms[MoteState.ST_JOINED])[0]
        asn = json.loads(ms[MoteState.ST_ASN])[0]
        kaperiod = json.loads(ms[MoteState.ST_KAPERIOD])[0]

        print('\n', end='')
        _str = self._build_str(10, int(id_manager['isDAGroot']))
        print(_str.format('DAG root', id_manager['isDAGroot']))
        _str = self._build_str(6, int(is_sync['isSync']))
        print(_str.format('Synchronized', is_sync['isSync']))
        _str = self._build_str(3, int(joined['joinedAsn'], 16))
        print(_str.format('Sec. Joined@ASN', int(joined['joinedAsn'], 16)))
        _str = self._build_str(10)
        print(_str.format('DAG rank', dagrank['myDAGrank']))
        _str = self._build_str(12)
        print(_str.format('PAN ID', id_manager['myPANID'][:-8]))
        _str = self._build_str(6)
        print(_str.format('IPv6 address',
                          transform_into_ipv6(id_manager['myPrefix'][:-9] + '-' + id_manager['my64bID'][:-5])))

        print('\n', end='')
        _str = self._build_str(7)
        print(_str.format('Current ASN', asn['asn']))

        print('\n', end='')
        _str = self._build_str(9)
        print(_str.format('KA Period', kaperiod['kaPeriod']))

    def _build_str(self, offset, flag=None):
        b = self.term.bold
        n = self.term.normal
        red = self.term.bold_red
        green = self.term.bold_green

        if flag is None:
            return b + '{}' + n + self.term.move_right(offset) + '{}'

        if flag:
            return b + '{}' + n + self.term.move_right(offset) + green + '{}' + n
        else:
            return b + '{}' + n + self.term.move_right(offset) + red + '{}' + n

    def run(self):
        logging.debug("Enabling blessed fullscreen")
        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            super(MoteStatus, self).run()
        logging.debug("Exiting blessed fullscreen")
