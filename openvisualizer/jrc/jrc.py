"""
# Copyright (c) 2010-2020, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
"""

import binascii
import logging.handlers
import os
import threading

import cbor
import verboselogs
from coap import coap, coapResource, coapDefines as d, coapUtils as u, coapObjectSecurity as oscoap

from openvisualizer.eventbus.eventbusclient import EventBusClient
from openvisualizer.jrc.cojp_defines import CoJPLabel
from openvisualizer.utils import format_ipv6_addr, calculate_pseudo_header_crc

verboselogs.install()

log = logging.getLogger('JRC')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


# ======================== Top Level jrc Class =============================
class JRC(object):
    def __init__(self):
        coap_resource = JoinResource()
        self.coap_server = CoapServer(coap_resource, Contexthandler(coap_resource).security_context_lookup)

    def close(self):
        self.coap_server.close()


# ======================== Security Context Handler =========================
class Contexthandler(object):
    # value of the OSCORE Master Secret from 6TiSCH TD
    MASTERSECRET = binascii.unhexlify('DEADBEEFCAFEDEADBEEFCAFEDEADBEEF')

    def __init__(self, join_resource):
        self.join_resource = join_resource

    # ======================== Context Handler needs to be registered =============================
    def security_context_lookup(self, kid):
        kid_buf = u.str2buf(kid)

        eui64 = kid_buf[:-1]
        sender_id = eui64 + [0x01]  # sender ID of jrc is reversed
        recipient_id = eui64 + [0x00]

        # if eui-64 is found in the list of joined nodes, return the appropriate context
        # this is important for replay protection
        for dictionary in self.join_resource.joinedNodes:
            if dictionary['eui64'] == u.buf2str(eui64):
                try:
                    log.verbose("Node {0} found in joinedNodes. Returning context {1}.".format(
                        format_ipv6_addr(dictionary['eui64']), str(dictionary['context'])))
                except TypeError:
                    log.error("Type-error in conversion of {}".format(dictionary['eui64']))
                    
                return dictionary['context']

        # if eui-64 is not found, create a new tentative context but only add it to the list of joined nodes in the GET
        # handler of the join resource
        context = oscoap.SecurityContext(masterSecret=self.MASTERSECRET,
                                         senderID=u.buf2str(sender_id),
                                         recipientID=u.buf2str(recipient_id),
                                         aeadAlgorithm=oscoap.AES_CCM_16_64_128())

        log.verbose("New node: {0}. Derive new OSCORE context from master secret.".format(format_ipv6_addr(eui64)))

        return context


