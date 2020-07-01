# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import random
import threading

from openvisualizer.eventbus.eventbusclient import EventBusClient
from openvisualizer.motehandler.moteconnector.openparser import openparser

log = logging.getLogger('SerialTester')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


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
        self.data_lock = threading.RLock()
        self.test_pkt_len = self.DFLT_TESTPKT_LENGTH
        self.num_test_pkt = self.DFLT_NUM_TESTPKT
        self.timeout = self.DFLT_TIMEOUT
        self.trace_cb = None
        self.busy_testing = False
        self.last_sent = []
        self.last_received = []
        self.wait_for_reply = threading.Event()
        self._reset_stats()

        # give this thread a name
        self.name = 'SerialTester@{0}'.format(self)

        # initialize parent
        self.mote_probe.send_to_parser = self._receive_data_from_mote_serial

    def quit(self):
        self.go_on = False

    # ======================== public ==========================================

    def _receive_data_from_mote_serial(self, data):

        # handle data
        if chr(data[0]) == chr(openparser.OpenParser.SERFRAME_MOTE2PC_DATA):
            # don't handle if I'm not testing
            with self.data_lock:
                if not self.busy_testing:
                    return
            with self.data_lock:
                self.last_received = data[1 + 2 + 5:]  # type (1B), moteId (2B), ASN (5B)
                # wake up other thread
                self.wait_for_reply.set()

    # ===== setup test

    def set_test_pkt_length(self, new_length):
        assert type(new_length) == int
        with self.data_lock:
            self.test_pkt_len = new_length

    def set_num_test_pkt(self, new_num):
        assert type(new_num) == int
        with self.data_lock:
            self.num_test_pkt = new_num

    def set_timeout(self, new_timeout):
        assert type(new_timeout) == int
        with self.data_lock:
            self.timeout = new_timeout

    def set_trace(self, new_trace_cb):
        assert (callable(new_trace_cb)) or (new_trace_cb is None)
        with self.data_lock:
            self.trace_cb = new_trace_cb

    # ===== run test

    def test(self, blocking=True):
        if blocking:
            self._run_test()
        else:
            threading.Thread(target=self._run_test).start()

    # ===== get test results

    def get_stats(self):
        with self.data_lock:
            return_val = self.stats.copy()
        return return_val

    # ======================== private =========================================

    def _run_test(self):

        # I'm testing
        with self.data_lock:
            self.busy_testing = True

        # gather test parameters
        with self.data_lock:
            test_pkt_len = self.test_pkt_len
            num_test_pkt = self.num_test_pkt
            timeout = self.timeout

        # reset stats
        self._reset_stats()

        # send packets and collect stats
        for pkt_num in range(num_test_pkt):

            # prepare random packet to send
            packet_to_send = [random.randint(0x00, 0xff) for _ in range(test_pkt_len)]

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
            self._log('--- packet {0}'.format(pkt_num))
            self._log('sent:     {0}'.format(self.format_list(self.last_sent)))

            # wait for answer
            self.wait_for_reply.clear()
            if self.wait_for_reply.wait(timeout):

                # log
                self._log('received: {0}'.format(self.format_list(self.last_received)))

                # echo received
                with self.data_lock:
                    if self.last_received == self.last_sent:
                        self.stats['numOk'] += 1
                    else:
                        self.stats['numCorrupted'] += 1
                        self._log('!! corrupted.')
            else:
                # timeout
                with self.data_lock:
                    self.stats['numTimeout'] += 1
                    self._log('!! timeout.')

        # I'm not testing
        with self.data_lock:
            self.busy_testing = False

    def _log(self, msg):
        if log.isEnabledFor(logging.DEBUG):
            log.debug(msg)
        with self.data_lock:
            if self.trace_cb:
                self.trace_cb(msg)

    def _reset_stats(self):
        with self.data_lock:
            self.stats = {
                'numSent': 0,
                'numOk': 0,
                'numCorrupted': 0,
                'numTimeout': 0,
            }

    def format_list(self, lst):
        return '-'.join(['%02x' % b for b in lst])
