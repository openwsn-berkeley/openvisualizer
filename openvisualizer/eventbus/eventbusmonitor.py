# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import copy
import json
import logging
import threading

from pydispatch import dispatcher
from scapy.compat import raw
from scapy.layers.inet import UDP
from scapy.layers.inet6 import IPv6

from openvisualizer.opentun.opentun import OpenTun
from openvisualizer.utils import format_buf, calculate_fcs, format_ipv6_addr

log = logging.getLogger('EventBusMonitor')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


class EventBusMonitor(object):

    def __init__(self):

        # log
        log.debug("create instance")

        # store params

        # local variables
        self.data_lock = threading.Lock()
        self.stats = {}
        self.wireshark_debug_enabled = True
        self.dagoot_eui64 = [0x00] * 8
        self.sim_mode = False

        # give this instance a name
        self.name = 'EventBusMonitor'

        # connect to dispatcher
        dispatcher.connect(self._eventbus_notification)

    # ======================== public ==========================================

    def get_stats(self):

        # get a copy of stats
        with self.data_lock:
            temp_stats = copy.deepcopy(self.stats)

        # format as a dictionnary
        return_val = [
            {
                'sender': k[0],
                'signal': k[1],
                'num': v,
            } for (k, v) in temp_stats.items()
        ]

        # send back JSON string
        return json.dumps(return_val)

    def set_wireshark_debug(self, is_enabled):
        """
        Turns on/off the export of a copy of mesh-bound messages to the Internet interface, in the form of ZEP packets.
        Well-suited to viewing the packets in Wireshark. See http://wiki.wireshark.org/IEEE_802.15.4 for ZEP details.
        """
        with self.data_lock:
            self.wireshark_debug_enabled = (True and is_enabled)
        log.info('%s export of ZEP mesh debug packets to Internet',
                 'Enabled' if self.wireshark_debug_enabled else 'Disabled')

    # ======================== private =========================================

    def _eventbus_notification(self, signal, sender, data):
        """ Adds the signal to stats log and performs signal-specific handling """

        with self.data_lock:
            key = (sender, signal)
            if key not in self.stats:
                self.stats[key] = 0
            self.stats[key] += 1

        if signal == 'infoDagRoot' and data['isDAGroot'] == 1:
            self.dagoot_eui64 = data['eui64'][:]

        if signal == 'wirelessTxStart':
            # this signal only exists is simulation mode
            self.sim_mode = True

        if self.wireshark_debug_enabled:

            if self.sim_mode:
                # simulation mode

                if signal == 'wirelessTxStart':
                    # Forwards a copy of the packet exchanged between simulated motes
                    # to the tun interface for debugging.

                    (mote_id, frame, frequency) = data

                    if log.isEnabledFor(logging.DEBUG):
                        output = []
                        output += ['']
                        output += ['- moteId:    {0}'.format(mote_id)]
                        output += ['- frame:     {0}'.format(format_buf(frame))]
                        output += ['- frequency: {0}'.format(frequency)]
                        output = '\n'.join(output)
                        log.debug(output)

                    assert len(frame) >= 1 + 2  # 1 for length byte, 2 for CRC

                    # cut frame in pieces
                    _ = frame[0]  # length
                    body = frame[1:-2]
                    _ = frame[-2:]  # crc

                    # wrap with zep header
                    zep = self._wrap_zep_crc(body, frequency)
                    self._dispatch_mesh_debug_packet(zep)

            else:
                # non-simulation mode

                if signal == 'fromMote.data':
                    # Forwards a copy of the data received from a mode to the Internet interface for debugging.
                    (previous_hop, lowpan) = data

                    zep = self._wrap_mac_and_zep(previous_hop=previous_hop, next_hop=self.dagoot_eui64, lowpan=lowpan)
                    self._dispatch_mesh_debug_packet(zep)

                if signal == 'fromMote.sniffedPacket':
                    body = data[0:-3]
                    _ = data[-3:-1]  # crc
                    frequency = data[-1]

                    # wrap with zep header
                    zep = self._wrap_zep_crc(body, frequency)
                    self._dispatch_mesh_debug_packet(zep)

                if signal == 'bytesToMesh':
                    # Forwards a copy of the 6LoWPAN packet destined for the mesh to the tun interface for debugging.
                    (next_hop, lowpan) = data

                    zep = self._wrap_mac_and_zep(previous_hop=self.dagoot_eui64, next_hop=next_hop, lowpan=lowpan)
                    self._dispatch_mesh_debug_packet(zep)

    def _wrap_mac_and_zep(self, previous_hop, next_hop, lowpan):
        """
        Returns Exegin ZEP protocol header and dummy 802.15.4 header wrapped around outgoing 6LoWPAN layer packet.
        """

        phop = previous_hop[:]
        phop.reverse()
        nhop = next_hop[:]
        nhop.reverse()

        # ZEP
        zep = [ord('E'), ord('X')]  # Protocol ID String
        zep += [0x02]  # Protocol Version
        zep += [0x01]  # Type
        zep += [0x00]  # Channel ID
        zep += [0x00, 0x01]  # Device ID
        zep += [0x01]  # LQI/CRC mode
        zep += [0xff]
        zep += [0x01] * 8  # timestamp
        zep += [0x02] * 4  # sequence number
        zep += [0x00] * 10  # reserved
        zep += [21 + len(lowpan) + 2]  # length

        # IEEE802.15.4                 (data frame with dummy values)
        mac = [0x41, 0xcc]  # frame control
        mac += [0x66]  # sequence number
        mac += [0xfe, 0xca]  # destination PAN ID
        mac += nhop  # destination address
        mac += phop  # source address
        mac += lowpan
        # CRC
        mac += calculate_fcs(mac)

        return zep + mac

    def _wrap_zep_crc(self, body, frequency):

        # ZEP header
        zep = [ord('E'), ord('X')]  # Protocol ID String
        zep += [0x02]  # Protocol Version
        zep += [0x01]  # Type
        zep += [frequency]  # Channel ID
        zep += [0x00, 0x01]  # Device ID
        zep += [0x01]  # LQI/CRC mode
        zep += [0xff]
        zep += [0x01] * 8  # timestamp
        zep += [0x02] * 4  # sequence number
        zep += [0x00] * 10  # reserved
        zep += [len(body) + 2]  # length

        # mac frame
        mac = body
        mac += calculate_fcs(mac)

        return zep + mac

    def _dispatch_mesh_debug_packet(self, zep):
        """
        Wraps ZEP-based debug packet, for outgoing mesh 6LoWPAN message,  with UDP and IPv6 headers. Then forwards as
        an event to the Internet interface.
        """

        # UDP
        udp = UDP(sport=0, dport=17754)
        udp.add_payload("".join([chr(i) for i in zep]))

        # Common address for source and destination
        addr = []
        addr += OpenTun.IPV6PREFIX
        addr += OpenTun.IPV6HOST
        addr = format_ipv6_addr(addr)

        # IP
        ip = IPv6(version=6, tc=0, src=addr, hlim=64, dst=addr)
        ip = ip / udp

        data = [ord(b) for b in raw(ip)]

        dispatcher.send(sender=self.name, signal='v6ToInternet', data=data)
