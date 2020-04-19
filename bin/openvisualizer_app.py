# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

"""
Contains application model for OpenVisualizer. Expects to be called by top-level UI module.  See main() for startup use.
"""

import json
import logging
import logging.config
import os
import signal
import sys

import utils as u
from openvisualizer.eventbus import eventbusmonitor
from openvisualizer.jrc import jrc
from openvisualizer.motehandler.moteconnector import moteconnector
from openvisualizer.motehandler.moteprobe import moteprobe
from openvisualizer.motehandler.motestate import motestate
from openvisualizer.openlbr import openlbr
from openvisualizer.opentun.opentun import OpenTun
from openvisualizer.ovtracer import OVtracer
from openvisualizer.rpl import topology, rpl
from openvisualizer.simengine import simengine, motehandler

log = logging.getLogger('OpenVisualizerApp')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


class OpenVisualizerApp(object):
    """
    Provides an application model for OpenVisualizer. Provides common, top-level functionality for several UI clients.
    """

    def __init__(self, conf_dir, data_dir, log_dir, simulator_mode, num_motes, trace, debug, use_page_zero,
                 sim_topology, iotlab_motes, testbed_motes, path_topo, mqtt_broker_address, opentun):

        # store params
        self.conf_dir = conf_dir
        self.data_dir = data_dir
        self.log_dir = log_dir
        self.simulator_mode = simulator_mode
        self.num_motes = num_motes
        self.trace = trace
        self.debug = debug
        self.use_page_zero = use_page_zero
        self.iotlab_motes = iotlab_motes
        self.testbed_motes = testbed_motes
        self.path_topo = path_topo

        # local variables
        self.ebm = eventbusmonitor.EventBusMonitor()
        self.open_lbr = openlbr.OpenLbr(use_page_zero)
        self.rpl = rpl.RPL()
        self.jrc = jrc.JRC()
        self.topology = topology.Topology()
        self.dagroot_list = []
        self.mote_probes = []

        # create opentun call last since indicates prefix
        self.opentun = OpenTun.create(opentun)
        if self.simulator_mode:
            self.simengine = simengine.SimEngine(sim_topology)
            self.simengine.start()

        topo = None
        # import the number of motes from json file given by user (if the path_topo option is enabled)
        if self.path_topo and self.simulator_mode:
            try:
                topo_config = open(path_topo)
                topo = json.load(topo_config)
                self.num_motes = len(topo['motes'])
            except Exception as err:
                log.error(err)
                self.close()
                os.kill(os.getpid(), signal.SIGTERM)

        # create a moteprobe for each mote
        if self.simulator_mode:
            # in "simulator" mode, motes are emulated
            sys.path.append(os.path.join(self.data_dir, 'sim_files'))
            import oos_openwsn  # pylint: disable=import-error

            motehandler.read_notif_ids(os.path.join(self.data_dir, 'sim_files', 'openwsnmodule_obj.h'))
            self.mote_probes = []
            for _ in range(self.num_motes):
                mote_handler = motehandler.MoteHandler(oos_openwsn.OpenMote())
                self.simengine.indicateNewMote(mote_handler)
                self.mote_probes += [moteprobe.MoteProbe(mqtt_broker_address, emulated_mote=mote_handler)]
        elif self.iotlab_motes:
            # in "IoT-LAB" mode, motes are connected to TCP ports

            self.mote_probes = [
                moteprobe.MoteProbe(mqtt_broker_address, iotlab_mote=p) for p in self.iotlab_motes.split(',')
            ]
        elif self.testbed_motes:
            motes_finder = moteprobe.OpentestbedMoteFinder(mqtt_broker_address)
            self.mote_probes = [
                moteprobe.MoteProbe(mqtt_broker_address, testbedmote_eui64=p)
                for p in motes_finder.get_opentestbed_motelist()
            ]

        else:
            # in "hardware" mode, motes are connected to the serial port

            self.mote_probes = [
                moteprobe.MoteProbe(mqtt_broker_address, serial_port=p) for p in moteprobe.find_serial_ports()
            ]

        # create a MoteConnector for each MoteProbe
        self.mote_connectors = [moteconnector.MoteConnector(mp) for mp in self.mote_probes]

        # create a MoteState for each MoteConnector
        self.mote_states = [motestate.MoteState(mc) for mc in self.mote_connectors]

        # boot all emulated motes, if applicable
        if self.simulator_mode:
            self.simengine.pause()
            now = self.simengine.timeline.get_current_time()
            for rank in range(self.simengine.getNumMotes()):
                mote_handler = self.simengine.getMoteHandler(rank)
                self.simengine.timeline.schedule_event(
                    now,
                    mote_handler.get_id(),
                    mote_handler.hw_supply.switch_on,
                    mote_handler.hw_supply.INTR_SWITCHON
                )
            self.simengine.resume()

        # import the topology from the json file
        if self.path_topo and self.simulator_mode and 'motes' in topo:

            # delete each connections automatically established during motes creation
            connections_to_delete = self.simengine.propagation.retrieve_connections()
            for co in connections_to_delete:
                from_mote = int(co['fromMote'])
                to_mote = int(co['toMote'])
                self.simengine.propagation.delete_connection(from_mote, to_mote)

            motes = topo['motes']
            for mote in motes:
                mh = self.simengine.get_mote_handler_by_id(mote['id'])
                mh.set_location(mote['lat'], mote['lon'])

            # implements new connections
            connect = topo['connections']
            for co in connect:
                from_mote = int(co['fromMote'])
                to_mote = int(co['toMote'])
                pdr = float(co['pdr'])
                self.simengine.propagation.create_connection(from_mote, to_mote)
                self.simengine.propagation.update_connection(from_mote, to_mote, pdr)

            # store DAGroot moteids in DAGrootList
            dagroot_l = topo['DAGrootList']
            for DAGroot in dagroot_l:
                hex_dagroot = hex(DAGroot)
                hex_dagroot = hex_dagroot[2:]
                prefix_len = 4 - len(hex_dagroot)

                prefix = ""
                for i in range(prefix_len):
                    prefix += "0"
                mote_id = prefix + hex_dagroot
                self.dagroot_list.append(mote_id)

        # start tracing threads
        if self.trace:
            logging.config.fileConfig(
                os.path.join(self.conf_dir, 'trace.conf'), {'logDir': u.force_slash_sep(self.log_dir, self.debug)})
            OVtracer()

    # ======================== public ==========================================

    def close(self):
        """ Closes all thread-based components. """
        log.info('Closing OpenVisualizer')

        self.opentun.close()
        self.rpl.close()
        self.jrc.close()
        for probe in self.mote_probes:
            probe.close()

    def get_mote_state(self, mote_id):
        """
        Returns the MoteState object for the provided connected mote.
        :param mote_id: 16-bit ID of mote
        :rtype: MoteState or None if not found
        """

        for ms in self.mote_states:
            id_manager = ms.get_state_elem(ms.ST_IDMANAGER)
            if id_manager and id_manager.get_16b_addr():
                addr = ''.join(['%02x' % b for b in id_manager.get_16b_addr()])
                if addr == mote_id:
                    return ms
        else:
            return None

    def get_motes_connectivity(self):
        motes = []
        states = []
        edges = []
        src_s = None

        for ms in self.mote_states:
            id_manager = ms.get_state_elem(ms.ST_IDMANAGER)
            if id_manager and id_manager.get_16b_addr():
                src_s = ''.join(['%02X' % b for b in id_manager.get_16b_addr()])
                motes.append(src_s)
            neighbor_table = ms.get_state_elem(ms.ST_NEIGHBORS)
            for neighbor in neighbor_table.data:
                if len(neighbor.data) == 0:
                    break
                if neighbor.data[0]['used'] == 1 and neighbor.data[0]['parentPreference'] == 1:
                    dst_s = ''.join(['%02X' % b for b in neighbor.data[0]['addr'].addr[-2:]])
                    edges.append({'u': src_s, 'v': dst_s})
                    break

        motes = list(set(motes))
        for mote in motes:
            d = {'id': mote, 'value': {'label': mote}}
            states.append(d)
        return states, edges

    def get_mote_dict(self):
        """ Returns a dictionary with key-value entry: (mote_id: serialport) """
        mote_dict = {}
        for ms in self.mote_states:
            addr = ms.get_state_elem(motestate.MoteState.ST_IDMANAGER).get_16b_addr()
            if addr:
                mote_dict[''.join(['%02x' % b for b in addr])] = ms.mote_connector.serialport
            else:
                mote_dict[ms.mote_connector.serialport] = None
        return mote_dict


