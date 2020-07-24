# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

"""
Contains application model for OpenVisualizer. Expects to be called by top-level UI module.  See main() for startup use.
"""
import json
import logging.config
import os
import platform
import shutil
import signal
import sys
import tempfile
import time
from ConfigParser import SafeConfigParser
from SimpleXMLRPCServer import SimpleXMLRPCServer
from argparse import ArgumentParser
from xmlrpclib import Fault

import appdirs
import coloredlogs
import pkg_resources
import verboselogs
from iotlabcli.parser import common

from openvisualizer import PACKAGE_NAME, WINDOWS_COLORS, UNIX_COLORS, DEFAULT_LOGGING_CONF, APPNAME
from openvisualizer.eventbus import eventbusmonitor
from openvisualizer.eventbus.eventbusclient import EventBusClient
from openvisualizer.jrc import jrc
from openvisualizer.motehandler.moteconnector import moteconnector
from openvisualizer.motehandler.moteprobe import emulatedmoteprobe
from openvisualizer.motehandler.moteprobe import testbedmoteprobe
from openvisualizer.motehandler.moteprobe.iotlabmoteprobe import IotlabMoteProbe
from openvisualizer.motehandler.moteprobe.serialmoteprobe import SerialMoteProbe
from openvisualizer.motehandler.motestate import motestate
from openvisualizer.motehandler.motestate.motestate import MoteState
from openvisualizer.openlbr import openlbr
from openvisualizer.opentun.opentun import OpenTun
from openvisualizer.opentun.opentunnull import OpenTunNull
from openvisualizer.rpl import topology, rpl
from openvisualizer.simengine import simengine, motehandler
from openvisualizer.utils import extract_component_codes, extract_log_descriptions, extract_6top_rcs, \
    extract_6top_states

verboselogs.install()

log = logging.getLogger('OpenVisualizerServer')
coloredlogs.install(level='WARNING', logger=log, fmt='%(asctime)s [%(name)s:%(levelname)s] %(message)s',
                    datefmt='%H:%M:%S')


class ColoredFormatter(coloredlogs.ColoredFormatter):
    """ Class that matches coloredlogs.ColoredFormatter arguments with logging.Formatter """

    def __init__(self, fmt=None, datefmt=None):
        self.parser = SafeConfigParser()

        if sys.platform.startswith('win32'):
            log_colors_conf = pkg_resources.resource_filename(PACKAGE_NAME, WINDOWS_COLORS)
        else:
            log_colors_conf = pkg_resources.resource_filename(PACKAGE_NAME, UNIX_COLORS)

        self.parser.read(log_colors_conf)

        ls = self.parse_section('levels', 'keys')
        fs = self.parse_section('fields', 'keys')

        coloredlogs.ColoredFormatter.__init__(self, fmt=fmt, datefmt=datefmt, level_styles=ls, field_styles=fs)

    def parse_section(self, section, option):
        dictionary = {}

        if not self.parser.has_section(section) or not self.parser.has_option(section, option):
            log.warning('Unknown section {} or option {}'.format(section, option))
            return dictionary

        subsections = map(str.strip, self.parser.get(section, option).split(','))

        for subsection in subsections:
            if not self.parser.has_section(str(subsection)):
                log.warning('Unknown section name: {}'.format(subsection))
                continue

            dictionary[subsection] = {}
            options = self.parser.options(subsection)

            for opt in options:
                res = self.parse_options(subsection, opt.strip().lower())
                if res is not None:
                    dictionary[subsection][opt] = res

        return dictionary

    def parse_options(self, section, option):
        res = None
        if option == 'bold' or option == 'faint':
            try:
                return self.parser.getboolean(section, option)
            except ValueError:
                log.error('Illegal value: {} for option: {}'.format(self.parser.get(section, option), option))
        elif option == 'color':
            try:
                res = self.parser.getint(section, option)
            except ValueError:
                res = self.parser.get(section, option)
        else:
            log.warning('Unknown option name: {}'.format(option))

        return res


