import logging

import pytest
from Crypto.Random.random import randint
from scapy.compat import raw
from scapy.layers.inet6 import IPv6, ICMPv6EchoRequest, ICMPv6EchoReply

from tests.conftest import is_my_icmpv6

log = logging.getLogger(__name__)

# =========================== defines ==========================================

NH_ICMPV6 = 58

LOCAL_ADDR = "cccc::2"


# ============================ tests ===========================================


@pytest.mark.parametrize("payload_len", range(100, 500, 100))
def test_basic_6lo_fragmentation(etun, mote_addr, payload_len):
    """ Test basic 6LoWPAN fragmentation and reassembly functions """

    ip = IPv6(src=LOCAL_ADDR, dst=mote_addr, hlim=64)
    id = randint(0, 65535)
    seq = randint(0, 65535)
    icmp = ICMPv6EchoRequest(id=id, seq=seq)
    pkt = ip / icmp

    payload = "".join([chr(randint(0, 255))] * payload_len)
    pkt.add_payload(payload)

    etun.write(list(bytearray(raw(pkt))))
    received = etun.read(dest=LOCAL_ADDR, timeout=15)

    timeout = True
    for recv_pkt in received:
        ipv6_pkt = IPv6(recv_pkt)
        if is_my_icmpv6(ipv6_pkt, mote_addr, LOCAL_ADDR, NH_ICMPV6):
            timeout = False
            icmp = ICMPv6EchoReply(raw(ipv6_pkt)[40:])
            # check if icmp headers match
            assert icmp.id == id
            assert icmp.seq == seq

    if timeout:
        # node to failed to respond with an ICMPv6 echo before timeout
        pytest.fail("Timeout on ICMPv6 Echo Response!")


# @pytest.mark.sim_only
def test_cleanup_on_fragment_loss(etun):
    """
    Test the cleanup function after a fragment loss
    """

    pass
