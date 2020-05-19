from __future__ import print_function

import json
import logging

from openvisualizer.client.plugins.plugin import Plugin
from openvisualizer.client.view import View
from openvisualizer.motehandler.motestate.motestate import MoteState


@Plugin.record_view("msf")
class MSF(View):
    def __init__(self, proxy, mote_id, refresh_rate):
        super(MSF, self).__init__(proxy, mote_id, refresh_rate)

        self.title = 'msf'

    def render(self, ms=None):
        super(MSF, self).render()
        msf_values = json.loads(ms[MoteState.ST_MSF])
        print(msf_values)

    def run(self):
        logging.debug("Enabling blessed fullscreen")
        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            super(MSF, self).run()
        logging.debug("Exiting blessed fullscreen")