class OpenVisualizerServer(SimpleXMLRPCServer, EventBusClient):
    """
    Class implements and RPC server that allows monitoring and (remote) management of a mesh network.
    """

    def __init__(self, host, port, simulator_mode, debug, vcdlog,
                 use_page_zero, sim_topology, testbed_motes, mqtt_broker,
                 opentun, fw_path, auto_boot, root, port_mask, baudrate,
                 topo_file, iotlab_motes, iotlab_passwd, iotlab_user):

        # store params
        self.host = host

        try:
            self.port = int(port)
            self.simulator_mode = int(simulator_mode)
        except ValueError as err:
            log.error(err)

        if self.simulator_mode == 0 and sim_topology is not None:
            log.warning("Simulation topology specified but no --sim=<x> given, switching to hardware mode")

        self.sim_topology = sim_topology

        self.debug = debug
        if self.debug and not opentun:
            log.warning("Wireshark debugging requires opentun")

        self.use_page_zero = use_page_zero
        self.vcdlog = vcdlog

        if fw_path is not None:
            self.fw_path = os.path.expanduser(fw_path)
        else:
            self.fw_path = fw_path

        self.root = root
        self.dagroot = None
        self.auto_boot = auto_boot

        if topo_file is not None:
            self.topo_file = os.path.expanduser(topo_file)
        else:
            self.topo_file = topo_file

        # if a topology file is specified, overwrite the simulation and topology options
        if self.topo_file:
            self.load_motes_from_topology_file()

        if self.fw_path is None:
            try:
                self.fw_path = os.environ['OPENWSN_FW_BASE']
            except KeyError:
                log.critical("Neither OPENWSN_FW_BASE or '--fw-path' was specified.")
                os.kill(os.getpid(), signal.SIGTERM)

        # local variables
        self.ebm = eventbusmonitor.EventBusMonitor()
        self.openlbr = openlbr.OpenLbr(use_page_zero)
        self.rpl = rpl.RPL()
        self.jrc = jrc.JRC()
        self.topology = topology.Topology()
        self.mote_probes = []

        # create opentun call last since indicates prefix
        self.opentun = OpenTun.create(opentun)

        if self.debug and opentun:
            self.ebm.wireshark_debug_enabled = True
        else:
            self.ebm.wireshark_debug_enabled = False

        if self.simulator_mode:
            self.simengine = simengine.SimEngine(self.sim_topology)
            self.simengine.start()

            self.temp_dir = self.copy_sim_fw()

            if self.temp_dir is None:
                log.critical("failed to import simulation files! Exiting now!")
                os.kill(os.getpid(), signal.SIGTERM)

            sys.path.append(os.path.join(self.temp_dir))
            motehandler.read_notif_ids(os.path.join(self.temp_dir, 'openwsnmodule_obj.h'))

            import oos_openwsn  # pylint: disable=import-error

            self.mote_probes = []
            for _ in range(self.simulator_mode):
                mote_handler = motehandler.MoteHandler(oos_openwsn.OpenMote(), self.vcdlog)
                self.simengine.indicate_new_mote(mote_handler)
                self.mote_probes += [emulatedmoteprobe.EmulatedMoteProbe(emulated_mote=mote_handler)]

            # load the saved topology from the topology file
            if self.topo_file:
                self.load_topology()
        elif iotlab_motes:
            # in "IoT-LAB" mode, motes are connected to TCP ports
            self.mote_probes = IotlabMoteProbe.probe_iotlab_motes(
                iotlab_motes=iotlab_motes,
                iotlab_user=iotlab_user,
                iotlab_passwd=iotlab_passwd,
            )
        elif testbed_motes:
            motes_finder = testbedmoteprobe.OpentestbedMoteFinder(mqtt_broker)
            mote_list = motes_finder.get_opentestbed_motelist()
            for p in mote_list:
                self.mote_probes.append(testbedmoteprobe.OpentestbedMoteProbe(mqtt_broker, testbedmote_eui64=p))
        else:
            # in "hardware" mode, motes are connected to the serial port
            self.mote_probes = SerialMoteProbe.probe_serial_ports(port_mask=port_mask, baudrate=baudrate)

        # create a MoteConnector for each MoteProbe
        try:
            fw_defines = self.extract_stack_defines()
        except IOError as err:
            log.critical("could not updated firmware definitions: {}".format(err))
            os.kill(os.getpid(), signal.SIGTERM)
            return

        self.mote_connectors = [moteconnector.MoteConnector(mp, fw_defines, mqtt_broker) for mp in self.mote_probes]

        # create a MoteState for each MoteConnector
        self.mote_states = [motestate.MoteState(mc) for mc in self.mote_connectors]

        # set up EventBusClient
        EventBusClient.__init__(self, name='OpenVisualizerServer', registrations=[])

        # set up RPC server
        try:
            SimpleXMLRPCServer.__init__(self, (self.host, self.port), allow_none=True, logRequests=False)

            self.register_introspection_functions()

            # register RPCs
            self.register_function(self.shutdown)
            self.register_function(self.get_mote_dict)
            self.register_function(self.boot_motes)
            self.register_function(self.set_root)
            self.register_function(self.get_mote_state)
            self.register_function(self.get_dagroot)
            self.register_function(self.get_dag)
            self.register_function(self.get_motes_connectivity)
            self.register_function(self.get_wireshark_debug)
            self.register_function(self.enable_wireshark_debug)
            self.register_function(self.disable_wireshark_debug)
            self.register_function(self.get_ebm_stats)
            self.register_function(self.get_network_topology)
            self.register_function(self.update_network_topology)
            self.register_function(self.create_motes_connection)
            self.register_function(self.update_motes_connection)
            self.register_function(self.delete_motes_connection)
            self.register_function(self.retrieve_routing_path)

            # boot all simulated motes
            if self.simulator_mode and self.auto_boot:
                self.boot_motes(['all'])

            # set a mote (hardware or emulated) as DAG root of the network
            if self.root is not None:
                if self.simulator_mode and self.auto_boot is False:
                    log.warning("Cannot set root when motes are not booted! ")
                else:
                    log.info("Setting DAG root...")
                    # make sure that the simulated motes are booted and the hardware motes have communicated
                    # their mote ID
                    time.sleep(1.5)
                    self.set_root(self.root)
        except Exception as e:
            log.critical(e)
            self.shutdown()
            return

    @staticmethod
    def cleanup_temporary_files(files):
        """ Clean up temporary simulation files """
        for f in files:
            log.verbose("cleaning up files: {}".format(f))
            shutil.rmtree(f, ignore_errors=True)

    def load_motes_from_topology_file(self):
        """ Import the number of motes from the topology file. """
        topo_config = self._load_saved_topology()
        if topo_config is None:
            return

        # set/override the amount of simulated motes and set temporary topology to fully-meshed (otherwise
        # connections might be deleted due to pdr == 0 in Pister-hack model)
        self.simulator_mode = len(topo_config['motes'])
        self.sim_topology = 'fully-meshed'

    def load_topology(self):
        """ Import the network topology from a json file. """
        if not self.simulator_mode:
            log.error("Only supported in simulator mode")
            return

        log.success("loading topology from file.")

        topo_config = self._load_saved_topology()
        if topo_config is None:
            return

        # delete each connections automatically established during motes creation
        connections_to_delete = self.simengine.propagation.retrieve_connections()
        for co in connections_to_delete:
            from_mote = int(co['fromMote'])
            to_mote = int(co['toMote'])
            self.simengine.propagation.delete_connection(from_mote, to_mote)

        motes = topo_config['motes']
        for mote in motes:
            mh = self.simengine.get_mote_handler_by_id(mote['id'])
            mh.set_location(mote['lat'], mote['lon'])

        # implements new connections
        connect = topo_config['connections']
        for co in connect:
            from_mote = int(co['fromMote'])
            to_mote = int(co['toMote'])
            pdr = float(co['pdr'])
            self.simengine.propagation.create_connection(from_mote, to_mote)
            self.simengine.propagation.update_connection(from_mote, to_mote, pdr)

        try:
            # recover dagroot
            self.root = topo_config['DAGroot']
        except KeyError:
            pass

    def _load_saved_topology(self):
        """ Check if we can find the file locally, if not search the example directory. """

        local_path = '/'.join(('topologies', str(self.topo_file)))

        try:
            if os.path.isfile(self.topo_file):
                filename = self.topo_file
                f = open(filename, 'r')
            elif pkg_resources.resource_exists(PACKAGE_NAME, local_path):
                f = pkg_resources.resource_stream(PACKAGE_NAME, local_path)
            else:
                log.error('could not open file: {}'.format(self.topo_file))
                return

            topo_config = json.load(f)
            f.close()
        except (IOError, ValueError) as err:
            log.error('failed to load topology from file: {}'.format(err))
            return

        return topo_config

    def copy_sim_fw(self):
        """
        Copy simulation files from build folder in openwsn-fw to a temporary directory.
        The latter is subsequently added to the python path.
        """

        hosts = ['amd64-linux', 'x86-linux', 'amd64-windows', 'x86-windows']
        if os.name == 'nt':
            index = 2 if platform.architecture()[0] == '64bit' else 3
        else:
            index = 0 if platform.architecture()[0] == '64bit' else 1

        host = hosts[index]

        # in openwsn-fw, directory containing 'openwsnmodule_obj.h'
        inc_dir = os.path.join(self.fw_path, 'bsp', 'boards', 'python')
        if not os.path.exists(inc_dir):
            log.critical("path '{}' does not exist".format(inc_dir))
            return

        # in openwsn-fw, directory containing extension library
        lib_dir = os.path.join(self.fw_path, 'build', 'python_gcc', 'projects', 'common')
        if not os.path.exists(lib_dir):
            log.critical("path '{}' does not exist".format(lib_dir))
            return

        temp_dir = tempfile.mkdtemp()

        # Build source and destination pathnames.
        arch_and_os = host.split('-')
        lib_ext = 'pyd' if arch_and_os[1] == 'windows' else 'so'
        source_name = 'oos_openwsn.{0}'.format(lib_ext)
        dest_name = 'oos_openwsn-{0}.{1}'.format(arch_and_os[0], lib_ext)
        dest_dir = os.path.join(temp_dir, arch_and_os[1])

        try:
            shutil.copy(os.path.join(inc_dir, 'openwsnmodule_obj.h'), temp_dir)
        except IOError:
            log.critical("could not find {} file".format('openwsnmodule_obj.h'))
            return

        log.verbose(
            "copying '{}' to temporary dir '{}'".format(os.path.join(inc_dir, 'openwsnmodule_obj.h'), temp_dir))

        try:
            os.makedirs(os.path.join(dest_dir))
        except OSError:
            pass

        try:
            shutil.copy(os.path.join(lib_dir, source_name), os.path.join(dest_dir, dest_name))
        except IOError:
            log.critical("Could not find: {}".format(str(os.path.join(lib_dir, source_name))))
            return

        log.verbose(
            "copying '{}' to '{}'".format(os.path.join(lib_dir, source_name), os.path.join(dest_dir, dest_name)))

        # Copy the module directly to sim_files directory if it matches this host.
        if arch_and_os[0] == 'amd64':
            arch_match = platform.architecture()[0] == '64bit'
        else:
            arch_match = platform.architecture()[0] == '32bit'
        if arch_and_os[1] == 'windows':
            os_match = os.name == 'nt'
        else:
            os_match = os.name == 'posix'

        if arch_match and os_match:
            try:
                shutil.copy(os.path.join(lib_dir, source_name), temp_dir)
            except IOError:
                log.critical("could not find {}".format(str(os.path.join(lib_dir, source_name))))
                return

        return temp_dir

    def extract_stack_defines(self):
        """ Extract firmware definitions for the OpenVisualizer parser from the OpenWSN-FW files. """
        log.info('extracting firmware definitions.')
        definitions = {
            "components": extract_component_codes(os.path.join(self.fw_path, 'inc', 'opendefs.h')),
            "log_descriptions": extract_log_descriptions(os.path.join(self.fw_path, 'inc', 'opendefs.h')),
            "sixtop_returncodes": extract_6top_rcs(os.path.join(self.fw_path, 'openstack', '02b-MAChigh', 'sixtop.h')),
            "sixtop_states": extract_6top_states(os.path.join(self.fw_path, 'openstack', '02b-MAChigh', 'sixtop.h')),
        }

        return definitions

    # ======================== RPC functions ================================

    def shutdown(self):
        """ Closes all thread-based components. """
        log.debug('RPC: {}'.format(self.shutdown.__name__))

        self.opentun.close()
        self.rpl.close()
        self.jrc.close()
        for probe in self.mote_probes:
            probe.close()
            if probe.daemon is False:
                probe.join()

        if self.simulator_mode:
            OpenVisualizerServer.cleanup_temporary_files([self.temp_dir])

        os.kill(os.getpid(), signal.SIGTERM)

    def get_dag(self):
        return self.topology.get_dag()

    def boot_motes(self, addresses):
        # boot all emulated motes, if applicable
        log.debug('RPC: {}'.format(self.boot_motes.__name__))

        if self.simulator_mode:
            self.simengine.pause()
            now = self.simengine.timeline.get_current_time()
            if len(addresses) == 1 and addresses[0] == "all":
                for rank in range(self.simengine.get_num_motes()):
                    mh = self.simengine.get_mote_handler(rank)
                    if not mh.hw_supply.mote_on:
                        self.simengine.timeline.schedule_event(now, mh.get_id(), mh.hw_supply.switch_on,
                                                               mh.hw_supply.INTR_SWITCHON)
                    else:
                        raise Fault(faultCode=-1, faultString="Mote already booted.")
            else:
                for address in addresses:
                    try:
                        address = int(address)
                    except ValueError:
                        raise Fault(faultCode=-1, faultString="Invalid mote address: {}".format(address))

                    for rank in range(self.simengine.get_num_motes()):
                        mh = self.simengine.get_mote_handler(rank)
                        if address == mh.get_id():
                            if not mh.hw_supply.mote_on:
                                self.simengine.timeline.schedule_event(now, mh.get_id(), mh.hw_supply.switch_on,
                                                                       mh.hw_supply.INTR_SWITCHON)
                            else:
                                raise Fault(faultCode=-1, faultString="Mote already booted.")

            self.simengine.resume()
            return True
        else:
            raise Fault(faultCode=-1, faultString="Method not supported on real hardware")

    def set_root(self, port_or_address):
        log.debug('RPC: {}'.format(self.set_root.__name__))

        mote_dict = self.get_mote_dict()
        if port_or_address in mote_dict:
            port = mote_dict[port_or_address]
        elif port_or_address in mote_dict.values():
            port = port_or_address
        else:
            raise Fault(faultCode=-1, faultString="Unknown port or address: {}".format(port_or_address))

        for ms in self.mote_states:
            try:
                if ms.mote_connector.serialport == port:
                    ms.trigger_action(MoteState.TRIGGER_DAGROOT)
                    self.dagroot = ms.get_state_elem(ms.ST_IDMANAGER).get_16b_addr()
                    log.success('Setting mote {} as root'.format(''.join(['%02x' % b for b in self.dagroot])))
                    return True
            except ValueError as err:
                log.error(err)
                break
        raise Fault(faultCode=-1, faultString="Could not set {} as root".format(port))

    def get_dagroot(self):
        log.debug('RPC: {}'.format(self.get_dagroot.__name__))
        return self.dagroot

    def get_mote_state(self, mote_id):
        """
        Returns the MoteState object for the provided connected mote.
        :param mote_id: 16-bit ID of mote
        :rtype: MoteState or None if not found
        """
        log.debug('RPC: {}'.format(self.get_mote_state.__name__))

        for ms in self.mote_states:
            id_manager = ms.get_state_elem(ms.ST_IDMANAGER)
            if id_manager and id_manager.get_16b_addr():
                addr = ''.join(['%02x' % b for b in id_manager.get_16b_addr()])
                if addr == mote_id:
                    return OpenVisualizerServer._extract_mote_states(ms)
        else:
            error_msg = "Unknown mote ID: {}".format(mote_id)
            log.warning("returning fault: {}".format(error_msg))
            raise Fault(faultCode=-1, faultString=error_msg)

    def enable_wireshark_debug(self):
        if isinstance(self.opentun, OpenTunNull):
            raise Fault(faultCode=-1, faultString="Wireshark debugging requires opentun to be active on the server")
        else:
            self.ebm.wireshark_debug_enabled = True

    def disable_wireshark_debug(self):
        if isinstance(self.opentun, OpenTunNull):
            raise Fault(faultCode=-1, faultString="Wireshark debugging requires opentun to be active on the server")
        else:
            self.ebm.wireshark_debug_enabled = False

    def get_wireshark_debug(self):
        return self.ebm.wireshark_debug_enabled

    def get_ebm_stats(self):
        return self.ebm.get_stats()

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

    def update_network_topology(self, connections):
        connections = json.loads(connections)

        if not self.simulator_mode:
            return False

        for (_, v) in connections.items():
            mh = self.simengine.get_mote_handler_by_id(v['id'])
            mh.set_location(v['lat'], v['lon'])

        return True

    def get_network_topology(self):
        motes = []
        rank = 0

        if not self.simulator_mode:
            return {}

        while True:
            try:
                mh = self.simengine.get_mote_handler(rank)
                mote_id = mh.get_id()
                (lat, lon) = mh.get_location()
                motes += [{'id': mote_id, 'lat': lat, 'lon': lon}]
                rank += 1
            except IndexError:
                break

        # connections
        connections = self.simengine.propagation.retrieve_connections()

        data = {'motes': motes, 'connections': connections}
        return data

    def create_motes_connection(self, from_mote, to_mote):
        if not self.simulator_mode:
            return False

        self.simengine.propagation.create_connection(from_mote, to_mote)
        return True

    def update_motes_connection(self, from_mote, to_mote, pdr):
        if not self.simulator_mode:
            return False

        self.simengine.propagation.update_connection(from_mote, to_mote, pdr)
        return True

    def delete_motes_connection(self, from_mote, to_mote):
        if not self.simulator_mode:
            return False

        self.simengine.propagation.delete_connection(from_mote, to_mote)
        return True

    def retrieve_routing_path(self, destination):
        route = self._dispatch_and_get_result(signal='getSourceRoute', data=destination)
        route = [r[-1] for r in route]
        data = {'route': route}

        return data

    def get_mote_dict(self):
        """ Returns a dictionary with key-value entry: (mote_id: serialport) """
        log.debug('RPC: {}'.format(self.get_mote_dict.__name__))

        mote_dict = {}

        for ms in self.mote_states:
            addr = ms.get_state_elem(motestate.MoteState.ST_IDMANAGER).get_16b_addr()
            if addr:
                mote_dict[''.join(['%02x' % b for b in addr])] = ms.mote_connector.serialport
            else:
                mote_dict[ms.mote_connector.serialport] = None

        return mote_dict

    @staticmethod
    def _extract_mote_states(ms):
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
            ms.ST_MSF: ms.get_state_elem(ms.ST_MSF).to_json('data'),
        }
        return states


