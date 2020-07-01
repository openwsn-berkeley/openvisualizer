# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import re
import threading
import traceback

import verboselogs

verboselogs.install()

log = logging.getLogger('Utils')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

FCS16TAB = (
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
    0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
    0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
    0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
    0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
    0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
    0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
    0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
    0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
    0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
    0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
    0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
    0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
    0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
    0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
    0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
    0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
    0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
    0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
    0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
    0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
    0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
    0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0,
)


def buf2int(buf):
    """
    Converts some consecutive bytes of a buffer into an integer.
    Big-endianness is assumed.

    :param buf: Byte array.
    """

    return_val = 0
    for i in range(len(buf)):
        return_val += buf[i] << (8 * (len(buf) - i - 1))
    return return_val


# ===== formatting

def format_string_buf(buf):
    return '({0:>2}B) {1}'.format(len(buf), '-'.join(["%02x" % ord(b) for b in buf]))


def format_buf(buf):
    """
    Format a bytelist into an easy-to-read string. For example:

    ``[0xab,0xcd,0xef,0x00] -> '(4B) ab-cd-ef-00'``
    """

    return '({0:>2}B) {1}'.format(len(buf), '-'.join(["%02x" % b for b in buf]))


def format_ipv6_addr(addr):
    # group by 2 bytes
    addr = [buf2int(addr[2 * i:2 * i + 2]) for i in range(len(addr) / 2)]
    return ':'.join(["%x" % b for b in addr])


def format_addr(addr):
    return '-'.join(["%02x" % b for b in addr])


def format_thread_list():
    return '\nActive threads ({0})\n   {1}'.format(
        threading.activeCount(),
        '\n   '.join([t.name for t in threading.enumerate()]),
    )


# ===== parsing

def hex2buf(s):
    """
    Convert a string of hex caracters into a byte list. For example:

    ``'abcdef00' -> [0xab,0xcd,0xef,0x00]``

    :param s: The string to convert

    :returns: A list of integers, each element in [0x00..0xff].
    """
    assert type(s) == str
    assert len(s) % 2 == 0

    return_val = []

    for i in range(len(s) / 2):
        real_idx = i * 2
        return_val.append(int(s[real_idx:real_idx + 2], 16))

    return return_val


# ===== CRC

def calculate_crc(payload):
    checksum = [0x00] * 2

    checksum = _one_complement_sum(payload, checksum)

    checksum[0] ^= 0xFF
    checksum[1] ^= 0xFF

    checksum[0] = int(checksum[0])
    checksum[1] = int(checksum[1])

    return checksum


def calculate_pseudo_header_crc(src, dst, length, nh, payload):
    """
    See these references:

    * http://www-net.cs.umass.edu/kurose/transport/UDP.html
    * http://tools.ietf.org/html/rfc1071
    * http://en.wikipedia.org/wiki/User_Datagram_Protocol#IPv6_PSEUDO-HEADER
    """

    checksum = [0x00] * 2

    # compute pseudo header crc
    checksum = _one_complement_sum(src, checksum)
    checksum = _one_complement_sum(dst, checksum)
    checksum = _one_complement_sum(length, checksum)
    checksum = _one_complement_sum(nh, checksum)
    checksum = _one_complement_sum(payload, checksum)

    checksum[0] ^= 0xFF
    checksum[1] ^= 0xFF

    checksum[0] = int(checksum[0])
    checksum[1] = int(checksum[1])

    return checksum


def _one_complement_sum(field, checksum):
    res = 0xFFFF & (checksum[0] << 8 | checksum[1])
    i = len(field)
    while i > 1:
        res += 0xFFFF & (field[-i] << 8 | (field[-i + 1]))
        i -= 2
    if i:
        res += (0xFF & field[-1]) << 8
    while res >> 16:
        res = (res & 0xFFFF) + (res >> 16)

    checksum[0] = (res >> 8) & 0xFF
    checksum[1] = res & 0xFF

    return checksum


