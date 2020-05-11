#!/usr/bin/env python2

import json
import logging
import logging.handlers

import pytest

from openvisualizer.rpl import topology
from openvisualizer.rpl.sourceroute import SourceRoute

# ============================ logging =========================================
from openvisualizer.utils import format_addr

LOGFILE_NAME = 'test_sourceroute.log'

log = logging.getLogger('test_sourceRoute')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

log_handler = logging.handlers.RotatingFileHandler(LOGFILE_NAME, backupCount=5, mode='w')
log_handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s:%(levelname)s] %(message)s"))
for loggerName in ['test_sourceRoute', 'SourceRoute', ]:
    temp = logging.getLogger(loggerName)
    temp.setLevel(logging.DEBUG)
    temp.addHandler(log_handler)

# ============================ defines =========================================

MOTE_A = [0xaa] * 8
MOTE_B = [0xbb] * 8
MOTE_C = [0xcc] * 8
MOTE_D = [0xdd] * 8

# ============================ fixtures ========================================

EXPECTED_SOURCE_ROUTE = [
    json.dumps((MOTE_B, [MOTE_B, MOTE_A])),
    json.dumps((MOTE_C, [MOTE_C, MOTE_B, MOTE_A])),
    json.dumps((MOTE_D, [MOTE_D, MOTE_C, MOTE_B, MOTE_A])),
]


@pytest.fixture(params=EXPECTED_SOURCE_ROUTE)
def expected_source_route(request):
    return request.param


# ============================ helpers =========================================

# ============================ tests ===========================================

def test_source_route(expected_source_route):
    """
    This tests the following topology

    MOTE_A <- MOTE_B <- MOTE_C <- MOTE_D
    """

    source_route = SourceRoute()
    _ = topology.Topology()

    source_route.dispatch(signal='updateParents', data=(tuple(MOTE_B), [MOTE_A]))
    source_route.dispatch(signal='updateParents', data=(tuple(MOTE_C), [MOTE_B]))
    source_route.dispatch(signal='updateParents', data=(tuple(MOTE_D), [MOTE_C]))

    expected_destination = json.loads(expected_source_route)[0]
    expected_route = json.loads(expected_source_route)[1]
    calculated_route = source_route.get_source_route(expected_destination)

    # log
    if log.isEnabledFor(logging.DEBUG):
        output = []
        output += ['\n']
        output += ['expected_destination: {0}'.format(format_addr(expected_destination))]
        output += ['expectedRoute:']
        for m in expected_route:
            output += ['- {0}'.format(format_addr(m))]
        output += ['calculatedRoute:']
        for m in calculated_route:
            output += ['- {0}'.format(format_addr(m))]
        output = '\n'.join(output)
        log.debug(output)

    assert calculated_route == expected_route
