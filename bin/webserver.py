#!/usr/bin/python
# Copyright (c) 2013, Ken Bannister.
# All rights reserved.
#
# Released under the BSD 2-Clause license as published at the link below.
# http://opensource.org/licenses/BSD-2-Clause

import datetime
import functools
import logging
import re
import time

import bottle
from bottle import view, response

from openvisualizer import version
from openvisualizer.bspemulator import vcdlogger
from openvisualizer.SimEngine import SimEngine
from openvisualizer.eventbus.eventbusclient import EventBusClient
from openvisualizer.motehandler.motestate.motestate import MoteState

log = logging.getLogger('openVisualizerWeb')

# add default parameters to all bottle templates
view = functools.partial(view, ovVersion='.'.join(list([str(v) for v in version.VERSION])))


class WebServer(EventBusClient):
    def __init__(self, app, web_srv):
        """
        :param app: OpenVisualizerApp
        :param web_srv: Web server
        """
        log.info('Creating OpenVisualizerWeb')

        # store params
        self.app = app
        self.engine = SimEngine.SimEngine()
        self.web_srv = web_srv

        # initialize parent classes
        super(WebServer, self).__init__(name='OpenVisualizerWeb', registrations=[])

        # command support
        self.doc_header = 'Commands (type "help all" or "help <topic>"):'
        self.prompt = '> '
        self.intro = '\nOpenVisualizer  (type "help" for commands)'

        self._define_routes()
        # To find page templates
        bottle.TEMPLATE_PATH.append('{0}/web_files/templates/'.format(self.app.data_dir))

        # Set DAGroots imported
        if app.dagroot_list:
            # Wait the end of the mote threads creation
            time.sleep(1)
            for moteid in app.dagroot_list:
                self._show_moteview(moteid)
                self._get_mote_data(moteid)
                self._toggle_dagroot(moteid)

    # ======================== public ==========================================

    # ======================== private =========================================

    def _define_routes(self):
        """
        Matches web URL to impelementing method. Cannot use @route annotations on the methods due to the class-based
        implementation.
        """
        self.web_srv.route(path='/', callback=self._show_moteview)
        self.web_srv.route(path='/moteview', callback=self._show_moteview)
        self.web_srv.route(path='/moteview/:moteid', callback=self._show_moteview)
        self.web_srv.route(path='/motedata/:moteid', callback=self._get_mote_data)
        self.web_srv.route(path='/toggleDAGroot/:moteid', callback=self._toggle_dagroot)
        self.web_srv.route(path='/eventBus', callback=self._show_event_bus)
        self.web_srv.route(path='/routing', callback=self._show_routing)
        self.web_srv.route(path='/routing/dag', callback=self._show_dag)
        self.web_srv.route(path='/connectivity', callback=self._show_connectivity)
        self.web_srv.route(path='/connectivity/motes', callback=self._show_motes_connectivity)
        self.web_srv.route(path='/eventdata', callback=self._get_event_data)
        self.web_srv.route(path='/wiresharkDebug/:enabled', callback=self._set_wireshark_debug)
        self.web_srv.route(path='/gologicDebug/:enabled', callback=self._set_gologic_debug)
        self.web_srv.route(path='/topology', callback=self._topology_page)
        self.web_srv.route(path='/topology/data', callback=self._topology_data)
        self.web_srv.route(path='/topology/download', callback=self._topology_download)
        self.web_srv.route(path='/topology/motes', method='POST', callback=self._topology_motes_update)
        self.web_srv.route(path='/topology/connections', method='PUT', callback=self._topology_connections_create)
        self.web_srv.route(path='/topology/connections', method='POST', callback=self._topology_connections_update)
        self.web_srv.route(path='/topology/connections', method='DELETE', callback=self._topology_connections_delete)
        self.web_srv.route(path='/topology/route', method='GET', callback=self._topology_route_retrieve)
        self.web_srv.route(path='/static/<filepath:path>', callback=self._server_static)

    @view('moteview.tmpl')
    def _show_moteview(self, moteid=None):
        """
        Collects the list of motes, and the requested mote to view.
        :param moteid: 16-bit ID of mote (optional)
        """
        if log.isEnabledFor(logging.DEBUG):
            log.debug("moteview moteid parameter is {0}".format(moteid))

        mote_list = self.app.get_mote_dict().keys()

        tmpl_data = {
            'motelist': mote_list,
            'requested_mote': moteid if moteid else 'none',
        }
        return tmpl_data

    def _server_static(self, filepath):
        return bottle.static_file(filepath, root='{0}/web_files/static/'.format(self.app.data_dir))

    def _toggle_dagroot(self, moteid):
        """
        Triggers toggle DAGroot state, via MoteState. No real response. Page is updated when next retrieve mote data.
        :param moteid: 16-bit ID of mote
        """

        log.info('Toggle root status for moteid {0}'.format(moteid))
        ms = self.app.get_mote_state(moteid)
        if ms:
            if log.isEnabledFor(logging.DEBUG):
                log.debug('Found mote {0} in mote_states'.format(moteid))
            ms.trigger_action(ms.TRIGGER_DAGROOT)
            return '{"result" : "success"}'
        else:
            if log.isEnabledFor(logging.DEBUG):
                log.debug('Mote {0} not found in mote_states'.format(moteid))
            return '{"result" : "fail"}'

    def _get_mote_data(self, moteid):
        """
        Collects data for the provided mote.
        :param moteid: 16-bit ID of mote
        """

        if log.isEnabledFor(logging.DEBUG):
            log.debug('Get JSON data for moteid {0}'.format(moteid))
        ms = self.app.get_mote_state(moteid)
        if ms:
            if log.isEnabledFor(logging.DEBUG):
                log.debug('Found mote {0} in mote_states'.format(moteid))
            states = {
                ms.ST_IDMANAGER: ms.get_state_elem(ms.ST_IDMANAGER).to_json('data'),
                ms.ST_ASN: ms.get_state_elem(ms.ST_ASN).to_json('data'),
                ms.ST_ISSYNC: ms.get_state_elem(ms.ST_ISSYNC).to_json('data'),
                ms.ST_MYDAGRANK: ms.get_state_elem(ms.ST_MYDAGRANK).to_json('data'),
                ms.ST_KAPERIOD: ms.get_state_elem(ms.ST_KAPERIOD).to_json('data'),
                ms.ST_OUPUTBUFFER: ms.get_state_elem(ms.ST_OUPUTBUFFER).to_json('data'),
                ms.ST_BACKOFF: ms.get_state_elem(ms.ST_BACKOFF).to_json('data'),
                ms.ST_MACSTATS: ms.get_state_elem(ms.ST_MACSTATS).to_json('data'),
                ms.ST_SCHEDULE: ms.get_state_elem(ms.ST_SCHEDULE).to_json('data'),
                ms.ST_QUEUE: ms.get_state_elem(ms.ST_QUEUE).to_json('data'),
                ms.ST_NEIGHBORS: ms.get_state_elem(ms.ST_NEIGHBORS).to_json('data'),
                ms.ST_JOINED: ms.get_state_elem(ms.ST_JOINED).to_json('data'),
            }
        else:
            if log.isEnabledFor(logging.DEBUG):
                log.debug('Mote {0} not found in mote_states'.format(moteid))
            states = {}
        return states

    def _set_wireshark_debug(self, enabled):
        """
        Selects whether eventBus must export debug packets.
        :param enabled: 'true' if enabled; any other value considered false
        """
        log.info('Enable wireshark debug : {0}'.format(enabled))
        self.app.ebm.set_wireshark_debug(enabled == 'true')
        return '{"result" : "success"}'

    def _set_gologic_debug(self, enabled):
        log.info('Enable GoLogic debug : {0}'.format(enabled))
        vcdlogger.VcdLogger().set_enabled(enabled == 'true')
        return '{"result" : "success"}'

    @view('eventBus.tmpl')
    def _show_event_bus(self):
        """ Simple page; data for the page template is identical to the data for periodic updates of event list. """
        tmpl_data = self._get_event_data().copy()
        return tmpl_data

    def _show_dag(self):
        states, edges = self.app.topology.getDAG()
        return {'states': states, 'edges': edges}

    @view('connectivity.tmpl')
    def _show_connectivity(self):
        return {}

    def _show_motes_connectivity(self):
        states, edges = self.app.get_motes_connectivity()
        return {'states': states, 'edges': edges}

    @view('routing.tmpl')
    def _show_routing(self):
        return {}

    @view('topology.tmpl')
    def _topology_page(self):
        """ Retrieve the HTML/JS page. """
        return {}

    def _topology_data(self):
        """ Retrieve the topology data, in JSON format. """

        motes = []
        rank = 0
        while True:
            try:
                mh = self.engine.getMoteHandler(rank)
                mote_id = mh.getId()
                (lat, lon) = mh.getLocation()
                motes += [{'id': mote_id, 'lat': lat, 'lon': lon}]
                rank += 1
            except IndexError:
                break

        # connections
        connections = self.engine.propagation.retrieveConnections()

        data = {'motes': motes, 'connections': connections}

        return data

    def _topology_motes_update(self):

        motes_temp = {}
        for (k, v) in bottle.request.forms.items():
            m = re.match("motes\[(\w+)\]\[(\w+)\]", k)

            assert m
            index = int(m.group(1))
            param = m.group(2)
            try:
                v = int(v)
            except ValueError:
                try:
                    v = float(v)
                except ValueError:
                    pass
            if index not in motes_temp:
                motes_temp[index] = {}
            motes_temp[index][param] = v

        for (_, v) in motes_temp.items():
            mh = self.engine.getMoteHandlerById(v['id'])
            mh.setLocation(v['lat'], v['lon'])

    def _topology_connections_create(self):

        data = bottle.request.forms
        assert sorted(data.keys()) == sorted(['fromMote', 'toMote'])

        from_mote = int(data['fromMote'])
        to_mote = int(data['toMote'])

        self.engine.propagation.createConnection(from_mote, to_mote)

    def _topology_connections_update(self):
        data = bottle.request.forms
        assert sorted(data.keys()) == sorted(['fromMote', 'toMote', 'pdr'])

        from_mote = int(data['fromMote'])
        to_mote = int(data['toMote'])
        pdr = float(data['pdr'])

        self.engine.propagation.updateConnection(from_mote, to_mote, pdr)

    def _topology_connections_delete(self):

        data = bottle.request.forms
        assert sorted(data.keys()) == sorted(['fromMote', 'toMote'])

        from_mote = int(data['fromMote'])
        to_mote = int(data['toMote'])

        self.engine.propagation.deleteConnection(from_mote, to_mote)

    def _topology_route_retrieve(self):

        data = bottle.request.query
        assert data.keys() == ['destination']

        destination_eui = [0x14, 0x15, 0x92, 0xcc, 0x00, 0x00, 0x00, int(data['destination'])]

        route = self._dispatch_and_get_result(signal='getSourceRoute', data=destination_eui)
        route = [r[-1] for r in route]
        data = {'route': route}

        return data

    def _topology_download(self):
        """ Retrieve the topology data, in JSON format, and download it. """
        data = self._topology_data()
        now = datetime.datetime.now()
        dagroot_list = []

        for ms in self.app.mote_states:
            if ms.get_state_elem(MoteState.ST_IDMANAGER).isDAGroot:
                dagroot_list.append(ms.get_state_elem(MoteState.ST_IDMANAGER).get_16b_addr()[1])

        data['DAGrootList'] = dagroot_list

        response.headers['Content-disposition'] = 'attachement; filename=topology_data_' + now.strftime(
            "%d-%m-%y_%Hh%M") + '.json'
        response.headers['filename'] = 'test.json'
        response.headers['Content-type'] = 'application/json'

        return data

    def _get_event_data(self):
        response = {
            'isDebugPkts': 'true' if self.app.ebm.wireshark_debug_enabled else 'false', 'stats': self.app.ebm.get_stats()
        }
        return response
