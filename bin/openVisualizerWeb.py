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
import os
import re
import signal
import threading
import time
from argparse import ArgumentParser
from cmd import Cmd

import bottle
import netifaces as ni
from bottle import view, response
from coap import coap

import openVisualizerApp
from openvisualizer import ovVersion
from openvisualizer.BspEmulator import VcdLogger
from openvisualizer.SimEngine import SimEngine
from openvisualizer.eventBus.eventBusClient import eventBusClient
from openvisualizer.motehandler.motestate.motestate import MoteState

log = logging.getLogger('openVisualizerWeb')

# add default parameters to all bottle templates
view = functools.partial(view, ovVersion='.'.join(list([str(v) for v in ovVersion.VERSION])))


class OpenVisualizerWeb(eventBusClient, Cmd):
    """
    Provides web UI for OpenVisualizer. Runs as a webapp in a Bottle web
    server.
    """

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
        eventBusClient.__init__(self, name='OpenVisualizerWeb', registrations=[])
        Cmd.__init__(self)

        # command support
        self.doc_header = 'Commands (type "help all" or "help <topic>"):'
        self.prompt = '> '
        self.intro = '\nOpenVisualizer  (type "help" for commands)'

        # used for remote motes :
        self.rover_motes = {}
        self.client = coap.coap(udpPort=9000)
        self.client.respTimeout = 2
        self.client.ackTimeout = 2
        self.client.maxRetransmit = 1

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

        # activate these routes only if remote_connector_server is available
        if self._is_rover_mode():
            self.web_srv.route(path='/rovers', callback=self._show_rovers)
            self.web_srv.route(path='/updateroverlist/:updatemsg', callback=self._update_rover_list)
            self.web_srv.route(path='/motesdiscovery/:srcip', callback=self._motes_discovery)

    def _is_rover_mode(self):
        return self.app.remote_connector_server is not None

    @view('rovers.tmpl')
    def _show_rovers(self):
        """ Handles the discovery and connection to remote motes using remote_connector_server component. """
        my_if_dict = {}
        for myif in ni.interfaces():
            my_if_dict[myif] = ni.ifaddresses(myif)
        tmpl_data = {
            'myifdict': my_if_dict,
            'roverMotes': self.rover_motes,
            'roverMode': self._is_rover_mode()
        }
        return tmpl_data

    def _update_rover_list(self, updatemsg):
        """
        Handles the devices discovery
        """

        cmd, rover_data = updatemsg.split('@')
        if cmd == "add":
            if rover_data not in self.rover_motes.keys():
                self.rover_motes[rover_data] = []
        elif cmd == "del":
            for rover_ip in rover_data.split(','):
                if rover_ip in self.rover_motes.keys() and not self.rover_motes[rover_ip]:
                    self.rover_motes.pop(rover_ip)
        elif cmd == "upload":
            new_rovers = rover_data.split(",")
            for newRover in new_rovers:
                if newRover not in self.rover_motes.keys():
                    self.rover_motes[newRover] = []
        elif cmd == "disconn":
            for rover_ip in rover_data.split(','):
                if rover_ip in self.rover_motes.keys():
                    self.app.remove_rover_motes(rover_ip, self.rover_motes.pop(rover_ip))
        mote_dict = self.app.get_mote_dict()
        for rover in self.rover_motes:
            for i, serial in enumerate(self.rover_motes[rover]):
                for moteID, serial_conn in mote_dict.items():
                    if serial == serial_conn:
                        self.rover_motes[rover][i] = moteID

        return json.dumps(self.rover_motes)

    def _motes_discovery(self, srcip):
        """
        Collects the list of motes available on the rover and connects them to oV
        Use connetest to first check service availability
        :param srcip: IP of the rover
        """

        coap_threads = []
        for rover_ip in self.rover_motes.keys():
            t = threading.Thread(target=self._get_coap_response, args=(srcip, rover_ip))
            t.setDaemon(True)
            t.start()
            coap_threads.append(t)
        for t in coap_threads:
            t.join()
        self.app.refresh_rover_motes(self.rover_motes)
        return json.dumps(self.rover_motes)

    def _get_coap_response(self, srcip, roverip):
        log.info("sending coap request to rover {0}".format(roverip))
        try:
            if ':' in roverip:
                response = self.client.PUT('coap://[{0}]/pcinfo'.format(roverip),
                                           payload=[ord(c) for c in (srcip + ';50000;' + roverip)])
            else:
                response = self.client.PUT('coap://{0}/pcinfo'.format(roverip),
                                           payload=[ord(c) for c in (srcip + ';50000;' + roverip)])
            payload = ''.join([chr(b) for b in response])
            self.rover_motes[roverip] = json.loads(payload)
            self.rover_motes[roverip] = [rm + '@' + roverip for rm in self.rover_motes[roverip]]
        except Exception as err:
            self.rover_motes[roverip] = str(err)

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
            'roverMode': self._is_rover_mode()
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
        self.app.ebm.setWiresharkDebug(enabled == 'true')
        return '{"result" : "success"}'

    def _set_gologic_debug(self, enabled):
        log.info('Enable GoLogic debug : {0}'.format(enabled))
        VcdLogger.VcdLogger().setEnabled(enabled == 'true')
        return '{"result" : "success"}'

    @view('eventBus.tmpl')
    def _show_event_bus(self):
        """ Simple page; data for the page template is identical to the data for periodic updates of event list. """
        tmpl_data = self._get_event_data().copy()
        tmpl_data['roverMode'] = self._is_rover_mode()
        return tmpl_data

    def _show_dag(self):
        states, edges = self.app.topology.getDAG()
        return {'states': states, 'edges': edges}

    @view('connectivity.tmpl')
    def _show_connectivity(self):
        return {'roverMode': self._is_rover_mode()}

    def _show_motes_connectivity(self):
        states, edges = self.app.get_motes_connectivity()
        return {'states': states, 'edges': edges}

    @view('routing.tmpl')
    def _show_routing(self):
        return {'roverMode': self._is_rover_mode()}

    @view('topology.tmpl')
    def _topology_page(self):
        """ Retrieve the HTML/JS page. """
        return {'roverMode': self._is_rover_mode()}

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

        route = self._dispatchAndGetResult(signal='getSourceRoute', data=destination_eui)
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
            'isDebugPkts': 'true' if self.app.ebm.wiresharkDebugEnabled else 'false', 'stats': self.app.ebm.getStats()
        }
        return response

    # ===== callbacks

    def do_state(self, arg):
        """
        Prints provided state, or lists states.
        Usage: state [state-name]
        """
        if not arg:
            for ms in self.app.mote_states:
                output = []
                output += ['Available states:']
                output += [' - {0}'.format(s) for s in ms.get_state_elem_names()]
                self.stdout.write('\n'.join(output))
            self.stdout.write('\n')
        else:
            for ms in self.app.mote_states:
                try:
                    self.stdout.write(str(ms.get_state_elem(arg)))
                    self.stdout.write('\n')
                except ValueError as err:
                    self.stdout.write(str(err))
                    self.stdout.write('\n')

    def do_list(self, arg):
        """ List available states. (Obsolete; use 'state' without parameters.) """
        self.do_state('')

    def do_root(self, arg):
        """
        Sets dagroot to the provided mote, or lists motes
        Usage: root [serial-port]
        """
        if not arg:
            self.stdout.write('Available ports:')
            if self.app.mote_states:
                for ms in self.app.mote_states:
                    self.stdout.write('  {0}'.format(ms.mote_connector.serialport))
            else:
                self.stdout.write('  <none>')
            self.stdout.write('\n')
        else:
            for ms in self.app.mote_states:
                try:
                    if ms.mote_connector.serialport == arg:
                        ms.trigger_action(MoteState.TRIGGER_DAGROOT)
                except ValueError as err:
                    self.stdout.write(str(err))
                    self.stdout.write('\n')

    def do_set(self, arg):
        """ Sets mote with parameters. """
        if not arg:
            self.stdout.write('Available ports:')
            if self.app.mote_states:
                for ms in self.app.mote_states:
                    self.stdout.write('  {0}'.format(ms.mote_connector.serialport))
            else:
                self.stdout.write('  <none>')
            self.stdout.write('\n')
        else:
            try:
                [port, command, parameter] = arg.split(' ')
                for ms in self.app.mote_states:
                    try:
                        if ms.mote_connector.serialport == port:
                            ms.trigger_action([MoteState.SET_COMMAND, command, parameter])
                    except ValueError as err:
                        self.stdout.write(err)
                        self.stdout.write('\n')
            except ValueError as err:
                print "{0}:{1}".format(type(err), err)

    def help_all(self):
        """ Lists first line of help for all documented commands. """
        names = self.get_names()
        names.sort()
        max_len = 65
        self.stdout.write(
            'type "help <topic>" for topic details\n'.format(80 - max_len - 3))
        for name in names:
            if name[:3] == 'do_':
                try:
                    doc = getattr(self, name).__doc__
                    if doc:
                        # Handle multi-line doc comments and format for length.
                        doc_lines = doc.splitlines()
                        doc = doc_lines[0]
                        if len(doc) == 0 and len(doc_lines) > 0:
                            doc = doc_lines[1].strip()
                        if len(doc) > max_len:
                            doc = doc[:max_len] + '...'
                        self.stdout.write('{0} - {1}\n'.format(
                            name[3:80 - max_len], doc))
                except AttributeError:
                    pass

    def do_quit(self, arg):
        self.app.close()
        os.kill(os.getpid(), signal.SIGTERM)
        return True

    def emptyline(self):
        return

    def cmdloop(self, intro=None):
        try:
            super(OpenVisualizerWeb, self).cmdloop(intro=intro)
        except KeyboardInterrupt:
            print("\nYou pressed Ctrl-C. Killing OpenVisualizer..\n")
            self.app.close()
            os.kill(os.getpid(), signal.SIGTERM)