def _add_iotlab_parser_args(parser):
    """ Adds arguments specific to IotLab Support """
    description = """
    Commands for motes running on IotLab (iot-lab_A8-M3 excluded).
    For large experiments run directly on the ssh frontend to not open multiple
    connections.
    When not already authenticated (use iotlab-auth) and iotlab account
    USERNAME and PASSWORD must be provided.
    """
    iotlab_parser = parser.add_argument_group('iotlab', description)
    iotlab_parser.add_argument(
        '--iotlab-motes',
        default='',
        type=str,
        nargs='+',
        help='comma-separated list of IoT-LAB motes (e.g. "wsn430-9,wsn430-34,wsn430-3")',
    )
    common.add_auth_arguments(iotlab_parser, False)


def _add_parser_args(parser):
    """ Adds arguments specific to the OpenVisualizer application """
    parser.add_argument(
        '-s', '--sim',
        dest='simulator_mode',
        default=0,
        type=int,
        help='Run a simulation with the given amount of emulated motes.',
    )

    parser.add_argument(
        '--fw-path',
        dest='fw_path',
        type=str,
        help='Provide the path to the OpenWSN firmware. This option overrides the optional OPENWSN_FW_BASE environment '
             'variable.',
    )

    parser.add_argument(
        '-o', '--simtopo',
        dest='sim_topology',
        action='store',
        help='Force a predefined topology (linear or fully-meshed). Only available in simulation mode.',
    )

    parser.add_argument(
        '--root',
        dest='set_root',
        action='store',
        type=str,
        help='Set a simulated or hardware mote as root, specify the mote\'s port or address.',
    )

    parser.add_argument(
        '-d', '--wireshark-debug',
        dest='debug',
        default=False,
        action='store_true',
        help='Enables debugging with wireshark (requires opentun).',
    )

    parser.add_argument(
        '-l', '--lconf',
        dest='lconf',
        action='store',
        help='Provide a logging configuration.',
    )

    parser.add_argument(
        '--vcdlog',
        dest='vcdlog',
        default=False,
        action='store_true',
        help='Use VCD logger.',
    )

    parser.add_argument(
        '-z', '--pagezero',
        dest='use_page_zero',
        default=False,
        action='store_true',
        help='Use page number 0 in page dispatch (only works with one-hop).',
    )

    parser.add_argument(
        '-b', '--opentestbed',
        dest='testbed_motes',
        default=False,
        action='store_true',
        help='Connect to motes from opentestbed over the MQTT server (see option \'--mqtt-broker\')',
    )

    parser.add_argument(
        '--mqtt-broker',
        dest='mqtt_broker',
        default='argus.paris.inria.fr',
        action='store',
        help='MQTT broker address to use',
    )

    parser.add_argument(
        '--opentun',
        dest='opentun',
        default=False,
        action='store_true',
        help='Use a TUN device to route packets to the Internet.',
    )

    parser.add_argument(
        '-H',
        '--host',
        dest='host',
        default='localhost',
        action='store',
        help='Host address for the RPC address.',
    )

    parser.add_argument(
        '-P',
        '--port',
        dest='port',
        type=int,
        default=9000,
        action='store',
        help='Port number for the RPC server.',
    )

    parser.add_argument(
        '--port-mask',
        dest='port_mask',
        type=str,
        action='store',
        nargs='+',
        help='Port mask for serial port detection, e.g, /dev/tty/USB*.',
    )

    parser.add_argument(
        '--baudrate',
        dest='baudrate',
        default=[115200],
        action='store',
        nargs='+',
        help='List of baudrates to probe for, e.g 115200 500000.',
    )

    parser.add_argument(
        '--no-boot',
        dest='auto_boot',
        default=True,
        action='store_false',
        help='Disables automatic boot of emulated motes.',
    )

    parser.add_argument(
        '--load-topology',
        dest='topo_file',
        type=str,
        action='store',
        help='Provide a topology for the simulation, when in use this option will override all the other '
             'simulation options.',
    )


