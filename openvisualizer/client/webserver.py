#!/usr/bin/python
# Copyright (c) 2013, Ken Bannister.
# All rights reserved.
#
# Released under the BSD 2-Clause license as published at the link below.
# http://opensource.org/licenses/BSD-2-Clause
import datetime
import functools
import json
import logging
import re
import socket
import xmlrpclib

import bottle
import pkg_resources

from openvisualizer import VERSION, PACKAGE_NAME

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
st = logging.StreamHandler()
st.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s %(message)s', datefmt="%H:%M:%S"))
logger.addHandler(st)

# add default parameters to all bottle templates
bottle.view = functools.partial(bottle.view, ovVersion=VERSION)


class WebServer:
    """ Provides web UI for OpenVisualizer."""

    def __init__(self, bottle_srv, rpc_server_addr, debug):
        """
        :param bottle_srv: Bottle server instance
        """
        logger.debug('create instance')

        # store params
        self.rpc_server = xmlrpclib.ServerProxy('http://{}:{}'.format(*rpc_server_addr))
        self.bottle_srv = bottle_srv

        self._define_routes()

        # To find page templates
        templates_path = '/'.join(('client', 'web_files', 'templates'))
        templates_path = pkg_resources.resource_filename(PACKAGE_NAME, templates_path)
        bottle.TEMPLATE_PATH.append(templates_path)

    # ======================== public ==========================================

    # ======================== private =========================================

    def _define_routes(self):
        """
        Matches web URL to impelementing method. Cannot use @route annotations on the methods due to the class-based
        implementation.
        """
        self.bottle_srv.route(path='/', callback=self._show_moteview)
        self.bottle_srv.route(path='/moteview', callback=self._show_moteview)
        self.bottle_srv.route(path='/moteview/:moteid', callback=self._show_moteview)
        self.bottle_srv.route(path='/motedata/:moteid', callback=self._get_mote_data)
        self.bottle_srv.route(path='/toggleDAGroot/:moteid', callback=self._toggle_dagroot)
        self.bottle_srv.route(path='/eventBus', callback=self._show_event_bus)
        self.bottle_srv.route(path='/routing', callback=self._show_routing)
        self.bottle_srv.route(path='/routing/dag', callback=self._show_dag)
        self.bottle_srv.route(path='/connectivity', callback=self._show_connectivity)
        self.bottle_srv.route(path='/connectivity/motes', callback=self._show_motes_connectivity)
        self.bottle_srv.route(path='/eventdata', callback=self._get_event_data)
        self.bottle_srv.route(path='/wiresharkDebug/:enabled', callback=self._set_wireshark_debug)
        self.bottle_srv.route(path='/gologicDebug/:enabled', callback=WebServer._set_gologic_debug)
        self.bottle_srv.route(path='/topology', callback=self._topology_page)
        self.bottle_srv.route(path='/topology/data', callback=self._topology_data)
        self.bottle_srv.route(path='/topology/download', callback=self._topology_download)
        self.bottle_srv.route(path='/topology/motes', method='POST', callback=self._topology_motes_update)
        self.bottle_srv.route(path='/topology/connections', method='PUT', callback=self._topology_connections_create)
        self.bottle_srv.route(path='/topology/connections', method='POST', callback=self._topology_connections_update)
        self.bottle_srv.route(path='/topology/connections', method='DELETE', callback=self._topology_connections_delete)
        self.bottle_srv.route(path='/topology/route', method='GET', callback=self._topology_route_retrieve)
        self.bottle_srv.route(path='/static/<filepath:path>', callback=WebServer._server_static)

    @bottle.view('moteview.tmpl')
    def _show_moteview(self, moteid=None):
        """
        Collects the list of motes, and the requested mote to view.
        :param moteid: 16-bit ID of mote (optional)
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("moteview moteid parameter is {0}".format(moteid))

        try:
            mote_list = self.rpc_server.get_mote_dict().keys()
        except socket.error as err:
            logger.error(err)
            return {}

        tmpl_data = {
            'motelist': mote_list,
            'requested_mote': moteid if moteid else 'none',
        }
        return tmpl_data

    @staticmethod
    def _server_static(filepath):
        static_path = '/'.join(('client', 'web_files', 'static'))
        static_path = pkg_resources.resource_filename(PACKAGE_NAME, static_path)

        return bottle.static_file(filepath, root=static_path)

    def _toggle_dagroot(self, moteid):
        """
        Triggers toggle DAGroot state, via MoteState. No real response. Page is updated when next retrieve mote data.
        :param moteid: 16-bit ID of mote
        """

        logger.debug('Toggle root status for moteid {0}'.format(moteid))
        try:
            ms = self.rpc_server.get_mote_state(moteid)
        except xmlrpclib.Fault as err:
            logger.error("A fault occurred: {}".format(err))
            return '{"result" : "fail"}'
        except socket.error as err:
            logger.error(err)
            return '{}'

        if ms:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Found mote {0} in mote_states'.format(moteid))
            try:
                self.rpc_server.set_root(moteid)
            except socket.error as err:
                logger.error(err)
                return '{}'
            return '{"result" : "success"}'
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Mote {0} not found in mote_states'.format(moteid))
            return '{"result" : "fail"}'

    def _get_mote_data(self, moteid):
        """
        Collects data for the provided mote.
        :param moteid: 16-bit ID of mote
        """
        states = {}

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Get JSON data for moteid {0}'.format(moteid))
        try:
            states = self.rpc_server.get_mote_state(moteid)
        except xmlrpclib.Fault as err:
            logger.error("Could not fetch mote state for mote {}: {}".format(moteid, err))
            return states
        except socket.error as err:
            logger.error(err)
            return {}
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Found mote {0} in mote_states'.format(moteid))
        return states

    def _set_wireshark_debug(self, enabled):
        """
        Selects whether eventBus must export debug packets.
        :param enabled: 'true' if enabled; any other value considered false
        """
        logger.info('Enable wireshark debug: {0}'.format(enabled))
        try:
            if enabled.strip() == 'true':
                _ = self.rpc_server.enable_wireshark_debug()
            elif enabled.strip() == 'false':
                _ = self.rpc_server.disable_wireshark_debug()
            else:
                logger.error('Illegal value for \'_set_wireshark_debug\'')
        except xmlrpclib.Fault as err:
            logger.error("Caught a server fault: {}".format(err))
        except socket.error as err:
            logger.error(err)

    @staticmethod
    def _set_gologic_debug(enabled):
        logger.info('Enable GoLogic debug : {0}'.format(enabled))
        # vcdlogger.VcdLogger().set_enabled(enabled == 'true')
        return '{"result" : "success"}'

    @bottle.view('eventBus.tmpl')
    def _show_event_bus(self):
        """ Simple page; data for the page template is identical to the data for periodic updates of event list. """
        tmpl_data = self._get_event_data().copy()
        return tmpl_data

    def _show_dag(self):
        try:
            states, edges = self.rpc_server.get_dag()
        except socket.error as err:
            logger.error(err)
            return {}

        return {'states': states, 'edges': edges}

    @bottle.view('connectivity.tmpl')
    def _show_connectivity(self):
        return {}

    def _show_motes_connectivity(self):
        try:
            states, edges = self.rpc_server.get_motes_connectivity()
        except socket.error as err:
            logger.error(err)
            return {}
        return {'states': states, 'edges': edges}

    @bottle.view('routing.tmpl')
    def _show_routing(self):
        return {}

    @bottle.view('topology.tmpl')
    def _topology_page(self):
        """ Retrieve the HTML/JS page. """
        return {}

    def _topology_data(self):
        """ Retrieve the topology data, in JSON format. """
        data = {}
        try:
            data = self.rpc_server.get_network_topology()
        except socket.error as err:
            logger.error(err)
        return data

    def _topology_motes_update(self):
        """ Update the network topology (simulation only)"""

        motes_temp = {}
        for (k, v) in bottle.request.forms.items():
            m = re.match(r"motes\[([0-9]*)\]\[([a-z]*)\]", k)

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

        try:
            _ = self.rpc_server.update_network_topology(json.dumps(motes_temp))
        except socket.error as err:
            logger.error(err)

    def _topology_connections_create(self):
        data = bottle.request.forms
        assert sorted(data.keys()) == sorted(['fromMote', 'toMote'])

        from_mote = int(data['fromMote'])
        to_mote = int(data['toMote'])

        try:
            _ = self.rpc_server.create_motes_connection(from_mote, to_mote)
        except socket.error as err:
            logger.error(err)

    def _topology_connections_update(self):
        data = bottle.request.forms
        assert sorted(data.keys()) == sorted(['fromMote', 'toMote', 'pdr'])

        from_mote = int(data['fromMote'])
        to_mote = int(data['toMote'])
        pdr = float(data['pdr'])

        try:
            _ = self.rpc_server.update_motes_connection(from_mote, to_mote, pdr)
        except socket.error as err:
            logger.error(err)

    def _topology_connections_delete(self):
        data = bottle.request.forms
        assert sorted(data.keys()) == sorted(['fromMote', 'toMote'])

        from_mote = int(data['fromMote'])
        to_mote = int(data['toMote'])

        try:
            _ = self.rpc_server.delete_motes_connection(from_mote, to_mote)
        except socket.error as err:
            logger.error(err)

    def _topology_route_retrieve(self):
        data = bottle.request.query
        assert data.keys() == ['destination']

        destination_eui = [0x14, 0x15, 0x92, 0xcc, 0x00, 0x00, 0x00, int(data['destination'])]

        route = {}
        try:
            route = self.rpc_server.retrieve_routing_path(destination_eui)
        except socket.error:
            pass

        return route

    def _topology_download(self):
        """ Retrieve the topology data, in JSON format, and download it. """
        data = self._topology_data()
        now = datetime.datetime.now()

        try:
            dagroot = self.rpc_server.get_dagroot()
        except socket.error as err:
            logger.error(err)
            return {}

        if dagroot is not None:
            dagroot = ''.join('%02x' % b for b in dagroot)

        data['DAGroot'] = dagroot

        bottle.response.headers['Content-disposition'] = 'attachment; filename=topology_data_' + now.strftime(
            "%d-%m-%y_%Hh%M") + '.json'
        bottle.response.headers['filename'] = 'test.json'
        bottle.response.headers['Content-type'] = 'application/json'

        return data

    def _get_event_data(self):
        try:
            res = {
                'isDebugPkts': 'true' if self.rpc_server.get_wireshark_debug() else 'false',
                'stats': self.rpc_server.get_ebm_stats(),
            }
        except socket.error as err:
            logger.error(err)
            return {}

        return res