# ============================ main ============================================

def _add_parser_args(parser):
    """ Adds arguments specific to web UI. """
    parser.add_argument('-H', '--host', dest='host', default='0.0.0.0', action='store', help='host address')
    parser.add_argument('-p', '--port', dest='port', default=8080, action='store', help='port number')


webapp = None
if __name__ == "__main__":
    parser = ArgumentParser()
    _add_parser_args(parser)
    arg_space = parser.parse_known_args()[0]

    # log
    log.info(
        'Initializing OpenVisualizerWeb with options: \n\t{0}'.format(
            '\n    '.join(
                [
                    'host = {0}'.format(arg_space.host),
                    'port = {0}'.format(arg_space.port)
                ]
            )
        )
    )

    # ===== start the app
    app = openVisualizerApp.main(parser)

    # ===== add a web interface
    websrv = bottle.Bottle()
    webapp = OpenVisualizerWeb(app, websrv)

    # start web interface in a separate thread
    webthread = threading.Thread(
        target=websrv.run,
        kwargs={
            'host': arg_space.host,
            'port': arg_space.port,
            'quiet': not app.debug,
            'debug': app.debug,
        }
    )
    webthread.start()

    # ===== add a cli (minimal) interface

    banner = []
    banner += ['OpenVisualizer']
    banner += ['web interface started at {0}:{1}'.format(arg_space.host, arg_space.port)]
    banner += ['enter \'quit\' to exit']
    banner = '\n'.join(banner)
    print banner

    arg_space = parser.parse_args()
    webapp.do_root(arg_space.root)

    webapp.cmdloop()
