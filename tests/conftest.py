import errno
import logging
import os
import select
import socket
import struct
import time
import xmlrpclib
from fcntl import ioctl
from subprocess import Popen

import pytest
from ipaddr import IPv6Address
from scapy.layers.inet6 import IPv6

log = logging.getLogger(__name__)

# ============================ helpers & setup code =============================

HOST = "localhost"
PORT = 9000
PREFIX = "bbbb:0:0:0:1415:92cc:0:"

ADDRESSES = []

# Connect to a running instance of openv-server and retrieve the addresses of the motes in the network
url = 'http://{}:{}'.format(HOST, str(PORT))
try:
    rpc_server = xmlrpclib.ServerProxy(url)
    mote_ids = rpc_server.get_mote_dict().keys()
except socket.error as err:
    if errno.ECONNREFUSED:
        log.warning(
            "If you are trying to run a firmware test you need a running instance of openv-server with the options "
            "'--sim=<x> --simtopo=linear --root', otherwise you can ignore this warning")
    else:
        log.error(err)
else:
    try:
        root = ''.join(['%02x' % b for b in rpc_server.get_dagroot()])
    except TypeError:
        pytest.exit("Openvisualizer has no dagroot configured!")
    else:
        mote_ids.remove(root)
    ADDRESSES.extend([PREFIX + str(int(id)) for id in mote_ids])


def is_my_icmpv6(ipv6_pkt, his_address, my_address, next_header):
    if IPv6Address(ipv6_pkt.src).exploded == IPv6Address(his_address).exploded and \
            IPv6Address(ipv6_pkt.dst).exploded == IPv6Address(my_address).exploded and \
            ipv6_pkt.nh == next_header:
        return True
    else:
        return False


class TunInterface:
    VIRTUAL_TUN_ID = [0x00, 0x00, 0x86, 0xdd]

    IFF_TUN = 0x0001
    TUN_SET_IFF = 0x400454ca
    ETHERNET_MTU = 1500

    def __init__(self, prefix='cccc::', host='1'):
        self.ipv6_prefix = prefix
        self.ipv6_host = host

        try:
            self.tun_iff = self._create_tun_if()
        except IOError:
            pytest.exit("Opening a TUN interface requires sudo privileges")

    def _create_tun_if(self):
        return_val = os.open("/dev/net/tun", os.O_RDWR)
        ifs = ioctl(return_val, self.TUN_SET_IFF, struct.pack("16sH", "tun%d", self.IFF_TUN))
        self.if_name = ifs.decode('UTF-8')[:16].strip("\x00")

        os.system('ip tuntap add dev ' + self.if_name + ' mode tun user root')
        os.system('ip link set ' + self.if_name + ' up')
        os.system('ip -6 addr add ' + self.ipv6_prefix + self.ipv6_host + '/64 dev ' + self.if_name)
        os.system('ip -6 addr add fe80::' + self.ipv6_host + '/64 dev ' + self.if_name)

        return return_val

    def read(self, dest=None, count=1, timeout=0):
        received = []
        while True:
            readable, _, _ = select.select([self.tun_iff], [], [], timeout)
            if len(readable) > 0:
                pkt_byte = os.read(self.tun_iff, self.ETHERNET_MTU)[4:]

                if IPv6(pkt_byte).version == 6:
                    if dest is not None:
                        if IPv6Address(IPv6(pkt_byte).dst).exploded == IPv6Address(dest).exploded:
                            received.append(pkt_byte)
                    else:
                        received.append(pkt_byte)

                if 1 <= count == len(received):
                    break
            else:
                break

        return received

    def write(self, data):
        if not self.tun_iff:
            return

        # add tun header and convert to bytes
        data = self.VIRTUAL_TUN_ID + data
        data = "".join([chr(b) for b in data])

        try:
            # write over tuntap interface
            os.write(self.tun_iff, data)
        except Exception as err:
            print("write failed")


# ============================= fixtures ======================================

@pytest.fixture(params=ADDRESSES)
def mote_addr(request):
    return request.param


@pytest.fixture(scope="session")
def etun():
    return TunInterface()


@pytest.fixture()
def server():
    arguments = ['openv-server', '--sim=2', '--no-boot']
    server_proc = Popen(arguments, shell=False)
    time.sleep(2)
    yield server_proc
    server_proc.terminate()


@pytest.fixture()
def server_booted():
    arguments = ['openv-server', '--sim=2']
    server_proc = Popen(arguments, shell=False)
    time.sleep(2)
    yield server_proc
    server_proc.terminate()
