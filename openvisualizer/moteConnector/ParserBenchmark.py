# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
import logging

log = logging.getLogger('ParserBenchmark')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

import struct

from pydispatch import dispatcher

from ParserException import ParserException
import Parser

from openvisualizer.openType      import typeAsn

class ParserBenchmark(Parser.Parser):
    HEADER_LENGTH = 2

    def __init__(self):

        # log
        log.info("create instance")

        # initialize parent class
        Parser.Parser.__init__(self, self.HEADER_LENGTH)

        self._asn = ['asn_4',  # B
                     'asn_2_3',  # H
                     'asn_0_1',  # H
                     ]

    # ======================== public ==========================================

    def parseInput(self, input):
        # log
        log.debug("received data {0}".format(input))

        # ensure input not short longer than header
        self._checkLength(input)

        source = input[:8]
        event = input[8]

        asnParsed = struct.unpack('<HHB', ''.join([chr(c) for c in input[9:14]]))
        timestamp = typeAsn.typeAsn()
        timestamp.update(asnParsed[0], asnParsed[1], asnParsed[2])

        # generic fields are parsed, omit them
        input = input[14:]

        eventType = 'performanceData'

        return eventType, (source, event, timestamp, input)

    # ======================== private =========================================
