# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging

from openvisualizer.utils import buf2int, hex2buf

log = logging.getLogger('SixLowPanFrag')
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())


# ============================ parameters ======================================

class ReassembleEntry(object):
    def __init__(self, wanted, received, frag):
        self.total_bytes = wanted
        self.recvd_bytes = received
        self.fragments = frag


class Fragmentor(object):
    """
    Class which performs fragmentation and reassembly of 6LoWPAN packets for transport of IEEE 802.15.4 networks.

    This class implements the following RFCs;

    * *https://tools.ietf.org/html/rfc4944*
      Transmission of IPv6 Packets over IEEE 802.15.4 Networks.
    """

    FRAG1_DISPATCH = 0xC0
    FRAGN_DISPATCH = 0xE0

    FRAG_DISPATCH_MASK = 0xF8
    FRAG_SIZE_MASK = 0x7FF

    # If L2 security is not active in the network we can use up to 96 bytes of payload per fragment.
    # Since openvisualizer is not aware of the security configuration of the network, we use by default a smaller
    # fragment payload size.
    MAX_FRAGMENT_SIZE = 80
    FRAG1_HDR_SIZE = 4
    FRAGN_HDR_SIZE = 5

    def __init__(self, tag=1):
        self.reassemble_buffer = dict()

        self.datagram_tag = tag

    def do_reassemble(self, lowpan_pkt):
        reassembled_pkt = None

        # parse fragmentation header
        dispatch = lowpan_pkt[0] & self.FRAG_DISPATCH_MASK
        datagram_size = buf2int(lowpan_pkt[:2]) & self.FRAG_SIZE_MASK

        if dispatch not in [self.FRAG1_DISPATCH, self.FRAGN_DISPATCH]:
            return lowpan_pkt

        # extract fragmentation tag
        datagram_tag = buf2int(lowpan_pkt[2:4])

        if dispatch == self.FRAG1_DISPATCH:
            payload = lowpan_pkt[4:]
            offset = 0
        else:
            payload = lowpan_pkt[5:]
            offset = lowpan_pkt[4]

        if datagram_tag in self.reassemble_buffer:
            entry = self.reassemble_buffer[datagram_tag]
            entry.recvd_bytes += len(payload)
            entry.fragments.append((offset, payload))
        else:
            new_entry = ReassembleEntry(datagram_size, len(payload), [(offset, payload)])
            self.reassemble_buffer[datagram_tag] = new_entry

        # check if we can reassemble
        num_of_frags = 0
        used_tag = None
        for tag, entry in self.reassemble_buffer.items():
            if entry.total_bytes == entry.recvd_bytes:
                frags = sorted(entry.fragments, key=lambda frag: frag[0])
                used_tag = tag
                num_of_frags = len(frags)
                reassembled_pkt = []

                for frag in frags:
                    reassembled_pkt.extend(frag[1])
                break

        if used_tag is not None:
            del self.reassemble_buffer[used_tag]

        if reassembled_pkt is not None:
            log.success("[GATEWAY] Reassembled {} frags with tag {} into an IPv6 packet of size {}".format(
                num_of_frags, used_tag, len(reassembled_pkt)))

        return reassembled_pkt

    def do_fragment(self, ip6_pkt):
        fragment_list = []
        original_length = len(ip6_pkt)

        if len(ip6_pkt) <= self.MAX_FRAGMENT_SIZE + self.FRAGN_HDR_SIZE:
            return [ip6_pkt]

        while len(ip6_pkt) > 0:
            frag_header = []
            fragment = []

            datagram_tag = hex2buf("{:04x}".format(self.datagram_tag))

            if len(ip6_pkt) > self.MAX_FRAGMENT_SIZE:
                frag_len = self.MAX_FRAGMENT_SIZE
            else:
                frag_len = len(ip6_pkt)

            if len(fragment_list) == 0:
                # first fragment
                dispatch_size = hex2buf("{:02x}".format((self.FRAG1_DISPATCH << 8) | original_length))
                frag_header.extend(dispatch_size)
                frag_header.extend(datagram_tag)
            else:
                # subsequent fragment
                dispatch_size = hex2buf("{:02x}".format((self.FRAGN_DISPATCH << 8) | original_length))
                offset = [len(fragment_list) * (self.MAX_FRAGMENT_SIZE / 8)]
                frag_header.extend(dispatch_size)
                frag_header.extend(datagram_tag)
                frag_header.extend(offset)

            fragment.extend(frag_header)
            fragment.extend(ip6_pkt[:frag_len])

            fragment_list.append(fragment)

            ip6_pkt = ip6_pkt[frag_len:]

        # increment the tag for the new set of fragments
        self.datagram_tag += 1

        log.info("[GATEWAY] Fragmenting incoming IPv6 packet (size: {}) into {} fragments with tag {}".format(
            original_length, len(fragment_list), self.datagram_tag - 1))

        return fragment_list
