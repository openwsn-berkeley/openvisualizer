#!/usr/bin/env python

import json
import logging.handlers

import pytest

import openvisualizer.openvisualizer_utils as u

# ============================ logging =========================================

LOGFILE_NAME = 'test_utils.log'

log = logging.getLogger('test_utils')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

logHandler = logging.handlers.RotatingFileHandler(LOGFILE_NAME, backupCount=5, mode='w')

logHandler.setFormatter(logging.Formatter("%(asctime)s [%(name)s:%(levelname)s] %(message)s"))
for loggerName in ['test_utils', 'OpenLbr', ]:
    temp = logging.getLogger(loggerName)
    temp.setLevel(logging.DEBUG)
    temp.addHandler(logHandler)

# ============================ defines =========================================

# ============================ fixtures ========================================

# ===== expected_buf2int

EXPECTED_BUF2INT = [
    #           buf          int
    json.dumps(([0x01, 0x02], 0x0102)),
    json.dumps(([0xaa, 0xbb], 0xaabb)),
]


@pytest.fixture(params=EXPECTED_BUF2INT)
def expected_buf2int(request):
    return request.param


# ===== expected_hex2buf

EXPECTED_HEX2BUF = [
    #           hex          buf
    json.dumps(('abcd', [0xab, 0xcd])),
    json.dumps(('', [])),
    json.dumps(('aa', [0xaa])),
]


@pytest.fixture(params=EXPECTED_HEX2BUF)
def expected_hex2buf(request):
    return request.param


# ===== expected_byteinverse

EXPECTED_BYTEINVERSE = [
    #           b    b_inverse
    json.dumps((0x01, 0x80)),
    json.dumps((0x02, 0x40)),
    json.dumps((0x04, 0x20)),
    json.dumps((0x81, 0x81)),
]


@pytest.fixture(params=EXPECTED_BYTEINVERSE)
def expected_byteinverse(request):
    return request.param


# ===== expected_format_ipv6

EXPECTED_FORMAT_IPv6 = [
    json.dumps(
        (
            [  # list
                0x01, 0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef,
                0xfe, 0xdc, 0xba, 0x98, 0x76, 0x54, 0x32, 0x10
            ],
            '123:4567:89ab:cdef:fedc:ba98:7654:3210'  # string
        )
    ),
    json.dumps(
        (
            [  # list
                0x01, 0x23, 0x45, 0x67, 0x00, 0x00, 0xcd, 0xef,
                0xfe, 0xdc, 0xba, 0x98, 0x76, 0x54, 0x32, 0x10
            ],
            '123:4567:0:cdef:fedc:ba98:7654:3210'  # string
        )
    ),
    json.dumps(
        (
            [  # list
                0x01, 0x23, 0x45, 0x67, 0x00, 0x00, 0x00, 0x00,
                0xfe, 0xdc, 0xba, 0x98, 0x76, 0x54, 0x32, 0x10
            ],
            '123:4567:0:0:fedc:ba98:7654:3210'  # string
        )
    ),
]


@pytest.fixture(params=EXPECTED_FORMAT_IPv6)
def expected_format_ipv6(request):
    return request.param


# ============================ helpers =========================================

# ============================ tests ===========================================

def test_buf2int(expected_buf2int):
    (exp_buf, exp_int) = json.loads(expected_buf2int)

    assert u.buf2int(exp_buf) == exp_int


def test_hex2buf(expected_hex2buf):
    (exp_hex, exp_buf) = json.loads(expected_hex2buf)
    exp_hex = str(exp_hex)

    assert u.hex2buf(exp_hex) == exp_buf


def test_byteinverse(expected_byteinverse):
    (b, b_inverse) = json.loads(expected_byteinverse)

    assert u.byteinverse(b) == b_inverse
    assert u.byteinverse(b_inverse) == b


def test_format_ipv6_addr(expected_format_ipv6):
    (ipv6_list, ipv6_string) = json.loads(expected_format_ipv6)

    log.info(ipv6_string)

    assert u.formatIPv6Addr(ipv6_list) == ipv6_string
