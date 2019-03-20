from   coap   import    coap,                    \
                        coapResource,            \
                        coapDefines as d,        \
                        coapOption as o,         \
                        coapUtils as u,          \
                        coapObjectSecurity as oscoap
import logging.handlers
try:
    from openvisualizer.eventBus import eventBusClient
    import openvisualizer.openvisualizer_utils
except ImportError:
    pass

log = logging.getLogger('coapServer')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

import cbor
import binascii
import os
import threading

class coapServer(eventBusClient.eventBusClient):
    # link-local prefix
    LINK_LOCAL_PREFIX = [0xfe, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    # default IPv6 hop limit
    COAP_SERVER_DEFAULT_IPv6_HOP_LIMIT = 65

    def __init__(self):
        # log
        log.info("create instance")

        # run CoAP server in testing mode
        # this mode does not open a real socket, rather uses PyDispatcher for sending/receiving messages
        # We interface this mode with OpenVisualizer to run JRC co-located with the DAG root
        self.coapServer = coap.coap(udpPort=d.DEFAULT_UDP_PORT, testing=True)

        self.ephemeralCoapClient = None

        self.dagRootEui64 = None
        self.networkPrefix = None

        # store params

        # initialize parent class
        eventBusClient.eventBusClient.__init__(
            self,
            name='coapServer',
            registrations=[
                {
                    'sender': self.WILDCARD,
                    'signal': 'registerDagRoot',
                    'callback': self._registerDagRoot_notif
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'unregisterDagRoot',
                    'callback': self._unregisterDagRoot_notif
                },
            ]
        )

        # local variables
        self.stateLock = threading.Lock()

    # ======================== public ==========================================

    def close(self):
        # nothing to do
        pass

    def getDagRootEui64(self):
        return self.dagRootEui64

    def getDagRootIPv6(self):
        ipv6buf = self.networkPrefix + self.dagRootEui64
        return openvisualizer.openvisualizer_utils.formatIPv6Addr(ipv6buf)

    # ======================== private =========================================

    # ==== handle EventBus notifications

    def _registerDagRoot_notif(self, sender, signal, data):
        # register for the global address of the DAG root
        self.register(
            sender=self.WILDCARD,
            signal=(
                tuple(data['prefix'] + data['host']),
                self.PROTO_UDP,
                d.DEFAULT_UDP_PORT
            ),
            callback=self._receiveFromMesh,
        )

        # register to receive at link-local DAG root's address
        self.register(
            sender=self.WILDCARD,
            signal=(
                tuple(self.LINK_LOCAL_PREFIX + data['host']),
                self.PROTO_UDP,
                d.DEFAULT_UDP_PORT
            ),
            callback=self._receiveFromMesh,
        )

        self.dagRootEui64 = data['host']
        self.networkPrefix = data['prefix']

    def _unregisterDagRoot_notif(self, sender, signal, data):
        # unregister global address
        self.unregister(
            sender=self.WILDCARD,
            signal=(
                tuple(data['prefix'] + data['host']),
                self.PROTO_UDP,
                d.DEFAULT_UDP_PORT
            ),
            callback=self._receiveFromMesh,
        )
        # unregister link-local address
        self.unregister(
            sender=self.WILDCARD,
            signal=(
                tuple(self.LINK_LOCAL_PREFIX + data['host']),
                self.PROTO_UDP,
                d.DEFAULT_UDP_PORT
            ),
            callback=self._receiveFromMesh,
        )

        self.dagRootEui64 = None
        self.networkPrefix = None

    def _receiveFromMesh(self, sender, signal, data):
        '''
        Receive packet from the mesh destined for JRC's CoAP server.
        Forwards the packet to the virtual CoAP server running in test mode (PyDispatcher).
        '''
        sender = openvisualizer.openvisualizer_utils.formatIPv6Addr(data[0])

        hopLimit = data[2] # IPv6 metadata
        timestamp = str(data[3]) # timestamp of the received packet

        # FIXME pass source port within the signal and open coap client at this port
        self.ephemeralCoapClient = coap.coap(ipAddress=sender, udpPort=d.DEFAULT_UDP_PORT, testing=True, receiveCallback=self._receiveFromCoAP)
        self.ephemeralCoapClient.socketUdp.sendUdp(destIp='', destPort=d.DEFAULT_UDP_PORT, msg=data[1],metaData=(hopLimit, timestamp)) # low level forward of the CoAP message
        return True

    def _receiveFromCoAP(self, timestamp, sender, data):
        '''
        Receive CoAP response and forward it to the mesh network.
        Appends UDP and IPv6 headers to the CoAP message and forwards it on the Eventbus towards the mesh.
        '''
        self.ephemeralCoapClient.close()

        # UDP
        udplen = len(data) + 8

        udp = u.int2buf(sender[1], 2)  # src port
        udp += u.int2buf(self.ephemeralCoapClient.udpPort, 2)  # dest port
        udp += [udplen >> 8, udplen & 0xff]  # length
        udp += [0x00, 0x00]  # checksum
        udp += data

        # destination address of the packet is CoAP client's IPv6 address (address of the mote)
        dstIpv6Address = u.ipv6AddrString2Bytes(self.ephemeralCoapClient.ipAddress)
        assert len(dstIpv6Address)==16
        # source address of the packet is DAG root's IPV6 address
        # use the same prefix (link-local or global) as in the destination address
        srcIpv6Address = dstIpv6Address[:8]
        srcIpv6Address += self.dagRootEui64
        assert len(srcIpv6Address)==16

        # CRC See https://tools.ietf.org/html/rfc2460.

        udp[6:8] = openvisualizer.openvisualizer_utils.calculatePseudoHeaderCRC(
            src=srcIpv6Address,
            dst=dstIpv6Address,
            length=[0x00, 0x00] + udp[4:6],
            nh=[0x00, 0x00, 0x00, 17], # UDP as next header
            payload=udp,
        )

        # IPv6
        ip = [6 << 4]  # v6 + traffic class (upper nybble)
        ip += [0x00, 0x00, 0x00]  # traffic class (lower nibble) + flow label
        ip += udp[4:6]  # payload length
        ip += [17]  # next header (protocol); UDP=17
        ip += [self.COAP_SERVER_DEFAULT_IPv6_HOP_LIMIT]  # hop limit (pick a safe value)
        ip += srcIpv6Address  # source
        ip += dstIpv6Address  # destination
        ip += udp

        # announce network prefix
        self.dispatch(
            signal        = 'v6ToMesh',
            data          = ip
        )