def byteinverse(b):
    # TODO: speed up through lookup table
    rb = 0
    for pos in range(8):
        if b & (1 << pos) != 0:
            bitval = 1
        else:
            bitval = 0
        rb |= bitval << (7 - pos)
    return rb


def calculate_fcs(rpayload):
    payload = []
    for b in rpayload:
        payload += [byteinverse(b)]

    crc = 0x0000
    for b in payload:
        crc = ((crc << 8) & 0xffff) ^ FCS16TAB[((crc >> 8) ^ b) & 0xff]

    return_val = [
        byteinverse(crc >> 8),
        byteinverse(crc & 0xff),
    ]
    return return_val


def format_critical_message(error):
    return_val = []
    return_val += ['Error:']
    return_val += [str(error)]
    return_val += ['\ncall stack:\n']
    return_val += [traceback.format_exc()]
    return_val += ['\n']
    return_val = '\n'.join(return_val)
    return return_val


def format_crash_message(thread_name, error):
    return_val = []
    return_val += ['\n']
    return_val += ['======= crash in {0} ======='.format(thread_name)]
    return_val += [format_critical_message(error)]
    return_val = '\n'.join(return_val)
    return return_val


def extract_component_codes(fw_definitions_path):
    # find component codes in opendefs.h
    log.verbose("extracting firmware component names")

    codes_found = {}
    for line in open(fw_definitions_path, 'r'):
        m = re.search(' *COMPONENT_([^ .]*) *= *(.*), *', line)
        if m:
            name = m.group(1)
            try:
                code = int(m.group(2), 16)
            except ValueError:
                log.error("component '{}' - {} is not a hex number".format(name, m.group(2)))
            else:
                log.debug("extracted component '{}' with code {}".format(name, code))
                codes_found[code] = name

    return codes_found


def extract_log_descriptions(fw_definitions_path):
    # find error codes in opendefs.h
    log.verbose("extracting firmware log descriptions.")

    codes_found = {}
    for line in open(fw_definitions_path, 'r'):
        m = re.search(' *ERR_.* *= *([xXA-Fa-f0-9]*), *// *(.*)', line)
        if m:
            desc = m.group(2).strip()
            try:
                code = int(m.group(1), 16)
            except ValueError:
                log.error("log description '{}' - {} is not a hex number".format(desc, m.group(2)))
            else:
                log.debug("extracted log description '{}' with code {}".format(desc, code))
                codes_found[code] = desc

    return codes_found


def extract_6top_rcs(fw_6top_definitions_path):
    # find sixtop return codes in sixtop.h
    log.verbose("extracting 6top return codes.")

    codes_found = {}
    for line in open(fw_6top_definitions_path, 'r'):
        m = re.search(' *#define *IANA_6TOP_RC_([^ .]*) *([xXA-Za-z0-9]+) *// *([^ .]*).*', line)
        if m:
            name = m.group(3)
            try:
                code = int(m.group(2), 16)
            except ValueError:
                log.error("return code '{}': {} is not a hex number".format(name, m.group(2)))
            else:
                log.debug("extracted 6top RC '{}' with code {}".format(name, code))
                codes_found[code] = name

    return codes_found


def extract_6top_states(fw_6top_definitions_path):
    # find sixtop state codes in sixtop.h
    log.verbose("extracting 6top states.")

    codes_found = {}
    for line in open(fw_6top_definitions_path, 'r'):
        m = re.search(' *SIX_STATE_([^ .]*) *= *([^ .]*), *', line)
        if m:
            name = m.group(1)
            try:
                code = int(m.group(2), 16)
            except ValueError:
                log.error("state '{}' - {} is not a hex number".format(name, m.group(2)))
            else:
                log.debug("extracted 6top state '{}' with code {}".format(name, code))
                codes_found[code] = name

    return codes_found
