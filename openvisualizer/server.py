# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

"""
Contains application model for OpenVisualizer. Expects to be called by top-level UI module.  See main() for startup use.
"""

import logging.config
import os
import signal
from enum import IntEnum
from threading import Timer
from typing import Optional, Dict, Tuple, Any
from xmlrpc.client import Fault

from openvisualizer.eventbus import eventbusmonitor
from openvisualizer.eventbus.eventbusclient import EventBusClient
from openvisualizer.motehandler.moteconnector.moteconnector import MoteConnector
from openvisualizer.motehandler.moteprobe.emulatedmoteprobe import EmulatedMoteProbe
from openvisualizer.motehandler.moteprobe.serialmoteprobe import SerialMoteProbe
from openvisualizer.motehandler.motestate import motestate
from openvisualizer.motehandler.motestate.motestate import MoteState
from openvisualizer.openlbr import openlbr
from openvisualizer.opentun.opentun import OpenTun
from openvisualizer.opentun.opentunnull import OpenTunNull
from openvisualizer.rpl import rpl, topology
from openvisualizer.simulator.simengine import SimEngine
from openvisualizer.utils import extract_component_codes, extract_log_descriptions, extract_6top_rcs, \
    extract_6top_states

log = logging.getLogger('OpenVisualizer')


