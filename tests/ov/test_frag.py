#!/usr/bin/env python2

import logging.handlers
from random import randint, shuffle

import pytest
import scapy.layers.inet6 as ip6
import scapy.layers.sixlowpan as lo
from scapy.compat import raw

from openvisualizer.openlbr import sixlowpan_frag

# ============================ logging =========================================
LOGFILE_NAME = 'test_frag.log'

log = logging.getLogger('test_frag')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

log_handler = logging.handlers.RotatingFileHandler(LOGFILE_NAME, backupCount=5, mode='w')
log_handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s:%(levelname)s] %(message)s"))
for logger_name in ['test_frag', 'SixLowPanFrag']:
    temp = logging.getLogger(logger_name)
    temp.setLevel(logging.DEBUG)
    temp.addHandler(log_handler)

# ============================ defines =========================================

NUM_OF_TEST_VECTORS = 100
MAX_PAYLOAD_SIZE = 1280
MIN_PAYLOAD_SIZE = 0

# ============================ fixtures ========================================
TEST_VECTORS = []

for i in range(NUM_OF_TEST_VECTORS):
    # create an IPv6 packet with a random payload
    pkt = ip6.IPv6(src='bbbb::2', dst='bbbb::1', hlim=64)
    pkt.add_payload("".join([chr(randint(0, 255)) for j in range(randint(MIN_PAYLOAD_SIZE, MAX_PAYLOAD_SIZE))]))

    # fragment the packet
    fragment_list = lo.sixlowpan_fragment(pkt)

    for j in range(len(fragment_list)):
        fragment_list[j] = [ord(b) for b in raw(fragment_list[j])]

    pkt = [ord(b) for b in raw(pkt)]

    TEST_VECTORS.append((pkt, fragment_list))


@pytest.fixture(params=TEST_VECTORS)
def random_6lwp_fragments(request):
    return request.param


# ============================ tests ===========================================
def test_reassemble_fragments(random_6lwp_fragments):
    ip_pkt, frag_list = random_6lwp_fragments

    # fragments can arrive out-of-order
    shuffle(frag_list)

    log.debug("test_reassemble_fragments")

    assembler = sixlowpan_frag.Fragmentor()

    for frag in frag_list:
        result = assembler.do_reassemble(frag)

        if result is not None:
            assert result == ip_pkt


def test_fragment_packet(random_6lwp_fragments):
    ip_pkt, frag_list = random_6lwp_fragments

    log.debug("test_fragment_packet")

    fragmentor = sixlowpan_frag.Fragmentor()

    log.debug("Original packet (len: {}) -- {}".format(len(ip_pkt), ip_pkt))

    frags = [lo.SixLoWPAN("".join([chr(b) for b in f])) for f in fragmentor.do_fragment(ip_pkt)]
    log.debug(frags)

    reassembled = lo.sixlowpan_defragment(frags)

    if len(reassembled) == 0:
        # the packet was not fragmented
        log.debug(list(bytearray(raw(frags[0]))))
        log.debug(ip_pkt)
        assert ip_pkt == list(bytearray(raw(frags[0])))
    else:
        log.debug(list(bytearray(raw(reassembled[1]))))
        log.debug(ip_pkt)
        assert ip_pkt == list(bytearray(raw(reassembled[1])))
