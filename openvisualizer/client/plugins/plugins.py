from __future__ import print_function

import json
import logging
import sys

from openvisualizer.client.view import View
from openvisualizer.motehandler.motestate.motestate import MoteState


class Plugins(object):
    views = {}

    @classmethod
    def record_view(cls, view_id):
        """Decorator to record all the supported views dynamically"""

        def decorator(the_class):
            if not issubclass(the_class, View):
                raise ValueError("Can only decorate subclass of View")
            cls.views[view_id] = the_class
            return the_class

        return decorator


@Plugins.record_view("macstats")
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


@Plugins.record_view("pktqueue")
class PktQueue(View):
    def __init__(self, proxy, mote_id, refresh_rate):
        super(PktQueue, self).__init__(proxy, mote_id, refresh_rate)

        self.title = 'pktqueue'

    def render(self, ms=None):
        super(PktQueue, self).render()
        queue = json.loads(ms[MoteState.ST_QUEUE])
        width = int(self.term.width / 2)
        print('{:>{}}    {}    {}'.format('OWNER', width - 5, '|', 'CREATOR'))

        bar = '----------------------------'
        print('{:>{}}'.format(bar, width + int(len(bar) / 2)))
        for row in queue:
            print('{:>{}}    {}    {}'.format(row['owner'], width - 5, '|', row['creator']))

        sys.stdout.flush()