class OpenVisualizer(EventBusClient):
    """ Class implements an RPC server that allows (remote) monitoring and interaction a mesh network. """

    class Mode(IntEnum):
        HARDWARE = 0
        SIMULATION = 1
        IOTLAB = 2
        TESTBED = 3

    def __init__(self, config, mode, **kwargs):

        super().__init__(name='OpenVisualizer')

        log.info("Starting OpenVisualizer ... ")

        self.mode = mode

        if self.mode == self.Mode.HARDWARE:
            self.baudrate = kwargs.get('baudrate')
            self.port_mask = kwargs.get('port_mask')
            self.mote_probes = SerialMoteProbe.probe_serial_ports(port_mask=self.port_mask, baudrate=self.baudrate)
        elif self.mode == self.Mode.SIMULATION:
            self.num_of_motes = kwargs.get("num_of_motes")
            self.simulator = SimEngine(self.num_of_motes)
            self.mote_probes = [EmulatedMoteProbe(m_if) for m_if in self.simulator.mote_interfaces]
            self.simulator.start()
        elif self.mode == self.Mode.IOTLAB:
            pass
        elif self.mode == self.Mode.TESTBED:
            pass
        else:
            log.critical("Unknown OpenVisualizer mode")
            raise KeyboardInterrupt()

        # store configuration
        self.root = config.root
        self.fw_path = config.fw_path
        self.page_zero = config.page_zero

        self.ebm = eventbusmonitor.EventBusMonitor(kwargs.get("wireshark_debug"))
        self.lbr = openlbr.OpenLbr(self.page_zero)
        self.rpl = rpl.RPL()
        self.topology = topology.Topology()
        self.tun = OpenTun.create(config.tun)

        try:
            defines = self.extract_stack_defines()
        except FileNotFoundError:
            log.critical("Could not load stack definitions")
            self.shutdown()
            return

        self.mote_connectors = [MoteConnector(mp, defines, config.mqtt_broker) for mp in self.mote_probes]
        self.mote_states = [MoteState(mc) for mc in self.mote_connectors]

        self._dagroot = None

        if self.root:
            log.info(f"Setting DAGroot: {self.root}")
            Timer(2, self.set_dagroot, args=(self.root,)).start()

    def extract_stack_defines(self):
        """ Extract firmware definitions for the OpenVisualizer parser from the OpenWSN-FW files. """
        log.info('extracting firmware definitions.')
        definitions = {
            "components": extract_component_codes(os.path.join(self.fw_path, 'inc', 'defs.h')),
            "log_descriptions": extract_log_descriptions(os.path.join(self.fw_path, 'inc', 'defs.h')),
            "sixtop_returncodes": extract_6top_rcs(os.path.join(self.fw_path, 'stack', '02b-MAChigh', 'sixtop.h')),
            "sixtop_states": extract_6top_states(os.path.join(self.fw_path, 'stack', '02b-MAChigh', 'sixtop.h')),
        }

        return definitions

    def shutdown(self) -> None:
        """ Shutdown server and all its thread-based components. """

        if hasattr(self, 'simulator'):
            self.simulator.shutdown()
            self.simulator.join()

        self.tun.close()
        # self.jrc.close()

        for probe in self.mote_probes:
            probe.close()
            probe.join()

        raise KeyboardInterrupt()

    # ======================== RPC functions ================================

    @staticmethod
    def remote_shutdown() -> None:
        """ Function called from client """

        # we cannot call the shutdown function directly, otherwise the KeyBoardInterrupt would be returned to the client
        # instead of being intercept by the __main__.py module.
        def keyboard_interrupt():
            os.kill(os.getpid(), signal.SIGINT)

        Timer(1, keyboard_interrupt, args=()).start()

    def get_dag(self):
        self.topology.get_dag()

    def get_runtime(self, address: str) -> Tuple[float, float]:
        """ Get the real and simulated runtime of the simulation """

        if self.mode != self.Mode.SIMULATION:
            raise Fault(faultCode='-1', faultString="Only available during simulation")
        else:
            self.simulator.mote_cmd_ifs[int(address)].put('runtime')
            return eval(self.simulator.mote_cmd_ifs[int(address)].get(timeout=2))

    def pause_simulation(self) -> bool:
        """ Pauses or unpauses simulation engine. """

        if self.mode != self.Mode.SIMULATION:
            raise Fault(faultCode='-1', faultString="Can only pause a simulation")
        else:
            return self.simulator.pause()

    def get_dagroot(self) -> str:
        """ Getter for the network DAGroot. """

        for ms in self.mote_states:
            if ms.get_state_elem(motestate.MoteState.ST_IDMANAGER).is_dagroot():
                return ms.get_state_elem(motestate.MoteState.ST_IDMANAGER).get_16b_addr()

    def set_dagroot(self, port_or_address: str) -> None:
        """ Setter for the network DAGroot. """

        mote_dict = self.get_mote_dict()
        if port_or_address in mote_dict:
            port = mote_dict[port_or_address]
        elif port_or_address in mote_dict.values():
            port = port_or_address
        else:
            raise Fault(faultCode='-1', faultString="Unknown port or address: {}".format(port_or_address))

        for ms in self.mote_states:
            try:
                if ms.mote_connector.serialport == port:
                    return ms.trigger_action(MoteState.TRIGGER_DAGROOT)
            except ValueError as err:
                log.error(err)
                break
        raise Fault(faultCode='-1', faultString="Could not set {} as root".format(port))

    def get_mote_dict(self) -> Dict[str, str]:
        """ Returns a dictionary with key-value entry: {mote_id: serial-port} """

        mote_dict = {}

        for ms in self.mote_states:
            address = ms.get_state_elem(motestate.MoteState.ST_IDMANAGER).get_16b_addr()
            if address:
                mote_dict[address] = ms.mote_connector.serialport
            else:
                mote_dict[ms.mote_connector.serialport] = address

        return mote_dict

    def get_mote_state(self, mote_id) -> Optional[Dict[int, str]]:
        """
        Returns the MoteState object for the provided connected mote.
        :param mote_id: 16-bit ID of mote
        :rtype: MoteState or None if not found
        """

        for ms in self.mote_states:
            id_manager = ms.get_state_elem(ms.ST_IDMANAGER)
            if id_manager and id_manager.get_16b_addr():
                address = id_manager.get_16b_addr()
                if address == mote_id:
                    return OpenVisualizer._extract_mote_states(ms)
        else:
            raise Fault(faultCode='-1', faultString="Unknown mote ID: {}".format(mote_id))

    def get_motes_connectivity(self) -> tuple:
        motes = []
        states = []
        edges = []
        src_s = None

        for ms in self.mote_states:
            id_manager = ms.get_state_elem(ms.ST_IDMANAGER)
            if id_manager and id_manager.get_16b_addr():
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

    def get_network_topology(self):
        pass
        # motes = []
        # address = 1

        # if self.mode != self.Mode.SIMULATION:
        #     raise Fault(faultCode='-1', faultString="Only available during simulation")
        # else:
        #     while True:
        #         try:
        #             self.simulator.mote_cmd_ifs[address].put('location')
        #             lat, lon = eval(self.simulator.mote_cmd_ifs[address].get(timeout=2))
        #             motes += [{'id': address, 'lat': lat, 'lon': lon}]
        #             address += 1
        #         except IndexError:
        #             break

        # print(motes)
        # connections
        # connections = self.simengine.propagation.retrieve_connections()

        # data = {'motes': motes, 'connections': connections}
        return {}

    def retrieve_routing_path(self, destination) -> Dict[str, Any]:
        route = self._dispatch_and_get_result(signal='getSourceRoute', data=destination)
        route = [r[-1] for r in route]
        data = {'route': route}

        return data

    def enable_wireshark_debug(self) -> None:
        if isinstance(self.tun, OpenTunNull):
            raise Fault(faultCode='-1', faultString="Wireshark debugging requires tun to be active on the server")
        else:
            self.ebm.wireshark_debug_enabled = True

    def disable_wireshark_debug(self) -> None:
        if isinstance(self.tun, OpenTunNull):
            raise Fault(faultCode='-1', faultString="Wireshark debugging requires tun to be active on the server")
        else:
            self.ebm.wireshark_debug_enabled = False

    def get_wireshark_debug(self) -> bool:
        return self.ebm.wireshark_debug_enabled

    def get_ebm_stats(self):
        return self.ebm.get_stats()

    @staticmethod
    def _extract_mote_states(ms) -> Dict[int, str]:
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
