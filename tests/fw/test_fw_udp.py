import logging
from random import randint, choice

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

@pytest.mark.parametrize("payload",
                         ["hello", "hello from", "hello from the", "hello from the other", "hello from the other side"])
def test_udp_echo(etun, mote_addr, payload):
    local_sport = randint(1024, 65355)

    ip = IPv6(src=LOCAL_ADDR, dst=mote_addr, hlim=64)
    udp = UDP(sport=local_sport, dport=UDP_ECHO_PORT)
    pkt = ip / udp

    pkt.add_payload(payload)

    _verify_test_answer(etun, pkt, mote_addr, local_sport)


@pytest.mark.xfail(reason='Invalid checksum')
def test_udp_checksum(etun, mote_addr):
    local_sport = randint(1024, 65355)

    ip = IPv6(src=LOCAL_ADDR, dst=mote_addr, hlim=64)
    udp = UDP(sport=local_sport, dport=UDP_ECHO_PORT)
    pkt = ip / udp

    payload = "test packet with wrong checksum"
    pkt.add_payload(payload)
    logger.info("Resetting checksum")
    pkt[UDP].chksum = 0

    _verify_test_answer(etun, pkt, mote_addr, local_sport)


@pytest.mark.parametrize("payload_len", range(0, 25))
def test_multiple_connection_echo(etun, mote_addr, payload_len):
    local_sport = randint(1024, 65355)

    address_list = ['CCCC::0002', 'CCCC::45ab:0009', 'CCCC::deaf', 'CCCC::beef']
    my_address = choice(address_list)

    ip = IPv6(src=my_address, dst=mote_addr, hlim=64)
    udp = UDP(sport=local_sport, dport=UDP_ECHO_PORT)
    pkt = ip / udp

    pkt.add_payload("".join([chr(randint(0, 255))] * payload_len))

    _verify_test_answer(etun, pkt, mote_addr, local_sport, my_address)


def _verify_test_answer(etun, pkt, mote_addr, local_sport, my_address=None):
    etun.write(list(bytearray(raw(pkt))))

    if my_address is None:
        addr = LOCAL_ADDR
    else:
        addr = my_address

    received = etun.read(dest=addr, timeout=15)

    timeout = True
    for recv_pkt in received:
        ipv6_pkt = IPv6(recv_pkt)
        if is_my_icmpv6(ipv6_pkt, mote_addr, addr, NH_UDP):
            timeout = False
            udp = UDP(raw(ipv6_pkt)[40:])
            assert udp.sport == UDP_ECHO_PORT
            assert udp.dport == local_sport

    if timeout:
        # node to failed to respond with an ICMPv6 echo before timeout
        pytest.fail("Timeout on UDP Echo!")
