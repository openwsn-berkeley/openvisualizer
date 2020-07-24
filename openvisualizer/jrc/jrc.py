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
import json
import verboselogs
from appdirs import user_data_dir
from coap import coap, coapResource, coapDefines as Defs, coapUtils as Utils, coapObjectSecurity as Oscoap

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
        self.coap_server = CoapServer(coap_resource, ContextHandler(coap_resource).security_context_lookup)

    def close(self):
        self.coap_server.close()


# ======================== Security Context Handler =========================
class ContextHandler(object):
    # value of the OSCORE Master Secret from 6TiSCH TD
    master_secret = "DEADBEEFCAFEDEADBEEFCAFEDEADBEEF"
    master_salt = ""

    def __init__(self, join_resource):
        self.join_resource = join_resource

    # ======================== Context Handler needs to be registered =============================
    def security_context_lookup(self, kid, kid_context):

        eui64 = kid_context
        sender_id = "JRC"
        recipient_id = ""

        # if eui-64 is found in the list of joined nodes, return the appropriate context
        # this is important for replay protection
        for dictionary in self.join_resource.joinedNodes:
            if dictionary['eui64'] == eui64:
                try:
                    log.verbose("Node {0} found in joinedNodes. Returning context {1}.".format(
                        format_ipv6_addr(dictionary['eui64']), str(dictionary['context'])))
                except TypeError:
                    log.error("Type-error in conversion of {}".format(dictionary['eui64']))

                return dictionary['context']

        # if eui-64 is not found, create a new tentative context but only add it to the list of joined nodes in the GET
        # handler of the join resource
        file_path = os.path.abspath(os.path.join(user_data_dir('openvisualizer'), "oscore_context_{0}.json".
                                                 format(binascii.hexlify(eui64))))
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

        log.verbose("New node: {0}. Creating new OSCORE context in {1}.".
                    format(format_ipv6_addr(Utils.str2buf(eui64)), file_path))

        # FIXME: until persistency is implemented in firmware, we need to overwrite the security context for each run
        # FIXME: this is a security issue as AEAD nonces get reused and should not be used in a production environment
        self.security_context_create_overwrite(file_path,
                                               binascii.hexlify(eui64),
                                               self.master_salt,
                                               self.master_secret,
                                               binascii.hexlify(sender_id),
                                               binascii.hexlify(recipient_id))

        context = Oscoap.SecurityContext(securityContextFilePath=file_path)

        return context

    # create and return a security context file
    @staticmethod
    def security_context_create_overwrite(file_path, id_context, master_salt, master_secret, sender_id, recipient_id):
        ctx_dict = {
            "aeadAlgorithm": "AES_CCM_16_64_128",
            "hashFunction": "sha256",
            "idContext": id_context,
            "masterSalt": master_salt,
            "masterSecret": master_secret,
            "recipientID": recipient_id,
            "senderID": sender_id,
            "replayWindow": [0],
            "sequenceNumber": 0,
        }

        with open(file_path, "w") as context_file:
            json.dump(ctx_dict, context_file, indent=4, sort_keys=True)


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
        self.coap_server = coap.coap(udpPort=Defs.DEFAULT_UDP_PORT, testing=True)
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
                    'callback': self._register_dagroot_notif,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'unregisterDagRoot',
                    'callback': self._unregister_dagroot_notif,
                },
            ],
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
                Defs.DEFAULT_UDP_PORT,
            ),
            callback=self._receive_from_mesh,
        )

        # register to receive at link-local DAG root's address
        self.register(
            sender=self.WILDCARD,
            signal=(
                tuple(self.LINK_LOCAL_PREFIX + data['host']),
                self.PROTO_UDP,
                Defs.DEFAULT_UDP_PORT,
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
                Defs.DEFAULT_UDP_PORT,
            ),
            callback=self._receive_from_mesh,
        )
        # unregister link-local address
        self.unregister(
            sender=self.WILDCARD,
            signal=(
                tuple(self.LINK_LOCAL_PREFIX + data['host']),
                self.PROTO_UDP,
                Defs.DEFAULT_UDP_PORT,
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
            coap.coap(ipAddress=sender, udpPort=Defs.DEFAULT_UDP_PORT, testing=True,
                      receiveCallback=self._receive_from_coap)
        # low level forward of the CoAP message
        self.coap_client.socketUdp.sendUdp(destIp='', destPort=Defs.DEFAULT_UDP_PORT, msg=data[1])
        return True

    def _receive_from_coap(self, timestamp, sender, data):
        """
        Receive CoAP response and forward it to the mesh network.
        Appends UDP and IPv6 headers to the CoAP message and forwards it on the Eventbus towards the mesh.
        """
        self.coap_client.close()

        # UDP
        udp_len = len(data) + 8

        udp = Utils.int2buf(sender[1], 2)  # src port
        udp += Utils.int2buf(self.coap_client.udpPort, 2)  # dest port
        udp += [udp_len >> 8, udp_len & 0xff]  # length
        udp += [0x00, 0x00]  # checksum
        udp += data

        # destination address of the packet is CoAP client's IPv6 address (address of the mote)
        dst_ipv6_address = Utils.ipv6AddrString2Bytes(self.coap_client.ipAddress)
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
            payload=udp,
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
        self.dispatch(signal='v6ToMesh', data=ip)


# ==================== Implementation of CoAP join resource =====================
class JoinResource(coapResource.coapResource):
    def __init__(self):
        self.joinedNodes = []

        self.networkKey = Utils.str2buf(os.urandom(16))  # random key every time OpenVisualizer is initialized
        self.networkKeyIndex = 0x01  # L2 key index

        # initialize parent class
        coapResource.coapResource.__init__(self, path='j')

        self.addSecurityBinding((None, [Defs.METHOD_POST]))  # security context should be returned by the callback

    def POST(self, options=[], payload=[]):  # noqa: N802

        log.verbose("received JRC join request")

        link_layer_keyset = [self.networkKeyIndex, Utils.buf2str(self.networkKey)]

        configuration = {CoJPLabel.COJP_PARAMETERS_LABELS_LLKEYSET: link_layer_keyset}

        configuration_serialized = cbor.dumps(configuration)

        resp_payload = [ord(b) for b in configuration_serialized]

        object_security = Oscoap.objectSecurityOptionLookUp(options)

        if object_security:
            # we need to add the pledge to a list of joined nodes, if not present already
            eui64 = Utils.buf2str(object_security.kidContext)
            found = False
            for node in self.joinedNodes:
                if node['eui64'] == eui64:
                    found = True
                    break

            if not found:
                self.joinedNodes += [
                    {
                        'eui64': eui64,  # remove last prepended byte
                        'context': object_security.context,
                    },
                ]

            # return the Join Response regardless of whether it is a first or Nth join attempt
            return Defs.COAP_RC_2_04_CHANGED, [], resp_payload
        else:
            return Defs.COAP_RC_4_01_UNAUTHORIZED, [], []
