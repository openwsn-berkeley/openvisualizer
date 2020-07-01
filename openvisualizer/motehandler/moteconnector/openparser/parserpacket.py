# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging

from openvisualizer.motehandler.moteconnector.openparser import parser

log = logging.getLogger('ParserPacket')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


class ParserPacket(parser.Parser):
    HEADER_LENGTH = 2

    def __init__(self):
        # log
        log.debug("create instance")

        # initialize parent class
        super(ParserPacket, self).__init__(self.HEADER_LENGTH)

    # ======================== public ==========================================

    def parse_input(self, data):
        # log
        log.debug("received packet: {0}".format(data))

        # ensure data not short longer than header
        self._check_length(data)

        _ = data[:2]  # header bytes

        # remove mote id at the beginning.
        data = data[2:]

        log.debug("packet without header: {0}".format(data))

        event_type = 'sniffedPacket'

        # notify a tuple including source as one hop away nodes elide SRC address as can be inferred from MAC layer
        # header
        return event_type, data

# ======================== private =========================================
