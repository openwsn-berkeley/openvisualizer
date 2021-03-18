# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import random
import threading
import time
from typing import List

from openvisualizer.eventbus.eventbusclient import EventBusClient
from openvisualizer.motehandler.moteconnector.openparser import openparser

log = logging.getLogger('SerialTester')
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler())


class SerialTester(EventBusClient):
    DFLT_TESTPKT_LENGTH = 10  # number of bytes in a test packet
    DFLT_NUM_TESTPKT = 20  # number of test packets to send
    DFLT_TIMEOUT = 5  # timeout in second for getting a reply

    def __init__(self, mote_probe):

        # log
        super(SerialTester, self).__init__('SerialTester', registrations=[])
        log.debug("creating instance")

        # store params
        self.mote_probe = mote_probe
        self.moteProbeSerialPort = self.mote_probe.portname

        # local variables
        self.data_lock = threading.Lock()
        self.wait_flag = threading.Event()
        self.test_pkt_len = self.DFLT_TESTPKT_LENGTH
        self.num_test_pkt = self.DFLT_NUM_TESTPKT
        self.timeout = self.DFLT_TIMEOUT
        self.last_sent = []
        self.last_received = []
        self._reset_stats()

        # give this thread a name
        self.name = 'SerialTester@{0}'.format(self)

        # initialize parent
        self.mote_probe.send_to_parser = self._receive_data_from_mote_serial

    def _receive_data_from_mote_serial(self, data: List[int]):

        with self.data_lock:
            if chr(data[0]) == chr(openparser.OpenParser.SERFRAME_MOTE2PC_DATA):
                self.last_received = data[1 + 2 + 5:]  # type (1B), moteId (2B), ASN (5B)
                self.wait_flag.set()

    # ======================== public ==========================================

    # ===== setup test

    def set_test_pkt_length(self, new_length: int):
        assert type(new_length) == int
        self.test_pkt_len = new_length

    def set_num_test_pkt(self, new_num: int):
        assert type(new_num) == int
        self.num_test_pkt = new_num

    def set_timeout(self, new_timeout: int):
        assert type(new_timeout) == int
        self.timeout = new_timeout

    def get_stats(self):
        return self.stats.copy()

    def test(self):

        # reset stats
        self._reset_stats()

        # send packets and collect stats
        for pkt_num in range(self.num_test_pkt):

            # prepare random packet to send
            packet_to_send = [random.randint(0x00, 0xff) for _ in range(self.test_pkt_len)]

            # remember as last sent packet
            with self.data_lock:
                self.last_sent = packet_to_send[:]

            # send
            self.dispatch(
                signal='fromMoteConnector@' + self.moteProbeSerialPort,
                data=''.join(
                    [chr(openparser.OpenParser.SERFRAME_PC2MOTE_TRIGGERSERIALECHO)] + [chr(b) for b in packet_to_send]),
            )

            with self.data_lock:
                self.stats['numSent'] += 1

            # log
            log.debug('--- packet {0}'.format(pkt_num))
            log.debug('sent:     {0}'.format(self.format_list(self.last_sent)))

            # wait for answer
            self.wait_flag.clear()
            if self.wait_flag.wait(timeout=self.timeout):

                # log
                log.debug('received: {0}'.format(self.format_list(self.last_received)))

                # echo received
                with self.data_lock:
                    if self.last_received == self.last_sent:
                        self.stats['numOk'] += 1
                    else:
                        self.stats['numCorrupted'] += 1
            else:
                with self.data_lock:
                    self.stats['numTimeout'] += 1

    def _reset_stats(self):
        with self.data_lock:
            self.stats = {
                'numSent': 0,
                'numOk': 0,
                'numCorrupted': 0,
                'numTimeout': 0,
            }

    @staticmethod
    def format_list(lst: list):
        return '-'.join(['%02x' % b for b in lst])
