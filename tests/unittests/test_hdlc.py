#!/usr/bin/env python

import json
import logging
import logging.handlers
import random

import pytest

# noinspection PyUnresolvedReferences
import build_python_path
import openvisualizer.openvisualizer_utils as u
from openvisualizer.motehandler.moteprobe import openhdlc

# ============================ logging =========================================

LOGFILE_NAME = 'test_hdlc.log'

log = logging.getLogger('test_hdlc')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

logHandler = logging.handlers.RotatingFileHandler(LOGFILE_NAME, maxBytes=2 * 1024 * 1024, backupCount=5, mode='w')
logHandler.setFormatter(logging.Formatter("%(asctime)s [%(name)s:%(levelname)s] %(message)s"))
for loggerName in ['test_hdlc', 'OpenHdlc']:
    temp = logging.getLogger(loggerName)
    temp.setLevel(logging.DEBUG)
    temp.addHandler(logHandler)

# ============================ fixtures ========================================

RANDOM_FRAME = []
for frameLen in range(1, 100, 5):
    for run in range(100):
        frame = None
        while (not frame) or (frame in RANDOM_FRAME):
            frame = []
            for _ in range(frameLen):
                frame += [random.randint(0x00, 0xff)]
        RANDOM_FRAME.append(frame)
RANDOM_FRAME = [json.dumps(f) for f in RANDOM_FRAME]


@pytest.fixture(params=RANDOM_FRAME)
def random_frame(request):
    return request.param


# ============================ helpers =========================================

# ============================ tests ===========================================

def test_build_request_frame():
    if log.isEnabledFor(logging.DEBUG):
        log.debug("\n---------- test_buildRequestFrame")

    hdlc = openhdlc.OpenHdlc()

    # hdlcify
    frame_hdlcified = hdlc.hdlcify('\x53')
    log.debug("request frame: {0}".format(u.format_string_buf(frame_hdlcified)))


def test_dehdlcify_to_zero():
    log.debug("\n---------- test_dehdlcify_to_zero")

    hdlc = openhdlc.OpenHdlc()

    # hdlc_frame
    hdlc_frame = [0x53, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, 0xaa]
    hdlc_frame = ''.join([chr(b) for b in hdlc_frame])
    log.debug("hdlc_frame:      {0}".format(u.format_string_buf(hdlc_frame)))

    # hdlcify
    hdlc_frame = hdlc.hdlcify(hdlc_frame)
    log.debug("hdlcify: {0}".format(u.format_string_buf(hdlc_frame)))

    # remove flags
    hdlc_frame = hdlc_frame[1:-1]
    log.debug("no flags:   {0}".format(u.format_string_buf(hdlc_frame)))

    # calculate CRC
    crcini = 0xffff
    crc = crcini
    for c in hdlc_frame:
        tmp = crc ^ (ord(c))
        crc = (crc >> 8) ^ hdlc.FCS16TAB[(tmp & 0xff)]
        log.debug("after {0}, crc={1}".format(hex(ord(c)), hex(crc)))


def test_randdom_back_and_forth(random_frame):
    random_frame = json.loads(random_frame)
    random_frame = ''.join([chr(b) for b in random_frame])

    log.debug("\n---------- test_randdom_back_and_forth")

    hdlc = openhdlc.OpenHdlc()

    log.debug("random_frame:    {0}".format(u.format_string_buf(random_frame)))

    # hdlcify
    frame_hdlcified = hdlc.hdlcify(random_frame)
    log.debug("hdlcified:   {0}".format(u.format_string_buf(frame_hdlcified)))

    # dehdlcify
    frame_dehdlcified = hdlc.dehdlcify(frame_hdlcified)
    log.debug("dehdlcified:    {0}".format(u.format_string_buf(frame_dehdlcified)))

    assert frame_dehdlcified == random_frame
