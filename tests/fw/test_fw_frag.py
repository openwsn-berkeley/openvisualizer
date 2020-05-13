import logging
import xmlrpclib

import pytest
from Crypto.Random.random import randint
from ipaddr import IPv6Address
from scapy.compat import raw
from scapy.layers.inet6 import IPv6, ICMPv6EchoRequest, ICMPv6EchoReply

log = logging.getLogger(__name__)

# =========================== defines ==========================================

NH_ICMPV6 = 58
LOCAL_ADDR = "cccc::2"
ADDRESSES = []
HOST = "localhost"
PORT = 9000
PREFIX = "bbbb:0:0:0:1415:92cc:0:"

# ============================ helpers & setup code =============================

url = 'http://{}:{}'.format(HOST, str(PORT))
rpc_server = xmlrpclib.ServerProxy(url)
mote_ids = rpc_server.get_mote_dict().keys()
try:
    root = ''.join(['%02x' % b for b in rpc_server.get_dagroot()])
except TypeError:
    pytest.exit("Openvisualizer has no dagroot configured!")
else:
    mote_ids.remove(root)
ADDRESSES.extend([PREFIX + str(int(id)) for id in mote_ids])
log.info("Running {} with mote addresses: {}".format(__name__, ADDRESSES))


# =========================== fixtures =========================================

@pytest.fixture(params=ADDRESSES)
def mote_addr(request):
    return request.param


def is_my_icmpv6(ipv6_pkt, his_address, my_address):
    if IPv6Address(ipv6_pkt.src).exploded == IPv6Address(his_address).exploded and \
            IPv6Address(ipv6_pkt.dst).exploded == IPv6Address(my_address).exploded and \
            ipv6_pkt.nh == NH_ICMPV6:
        return True
    else:
        return False


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
    received = etun.read(dest=LOCAL_ADDR, timeout=10)

    timeout = True
    for recv_pkt in received:
        ipv6_pkt = IPv6(recv_pkt)
        if is_my_icmpv6(ipv6_pkt, mote_addr, LOCAL_ADDR):
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
