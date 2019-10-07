from   coap   import    coap,                    \
                        coapResource,            \
                        coapDefines as d,        \
                        coapOption as o,         \
                        coapUtils as u,          \
                        coapObjectSecurity as oscoap, \
                        socketUdp
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
import time
import threading

# default IPv6 hop limit
COAP_SERVER_DEFAULT_IPv6_HOP_LIMIT = 65

class coapDispatcher(socketUdp.socketUdp, eventBusClient.eventBusClient):

    # link-local prefix
    LINK_LOCAL_PREFIX = [0xfe, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    def __init__(self, ipAddress, udpPort, callback):
        # log
        log.debug('creating instance')

        # params
        self.udpPort = udpPort
        self.dagRootEui64 = None
        self.networkPrefix = None
        self.callback = callback

        # initialize the parent socketUdp class
        socketUdp.socketUdp.__init__(self, ipAddress, self.udpPort, self.callback)

        # initialize the parent class eventBusClient class
        eventBusClient.eventBusClient.__init__(
            self,
            name='coapDispatcher',
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

        # change name
        self.name = 'coapDispatcher@DagRootIpv6:{0}'.format(self.udpPort)
        self.gotMsgSem = threading.Semaphore()

        # start myself
        self.start()

    # ======================== public ==========================================
    # TODO rework the class for it to be completely stateless and not depend on self.dagRootEui64
    def sendUdp(self, destIp, destPort, msg):
        '''
          Receive CoAP response and forward it to the mesh network.
          Appends UDP and IPv6 headers to the CoAP message and forwards it on the Eventbus towards the mesh.
          '''

        assert self.dagRootEui64
        assert self.networkPrefix

        log.debug("sendUdp to {0}:{1} message {2}".format(destIp,destPort,msg))

        # UDP
        udplen = len(msg) + 8

        # FIXME need to signal the source port from the packet
        udp = u.int2buf(self.udpPort, 2)  # src port
        udp += u.int2buf(destPort, 2)  # dest port
        udp += [udplen >> 8, udplen & 0xff]  # length
        udp += [0x00, 0x00]  # checksum
        udp += msg

        # destination address of the packet is CoAP client's IPv6 address (address of the mote)
        dstIpv6Address = u.ipv6AddrString2Bytes(destIp)
        assert len(dstIpv6Address) == 16
        # source address of the packet is DAG root's IPV6 address
        # use the same prefix (link-local or global) as in the destination address
        srcIpv6Address = dstIpv6Address[:8]
        srcIpv6Address += self.dagRootEui64
        assert len(srcIpv6Address) == 16

        # CRC See https://tools.ietf.org/html/rfc2460.

        udp[6:8] = openvisualizer.openvisualizer_utils.calculatePseudoHeaderCRC(
            src=srcIpv6Address,
            dst=dstIpv6Address,
            length=[0x00, 0x00] + udp[4:6],
            nh=[0x00, 0x00, 0x00, 17],  # UDP as next header
            payload=udp,
        )

        # IPv6
        ip = [6 << 4]  # v6 + traffic class (upper nybble)
        ip += [0x00, 0x00, 0x00]  # traffic class (lower nibble) + flow label
        ip += udp[4:6]  # payload length
        ip += [17]  # next header (protocol); UDP=17
        ip += [COAP_SERVER_DEFAULT_IPv6_HOP_LIMIT]  # hop limit (pick a safe value)
        ip += srcIpv6Address  # source
        ip += dstIpv6Address  # destination
        ip += udp

        self.dispatch(
            signal='v6ToMesh',
            data=ip
        )

        # update stats
        self._incrementTx()

    def close(self):
        # stop
        self.goOn = False
        self.gotMsgSem.release()

    # ======================== private =========================================

    def _messageNotification(self, sender, signal, data):
        # log
        log.debug("messageNotification: got {1} from {0}".format(sender, data))

        srcIpv6 = openvisualizer.openvisualizer_utils.formatIPv6Addr(data[0])
        rawbytes = data[1]
        hopLimit = data[2] # IPv6 metadata
        timestamp = str(data[3]) # timestamp of the received packet

        sender = (srcIpv6, self.udpPort, (hopLimit, timestamp))

        # call the callback
        self.callback(timestamp, sender, rawbytes)

        # update stats
        self._incrementRx()

        # release the lock
        self.gotMsgSem.release()

        # return success in order to acknowledge the reception
        return True

    def run(self):
        while self.goOn:
            self.gotMsgSem.acquire()

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
            callback=self._messageNotification,
        )

        # register to receive at link-local DAG root's address
        self.register(
            sender=self.WILDCARD,
            signal=(
                tuple(self.LINK_LOCAL_PREFIX + data['host']),
                self.PROTO_UDP,
                d.DEFAULT_UDP_PORT
            ),
            callback=self._messageNotification,
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
            callback=self._messageNotification,
        )
        # unregister link-local address
        self.unregister(
            sender=self.WILDCARD,
            signal=(
                tuple(self.LINK_LOCAL_PREFIX + data['host']),
                self.PROTO_UDP,
                d.DEFAULT_UDP_PORT
            ),
            callback=self._messageNotification,
        )

        self.dagRootEui64 = None
        self.networkPrefix = None
