# Copyright (c) 2017, CNRS.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import sys

from openvisualizer.motehandler.moteconnector.openparser import parser

log = logging.getLogger('ParserPrintf')
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())


class ParserPrintf(parser.Parser):
    HEADER_LENGTH = 2

    def __init__(self):

        # log
        log.debug('create instance')

        # initialize parent class
        super(ParserPrintf, self).__init__(self.HEADER_LENGTH)

    # returns a string with the decimal value of a uint16_t
    @staticmethod
    def bytes_to_string(bytestring):
        string = ''
        i = 0

        for byte in bytestring:
            string = format(eval('{0} + {1} * 256 ** {2}'.format(string, byte, i)))
            i = i + 1

        return string

    @staticmethod
    def bytes_to_addr(bytestring):
        string = ''

        for byte in bytestring:
            string = string + '{:02x}'.format(byte)

        return string

    def parse_input(self, data):

        # log
        log.debug('received printf {0}'.format(data))

        _ = ParserPrintf.bytes_to_addr(data[0:2])  # addr
        _ = ParserPrintf.bytes_to_string(data[2:7])  # asn

        sys.stdout.write("{}".format("".join([chr(c) for c in data[7:]])))
        sys.stdout.flush()

        # everything was fine
        return 'error', data
