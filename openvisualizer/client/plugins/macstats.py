import json
import logging

from openvisualizer.client.plugins.plugin import Plugin
from openvisualizer.client.view import View
from openvisualizer.motehandler.motestate.motestate import MoteState


@Plugin.record_view("macstats")
class MacStats(View):
    def __init__(self, proxy, mote_id, refresh_rate):
        super(MacStats, self).__init__(proxy, mote_id, refresh_rate)

        self.title = 'macstats'

    def render(self, ms=None):
        super(MacStats, self).render()
        state_dict = json.loads(ms[MoteState.ST_MACSTATS])[0]
        for stat in state_dict:
            print('{:>13}:{:>20}'.format(str(stat), str(state_dict[stat])))

    def run(self):
        logging.debug("Enabling blessed fullscreen")
        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            super(MacStats, self).run()
        logging.debug("Exiting blessed fullscreen")
