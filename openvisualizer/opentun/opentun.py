# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import abc
import logging
import socket
import sys
import time

import verboselogs

from openvisualizer.eventbus.eventbusclient import EventBusClient
from openvisualizer.utils import format_ipv6_addr

verboselogs.install()

log = logging.getLogger('OpenTun')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


class OpenTun(EventBusClient):
    """
    Class which interfaces between a TUN virtual interface and an EventBus.
    This class is abstract, with concrete subclasses based on operating system.
    """
    __metaclass__ = abc.ABCMeta

    # dynamically records supported operating systems
    os_support = {}

    # IPv6 address for TUN interface
    IPV6PREFIX = [0xbb, 0xbb, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    IPV6HOST = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01]

    def __init__(self):
        # register to receive outgoing network packets
        super(OpenTun, self).__init__(
            name='OpenTun',
            registrations=[
                {
                    'sender': self.WILDCARD,
                    'signal': 'getNetworkPrefix',
                    'callback': self._get_network_prefix_notif,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'getNetworkHost',
                    'callback': self._get_network_host_notif,
                },
                {
                    'sender': self.WILDCARD,
                    'signal': 'v6ToInternet',
                    'callback': self._v6_to_internet_notif,
                },
            ],
        )

        # local variables
        self.tun_if = self._create_tun_if()
        if self.tun_if:
            self.tun_read_thread = self._create_tun_read_thread()
        else:
            self.tun_read_thread = None

        # TODO: retrieve network prefix from interface settings

        # announce network prefix
        self.dispatch(signal='networkPrefix', data=self.IPV6PREFIX)

    # ======================== public ==========================================

    @classmethod
    def record_os(cls, os_id):
        """Decorator to record all the operating systems dynamically"""

        def decorator(the_class):
            if not issubclass(the_class, OpenTun):
                raise ValueError("Can only decorate subclass of OpenTun")
            cls.os_support[os_id] = the_class
            return the_class

        return decorator

    @classmethod
    def create(cls, opentun=False):
        """ Module-based Factory method to create instance based on operating system. """

        if not opentun:
            return cls.os_support['null']()

        elif sys.platform.startswith('win32'):
            return cls.os_support['win32']()

        elif sys.platform.startswith('linux'):
            return cls.os_support['linux']()

        elif sys.platform.startswith('darwin'):
            return cls.os_support['darwin']()

        else:
            raise NotImplementedError('Platform {0} not supported'.format(sys.platform))

    def close(self):

        if self.tun_read_thread:

            self.tun_read_thread.close()

            # Send a packet to OpenTun interface to break out of blocking read.
            attempts = 0
            while self.tun_read_thread.isAlive() and attempts < 3:
                attempts += 1
                try:
                    log.info('Closing tun interface')
                    log.debug('Sending UDP packet to close OpenTun')
                    sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
                    # Destination must route through the TUN host, but not be the host itself.
                    # OK if host does not really exist.
                    dst = self.IPV6PREFIX + self.IPV6HOST
                    dst[15] += 1
                    # Payload and destination port are arbitrary
                    sock.sendto('stop', (format_ipv6_addr(dst), 18004))
                    # Give thread some time to exit
                    time.sleep(0.05)
                except Exception as err:
                    log.error('Unable to send UDP to close tun_read_thread: {0}'.format(str(err)))

    # ======================== private =========================================

    def _get_network_prefix_notif(self, sender, signal, data):
        return self.IPV6PREFIX

    def _get_network_host_notif(self, sender, signal, data):
        return self.IPV6HOST

    def _v6_to_mesh_notif(self, data):
        """
        Called when receiving data from the TUN interface.
        This function forwards the data to the the EventBus. Read from 6lowPAN and forward to TUN interface
        """

        # dispatch to EventBus
        self.dispatch(signal='v6ToMesh', data=data)

    @abc.abstractmethod
    def _create_tun_if(self):
        """
        Open a TUN/TAP interface and switch it to TUN mode.
        :returns: The handler of the interface, which can be used for later read/write operations.
        """

        raise NotImplementedError('subclass must implement')

    @abc.abstractmethod
    def _create_tun_read_thread(self):
        """ Creates the thread to read messages arriving from the TUN interface """
        raise NotImplementedError('subclass must implement')

    @abc.abstractmethod
    def _v6_to_internet_notif(self, sender, signal, data):
        """
        Called when receiving data from the EventBus.

        This function forwards the data to the the TUN interface. Read from tun interface and forward to 6lowPAN
        """
        raise NotImplementedError('subclass must implement')
