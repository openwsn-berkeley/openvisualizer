import logging
from random import randint

import pytest
from scapy.compat import raw
from scapy.layers.inet import UDP
from scapy.layers.inet6 import IPv6

from tests.conftest import is_my_icmpv6

logger = logging.getLogger(__name__)

# =========================== defines ==========================================
LOCAL_ADDR = 'cccc::2'
UDP_ECHO_PORT = 7

NH_UDP = 17


# ============================ tests ===========================================

@pytest.mark.parametrize("payload_len", range(10, 60, 10))
def test_udp_echo(etun, mote_addr, payload_len):
    local_sport = randint(1024, 65355)

    ip = IPv6(src=LOCAL_ADDR, dst=mote_addr, hlim=64)
    udp = UDP(sport=local_sport, dport=UDP_ECHO_PORT)
    pkt = ip / udp

    payload = "".join([chr(randint(0, 255))] * payload_len)
    pkt.add_payload(payload)

    etun.write(list(bytearray(raw(pkt))))
    received = etun.read(dest=LOCAL_ADDR, timeout=5)

    timeout = True
    for recv_pkt in received:
        ipv6_pkt = IPv6(recv_pkt)
        if is_my_icmpv6(ipv6_pkt, mote_addr, LOCAL_ADDR, NH_UDP):
            timeout = False
            udp = UDP(raw(ipv6_pkt)[40:])
            assert udp.sport == UDP_ECHO_PORT
            assert udp.dport == local_sport

    if timeout:
        # node to failed to respond with an ICMPv6 echo before timeout
        pytest.fail("Timeout on ICMPv6 Echo Response!")


@pytest.mark.xfail(reason='Invalid checksum')
def test_udp_checksum(etun, mote_addr):
    local_sport = randint(1024, 65355)

    ip = IPv6(src=LOCAL_ADDR, dst=mote_addr, hlim=64)
    udp = UDP(sport=local_sport, dport=UDP_ECHO_PORT)
    pkt = ip / udp

    payload = "".join([chr(randint(0, 255))] * 30)
    pkt.add_payload(payload)
    logger.info("Reseting checksum")
    pkt[UDP].chksum = 0

    etun.write(list(bytearray(raw(pkt))))
    received = etun.read(dest=LOCAL_ADDR, timeout=10)

    timeout = True
    for recv_pkt in received:
        ipv6_pkt = IPv6(recv_pkt)
        if is_my_icmpv6(ipv6_pkt, mote_addr, LOCAL_ADDR, NH_UDP):
            timeout = False
            udp = UDP(raw(ipv6_pkt)[40:])
            assert udp.sport == UDP_ECHO_PORT
            assert udp.dport == local_sport

    if timeout:
        # node to failed to respond with an ICMPv6 echo before timeout
        pytest.fail("Timeout on ICMPv6 Echo Response!")
