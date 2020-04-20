#!/usr/bin/env python2

"""
This is a functional test which verify the correct behavior of the OpenTun. The test involves 3 components:
- the opentun element under test, which sits on the eventbus.
- the ReadThread, implemented in this test module, which listens for ICMPv6 echo request packets, and answers with an
  echo reply packet.
- the WriteThread, implemented in this test module, which periodically sends an echo reply. The expected behavior is
  that, for each echo request sent by the writeThread, an echo reply is received by the readThread.

Run this test by double-clicking on this file, then pinging any address in the prefix of your tun interface
(e.g. 'ping bbbb::5').
"""

import logging
import sys
import threading
import time

# noinspection PyUnresolvedReferences
import build_python_path
import openvisualizer.openvisualizer_utils as u
from openvisualizer.eventbus.eventbusclient import EventBusClient
from openvisualizer.opentun import opentun

log = logging.getLogger('test_opentun')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


# ============================ defines =========================================
# ============================ helpers =========================================


def carry_around_add(a, b):
    """ Helper function for checksum calculation. """
    c = a + b
    return (c & 0xffff) + (c >> 16)


def checksum(byte_list):
    """
    Calculate the checksum over a byte list. This is the checksum calculation used in e.g. the ICMPv6 header.

    :return the checksum, a 2-byte integer.
    """
    s = 0
    for i in range(0, len(byte_list), 2):
        w = byte_list[i] + (byte_list[i + 1] << 8)
        s = carry_around_add(s, w)
    return ~s & 0xffff


# ============================ threads =========================================

class ReadThread(EventBusClient):
    """
    Thread which continously reads input from a TUN interface. If that input is an IPv4 or IPv6 echo request
    (a "ping" command) issued to any IP address in the virtual network behind the TUN interface, this thread
    answers with the appropriate echo reply.
    """

    def __init__(self):

        # store params

        # initialize parent class
        super(ReadThread, self).__init__(
            name='OpenTun',
            registrations=[
                {
                    'sender': self.WILDCARD,
                    'signal': 'v6ToMesh',
                    'callback': self._v6_to_mesh_notif
                }
            ]
        )

    # ======================== public ==========================================

    # ======================== private =========================================

    def _v6_to_mesh_notif(self, sender, signal, data):

        p = data

        assert (p[0] & 0xf0) == 0x60

        if p[6] == 0x3a:
            # ICMPv6

            if p[40] == 0x80:
                # IPv6 echo request

                # print
                print 'Received IPv6 echo request'

                # create echo reply
                echo_reply = self._create_ipv6_echo_reply(p)

                # send over interface
                self.dispatch(
                    signal='v6ToInternet',
                    data=echo_reply
                )

                # print
                print 'Transmitted IPv6 echo reply'

            elif p[40] == 0x81:

                # print
                print 'Received IPv6 echo reply'

    def _create_ipv6_echo_reply(self, echo_request):

        # invert addresses, change "echo request" type to "echo reply"
        echo_reply = echo_request[:8] + echo_request[24:40] + echo_request[8:24] + [129] + echo_request[41:]

        # recalculate checksum
        pseudo = []
        pseudo += echo_request[24:40]  # source address
        pseudo += echo_request[8:24]  # destination address
        pseudo += [0x00] * 3 + [len(echo_request[40:])]  # upper-layer packet length
        pseudo += [0x00] * 3  # zero
        pseudo += [58]  # next header
        pseudo += echo_request[40:]  # ICMPv6 header+payload

        pseudo[40] = 129  # ICMPv6 type = echo reply
        pseudo[42] = 0x00  # reset CRC for calculation
        pseudo[43] = 0x00  # reset CRC for calculation

        crc = checksum(pseudo)

        echo_reply[42] = (crc & 0x00ff) >> 0
        echo_reply[43] = (crc & 0xff00) >> 8

        return echo_reply


class WriteThread(threading.Thread):
    """ Thread with periodically sends IPv6 echo requests. """

    SLEEP_PERIOD = 1

    def __init__(self, dispatch):

        # store params
        self.dispatch = dispatch
        self.go_on = True

        # local variables

        # initialize parent
        super(WriteThread, self).__init__()

        # give this thread a name
        self.name = 'writeThread'

        # start myself
        self.start()

    def run(self):
        try:
            while self.go_on:
                # sleep a bit
                time.sleep(self.SLEEP_PERIOD)

                # create an echo request
                echo_request = self._create_ipv6_echo_request()

                # transmit
                self.dispatch(signal='v6ToInternet', data=echo_request)
        except Exception as err:
            err_msg = u.format_crash_message(self.name, err)
            log.error(err_msg)
            sys.exit(1)

    def close(self):
        self.go_on = False

    # ======================== public ==========================================

    # ======================== private =========================================

    def _create_ipv6_echo_request(self):
        """ brief Create an IPv6 echo request. """

        echo_request = []

        # IPv6 header
        echo_request += [0x60, 0x00, 0x00, 0x00]  # ver, TF
        echo_request += [0x00, 40]  # length
        echo_request += [58]  # Next header (58==ICMPv6)
        echo_request += [128]  # HLIM
        # source
        echo_request += [0xbb, 0xbb, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x05]
        # destination
        echo_request += [0xbb, 0xbb, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01]

        # ICMPv6 header
        echo_request += [128]  # type (128==echo request)
        echo_request += [0]  # code
        echo_request += [0x00, 0x00]  # Checksum (to be filled out later)
        echo_request += [0x00, 0x04]  # Identifier
        echo_request += [0x00, 0x12]  # Sequence

        # ICMPv6 payload
        echo_request += [ord('a') + b for b in range(32)]

        # calculate ICMPv6 checksum
        pseudo = []
        pseudo += echo_request[24:40]  # source address
        pseudo += echo_request[8:24]  # destination address
        pseudo += [0x00] * 3 + [len(echo_request[40:])]  # upper-layer packet length
        pseudo += [0x00] * 3  # zero
        pseudo += [58]  # next header
        pseudo += echo_request[40:]  # ICMPv6 header+payload

        crc = checksum(pseudo)

        echo_request[42] = (crc & 0x00ff) >> 0
        echo_request[43] = (crc & 0xff00) >> 8

        return echo_request


# ============================ main ============================================

def main():
    # === create eventBus client elements

    tun_if = opentun.OpenTun.create(opentun=True)

    read_thread = ReadThread()
    write_thread = WriteThread(read_thread.dispatch)

    # === wait for Enter to stop

    raw_input("\nPress enter to stop...\n")
    print 'Closing...'
    write_thread.close()
    tun_if.close()


if __name__ == '__main__':
    main()
