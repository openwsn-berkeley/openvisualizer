# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import os
import sys
import threading

from openvisualizer.opentun.opentun import OpenTun
from openvisualizer.utils import format_buf, format_crash_message, format_critical_message, format_ipv6_addr

log = logging.getLogger('OpenTunMacOS')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


# ============================ helper classes ==================================

class TunReadThread(threading.Thread):
    """
    Thread which continuously reads input from a TUN interface.

    When data is received from the interface, it calls a callback configured during instantiation.
    """

    ETHERNET_MTU = 1500
    IPv6_HEADER_LENGTH = 40

    def __init__(self, tun_if, callback):

        # store params
        self.tun_if = tun_if
        self.callback = callback

        # local variables
        self.goOn = True

        # initialize parent
        super(TunReadThread, self).__init__()

        # give this thread a name
        self.name = 'TunReadThread'

        # start myself
        self.start()

    def run(self):
        try:
            while self.goOn:
                # wait for data
                p = os.read(self.tun_if, self.ETHERNET_MTU)

                # convert input from a string to a byte list
                p = [ord(b) for b in p]

                # debug info
                log.debug('packet captured on tun interface: {0}'.format(format_buf(p)))

                # make sure it's an IPv6 packet (i.e., starts with 0x6x)
                if (p[0] & 0xf0) != 0x60:
                    continue

                # because of the nature of tun for Windows, p contains ETHERNET_MTU
                # bytes. Cut at length of IPv6 packet.
                p = p[:self.IPv6_HEADER_LENGTH + 256 * p[4] + p[5]]

                # call the callback
                self.callback(p)
        except Exception as err:
            err_msg = format_crash_message(self.name, err)
            log.critical(err_msg)
            sys.exit(1)

    # ======================== public ==========================================

    def close(self):
        self.goOn = False


# ============================ main class ======================================
@OpenTun.record_os('darwin')
class OpenTunMACOS(OpenTun):
    """ Class which interfaces between a TUN virtual interface and an EventBus. """

    # insert 4 octedts ID tun for compatibility (it'll be discard)
    VIRTUAL_TUN_ID = [0x00, 0x00, 0x86, 0xdd]

    IFF_TUN = 0x0001
    TUN_SET_IFF = 0x400454ca

    def __init__(self):
        # log
        log.debug("create instance")

        # initialize parent class
        super(OpenTunMACOS, self).__init__()

    # ======================== public ==========================================

    # ======================== private =========================================

    def _v6_to_internet_notif(self, sender, signal, data):
        """
        Called when receiving data from the EventBus.
        This function forwards the data to the the TUN interface. Read from tun interface and forward to 6lowPAN
        """

        # convert data to string
        data = ''.join([chr(b) for b in data])

        try:
            # write over tuntap interface
            os.write(self.tun_if, data)
            log.debug("data dispatched to tun correctly {0}, {1}".format(signal, sender))
        except Exception as err:
            err_msg = format_critical_message(err)
            log.critical(err_msg)

    def _create_tun_if(self):
        """
        Open a TUN/TAP interface and switch it to TUN mode.
        :returns: The handler of the interface, which can be used for later read/write operations.
        """
        # =====
        log.info("opening tun interface")

        tun_counter = 0
        while tun_counter < 16:
            try:
                if_name = 'tun{0}'.format(tun_counter)
                f = os.open("/dev/{0}".format(if_name), os.O_RDWR)
                break
            except OSError:
                tun_counter += 1

        if tun_counter == 16:
            raise OSError('TUN device not found: check if it exists or if it is busy')
        else:
            # =====
            log.debug("configuring IPv6 address")
            prefix_str = format_ipv6_addr(self.IPV6PREFIX)
            host_str = format_ipv6_addr(self.IPV6HOST)

            _ = os.system('ifconfig {0} inet6 {1}:{2} prefixlen 64'.format(if_name, prefix_str, host_str))
            _ = os.system('ifconfig {0} inet6 fe80::{1} prefixlen 64 add'.format(if_name, host_str))

            # =====
            log.debug("adding static route route")
            # added 'metric 1' for router-compatibility constraint
            # (show ping packet on wireshark but don't send to mote at all)
            # os.system('ip -6 route add ' + prefixStr + ':1415:9200::/96 dev ' + ifname + ' metric 1')
            os.system('route add -inet6 {0}:1415:9200::/96 -interface {1}'.format(prefix_str, if_name))
            # trying to set a gateway for this route
            # os.system('ip -6 route add ' + prefixStr + '::/64 via ' + IPv6Prefix + ':' + hostStr + '/64')

            # =====
            log.debug("enabling IPv6 forwarding")
            # os.system('echo 1 > /proc/sys/net/ipv6/conf/all/forwarding')
            os.system('sysctl -w net.inet6.ip6.forwarding=1')

            # =====
            log.info('created following virtual interfaces')
            os.system('ifconfig {0}'.format(if_name))

            # =====start radvd
            # os.system('radvd start')

            return f

    def _create_tun_read_thread(self):
        """
        Creates and starts the thread to read messages arriving from the
        TUN interface.
        """
        return TunReadThread(self.tun_if, self._v6_to_mesh_notif)
