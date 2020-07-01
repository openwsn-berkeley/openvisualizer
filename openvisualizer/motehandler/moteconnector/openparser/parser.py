# Copyright (c) 2010-2020, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
from abc import ABCMeta

from openvisualizer.motehandler.moteconnector.openparser.parserexception import ParserException

log = logging.getLogger('Parser')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


class ParsingKey(object):

    def __init__(self, index, val, parser):
        assert (index is not None)
        assert (val is not None)
        assert (parser is not None)

        self.index = index
        self.val = val
        self.parser = parser

    def __str__(self):
        template = "{0}={1}"
        output = []
        output += [template.format("index", self.index)]
        output += [template.format("val", self.val)]
        output += [template.format("parser", self.parser)]
        return ' '.join(output)


class Parser(object):
    __metaclass__ = ABCMeta

    def __init__(self, header_length):

        # store params
        self.header_length = header_length

        # local variables
        self.parsing_keys = []
        self.header_parsing_keys = []
        self.named_tuple = {}

    # ======================== public ==========================================

    def parse_input(self, data):

        # log
        log.debug("received data: {0}".format(data))

        # ensure data not short longer than header
        self._check_length(data)

        # parse the header
        # TODO

        # call the next header parser
        for key in self.parsing_keys:
            if data[key.index] == key.val:
                return key.parser.parse_input(data[self.header_length:])

        # if you get here, no key was found
        raise ParserException(ParserException.ExceptionType.NO_KEY, "type={0} (\"{1}\")".format(data[0], chr(data[0])))

    # ======================== private =========================================

    def _check_length(self, input):
        if len(input) < self.header_length:
            raise ParserException(ParserException.ExceptionType.TOO_SHORT)

    def _add_sub_parser(self, index=None, val=None, parser=None):
        self.parsing_keys.append(ParsingKey(index, val, parser))