# ============================ main ============================================

def main():
    """ Entry point for the OpenVisualizer server. """

    banner = [""]
    banner += [" ___                 _ _ _  ___  _ _ "]
    banner += ["| . | ___  ___ ._ _ | | | |/ __>| \\ |"]
    banner += ["| | || . \\/ ._>| ' || | | |\\__ \\|   |"]
    banner += ["`___'|  _/\\___.|_|_||__/_/ <___/|_\\_|"]
    banner += ["     |_|                  openwsn.org"]
    banner += [""]

    print '\n'.join(banner)

    parser = ArgumentParser()
    _add_parser_args(parser)
    _add_iotlab_parser_args(parser)
    args = parser.parse_args()

    # create directories to store logs and application data
    try:
        os.makedirs(appdirs.user_log_dir(APPNAME))
    except OSError as err:
        if err.errno != 17:
            log.critical(err)
            return

    try:
        os.makedirs(appdirs.user_data_dir(APPNAME))
    except OSError as err:
        if err.errno != 17:
            log.critical(err)
            return

    # loading the logging configuration
    if not args.lconf and pkg_resources.resource_exists(PACKAGE_NAME, DEFAULT_LOGGING_CONF):
        try:
            logging.config.fileConfig(pkg_resources.resource_stream(PACKAGE_NAME, DEFAULT_LOGGING_CONF),
                                      {'log_dir': appdirs.user_log_dir(APPNAME)})
        except IOError as err:
            log.critical("permission error: {}".format(err))
            return
        log.verbose("loading logging configuration: {}".format(DEFAULT_LOGGING_CONF))
    elif args.lconf:
        logging.config.fileConfig(args.lconf)
        log.verbose("loading logging configuration: {}".format(args.lconf))
    else:
        log.error("could not load logging configuration.")

    options = ['log files directory     = {0}'.format(appdirs.user_log_dir(APPNAME)),
               'data files directory    = {0}'.format(appdirs.user_data_dir(APPNAME)),
               'host address server     = {0}'.format(args.host),
               'port number server      = {0}'.format(args.port)]

    if args.fw_path:
        options.append('firmware path           = {0}'.format(args.fw_path))
    else:
        try:
            options.append('firmware path           = {0}'.format(os.environ['OPENWSN_FW_BASE']))
        except KeyError:
            log.warning(
                "unknown openwsn-fw location, specify with option '--fw-path' or by exporting the OPENWSN_FW_BASE "
                "environment variable.")

    if args.simulator_mode:
        options.append('simulation              = {0}'.format(args.simulator_mode))
        if args.sim_topology:
            options.append('simulation topology     = {0}'.format(args.sim_topology))
        else:
            options.append('simulation topology     = {0}'.format('Pister-hack'))

        options.append('auto-boot sim motes     = {0}'.format(args.auto_boot))

    if args.set_root:
        options.append('set root                = {0}'.format(args.set_root))

    if args.opentun:
        options.append('opentun                 = {0}'.format('True'))
        if args.debug:
            options.append('wireshark debug         = {0}'.format(True))

    options.append('use page zero           = {0}'.format(args.use_page_zero))
    options.append('use VCD logger          = {0}'.format(args.vcdlog))

    if not args.simulator_mode and args.port_mask:
        options.append('serial port mask        = {0}'.format(args.port_mask))
    if not args.simulator_mode and args.baudrate:
        options.append('baudrates to probe      = {0}'.format(args.baudrate))

    if args.testbed_motes:
        options.append('opentestbed             = {0}'.format(args.testbed_motes))
        options.append('mqtt broker             = {0}'.format(args.mqtt_broker))

    if args.topo_file:
        options.append('load topology from file = {0}'.format(args.topo_file))

    if args.topo_file and (args.simulator_mode or args.sim_topology or args.set_root):
        log.warning("simulation options or root option might be overwritten by the configuration in '{}'".format(
            args.topo_file))

    log.info('initializing OV Server with options:\n\t- {0}'.format('\n\t- '.join(options)))

    log.debug('sys.path:\n\t{0}'.format('\n\t'.join(str(p) for p in sys.path)))

    server = OpenVisualizerServer(
        host=args.host,
        port=args.port,
        simulator_mode=args.simulator_mode,
        debug=args.debug,
        use_page_zero=args.use_page_zero,
        vcdlog=args.vcdlog,
        sim_topology=args.sim_topology,
        port_mask=args.port_mask,
        baudrate=args.baudrate,
        testbed_motes=args.testbed_motes,
        mqtt_broker=args.mqtt_broker,
        opentun=args.opentun,
        fw_path=args.fw_path,
        auto_boot=args.auto_boot,
        root=args.set_root,
        topo_file=args.topo_file,
        iotlab_motes=args.iotlab_motes,
        iotlab_user=args.username,
        iotlab_passwd=args.password,
    )

    try:
        log.info("starting RPC server")
        server.serve_forever()
    except KeyboardInterrupt:
        pass

    server.shutdown()