# ======================== Interface with OpenVisualizer ======================================
class CoapServer(EventBusClient):
    # link-local prefix
    LINK_LOCAL_PREFIX = [0xfe, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    def __init__(self, coap_resource, context_handler=None):
        # log
        log.debug("create instance")
        self.coap_resource = coap_resource

        # run CoAP server in testing mode
        # this mode does not open a real socket, rather uses PyDispatcher for sending/receiving messages
        # We interface this mode with OpenVisualizer to run jrc co-located with the DAG root
        self.coap_server = coap.coap(udpPort=d.DEFAULT_UDP_PORT, testing=True)
        self.coap_server.addResource(coap_resource)
        self.coap_server.addSecurityContextHandler(context_handler)
        self.coap_server.maxRetransmit = 1

        self.coap_client = None

        self.dagroot_eui64 = None

        # store params

        # initialize parent class
        super(CoapServer, self).__init__(
            name='jrc',
            registrations=[
                {
                    'sender': self.WILDCARD,
                    'signal': 'getL2SecurityKey',
                    'callback': self._get_l2_security_key_notif,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'registerDagRoot',
                    'callback': self._register_dagroot_notif
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'unregisterDagRoot',
                    'callback': self._unregister_dagroot_notif
                },
            ]
        )

        # local variables
        self.stateLock = threading.Lock()

    # ======================== public ==========================================

    def close(self):
        # nothing to do
        pass

    # ======================== private =========================================

    # ==== handle EventBus notifications

    def _get_l2_security_key_notif(self, sender, signal, data):
        """ Return L2 security key for the network. """

        return {'index': [self.coap_resource.networkKeyIndex], 'value': self.coap_resource.networkKey}

    def _register_dagroot_notif(self, sender, signal, data):
        # register for the global address of the DAG root
        self.register(
            sender=self.WILDCARD,
            signal=(
                tuple(data['prefix'] + data['host']),
                self.PROTO_UDP,
                d.DEFAULT_UDP_PORT
            ),
            callback=self._receive_from_mesh,
        )

        # register to receive at link-local DAG root's address
        self.register(
            sender=self.WILDCARD,
            signal=(
                tuple(self.LINK_LOCAL_PREFIX + data['host']),
                self.PROTO_UDP,
                d.DEFAULT_UDP_PORT
            ),
            callback=self._receive_from_mesh,
        )

        self.dagroot_eui64 = data['host']

    def _unregister_dagroot_notif(self, sender, signal, data):
        # unregister global address
        self.unregister(
            sender=self.WILDCARD,
            signal=(
                tuple(data['prefix'] + data['host']),
                self.PROTO_UDP,
                d.DEFAULT_UDP_PORT
            ),
            callback=self._receive_from_mesh,
        )
        # unregister link-local address
        self.unregister(
            sender=self.WILDCARD,
            signal=(
                tuple(self.LINK_LOCAL_PREFIX + data['host']),
                self.PROTO_UDP,
                d.DEFAULT_UDP_PORT
            ),
            callback=self._receive_from_mesh,
        )

        self.dagroot_eui64 = None

    def _receive_from_mesh(self, sender, signal, data):
        """
        Receive packet from the mesh destined for jrc's CoAP server.
        Forwards the packet to the virtual CoAP server running in test mode (PyDispatcher).
        """

        sender = format_ipv6_addr(data[0])
        # FIXME pass source port within the signal and open coap client at this port
        self.coap_client = \
            coap.coap(ipAddress=sender, udpPort=d.DEFAULT_UDP_PORT, testing=True,
                      receiveCallback=self._receive_from_coap)
        # low level forward of the CoAP message
        self.coap_client.socketUdp.sendUdp(destIp='', destPort=d.DEFAULT_UDP_PORT, msg=data[1])
        return True

    def _receive_from_coap(self, timestamp, sender, data):
        """
        Receive CoAP response and forward it to the mesh network.
        Appends UDP and IPv6 headers to the CoAP message and forwards it on the Eventbus towards the mesh.
        """
        self.coap_client.close()

        # UDP
        udp_len = len(data) + 8

        udp = u.int2buf(sender[1], 2)  # src port
        udp += u.int2buf(self.coap_client.udpPort, 2)  # dest port
        udp += [udp_len >> 8, udp_len & 0xff]  # length
        udp += [0x00, 0x00]  # checksum
        udp += data

        # destination address of the packet is CoAP client's IPv6 address (address of the mote)
        dst_ipv6_address = u.ipv6AddrString2Bytes(self.coap_client.ipAddress)
        assert len(dst_ipv6_address) == 16
        # source address of the packet is DAG root's IPV6 address
        # use the same prefix (link-local or global) as in the destination address
        src_ipv6_address = dst_ipv6_address[:8]
        src_ipv6_address += self.dagroot_eui64
        assert len(src_ipv6_address) == 16

        # CRC See https://tools.ietf.org/html/rfc2460.

        udp[6:8] = calculate_pseudo_header_crc(
            src=src_ipv6_address,
            dst=dst_ipv6_address,
            length=[0x00, 0x00] + udp[4:6],
            nh=[0x00, 0x00, 0x00, 17],  # UDP as next header
            payload=udp
        )

        # IPv6
        ip = [6 << 4]  # v6 + traffic class (upper nybble)
        ip += [0x00, 0x00, 0x00]  # traffic class (lower nibble) + flow label
        ip += udp[4:6]  # payload length
        ip += [17]  # next header (protocol); UDP=17
        ip += [64]  # hop limit (pick a safe value)
        ip += src_ipv6_address  # source
        ip += dst_ipv6_address  # destination
        ip += udp

        # announce network prefix
        self.dispatch(
            signal='v6ToMesh',
            data=ip
        )


# ==================== Implementation of CoAP join resource =====================
class JoinResource(coapResource.coapResource):
    def __init__(self):
        self.joinedNodes = []

        self.networkKey = u.str2buf(os.urandom(16))  # random key every time OpenVisualizer is initialized
        self.networkKeyIndex = 0x01  # L2 key index

        # initialize parent class
        coapResource.coapResource.__init__(self, path='j')

        self.addSecurityBinding((None, [d.METHOD_POST]))  # security context should be returned by the callback

    def POST(self, options=[], payload=[]):

        log.verbose("received JRC join request")

        link_layer_keyset = [self.networkKeyIndex, u.buf2str(self.networkKey)]

        configuration = {CoJPLabel.COJP_PARAMETERS_LABELS_LLKEYSET: link_layer_keyset}

        configuration_serialized = cbor.dumps(configuration)

        resp_payload = [ord(b) for b in configuration_serialized]

        object_security = oscoap.objectSecurityOptionLookUp(options)

        if object_security:
            # we need to add the pledge to a list of joined nodes, if not present already
            eui64 = u.buf2str(object_security.kid[:-1])
            found = False
            for node in self.joinedNodes:
                if node['eui64'] == eui64:
                    found = True
                    break

            if not found:
                self.joinedNodes += [
                    {'eui64': eui64,  # remove last prepended byte
                     'context': object_security.context
                     }
                ]

            # return the Join Response regardless of whether it is a first or Nth join attempt
            return d.COAP_RC_2_04_CHANGED, [], resp_payload
        else:
            return d.COAP_RC_4_01_UNAUTHORIZED, [], []