# ============================ main ============================================

def main(parser, conf_dir, data_dir, log_dir, sim_motes):
    """
    Entry point for application startup by UI. Parses common arguments.

    :param parser: Optional ArgumentParser passed in from enclosing UI module to allow that module to pre-parse
    specific arguments
    :param conf_dir: directory holding configuration files
    :param data_dir: directory containing additional data files
    :param log_dir: directory which will hold the logs written by OpenVisualizer
    :param sim_motes: the number of simulated motes

    :rtype: OpenVisualizerApp object
    """

    args = parser.parse_args()

    if args.path_topo:
        args.simulator_mode = True
        args.num_motes = 0
        args.sim_topology = "fully-meshed"
        # --path_topo
    elif args.num_motes > 0:
        # --simCount implies --sim
        args.simulator_mode = True
    elif args.simulator_mode:
        # default count when --simCount not provided
        args.num_motes = sim_motes

    if args.sim_topology:
        topo = args.sim_topology
    else:
        topo = 'Pister-hack model'

    log.info('Initializing OpenVisualizerApp with options:\n\t- {0}'.format(
        '\n\t- '.join(['appdir          = {0}'.format(args.appdir),
                      'sim             = {0}'.format(args.simulator_mode),
                      'simCount        = {0}'.format(args.num_motes),
                      'simTopology     = {0}'.format(topo),
                      'trace           = {0}'.format(args.trace),
                      'debug           = {0}'.format(args.debug),
                      'mqtt-broker     = {0}'.format(args.mqtt_broker),
                      'testbed_motes   = {0}'.format(args.testbed_motes),
                      'use_page_zero   = {0}'.format(args.use_page_zero)],
                     )))

    log.debug('sys.path:\n\t{0}'.format('\n\t'.join(str(p) for p in sys.path)))

    return OpenVisualizerApp(
        conf_dir=conf_dir,
        data_dir=data_dir,
        log_dir=log_dir,
        simulator_mode=args.simulator_mode,
        num_motes=args.num_motes,
        trace=args.trace,
        debug=args.debug,
        use_page_zero=args.use_page_zero,
        sim_topology=args.sim_topology,
        iotlab_motes=args.iotlab_motes,
        testbed_motes=args.testbed_motes,
        path_topo=args.path_topo,
        mqtt_broker_address=args.mqtt_broker,
        opentun=args.opentun
    )
