# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging

import parser
import parserdata
import parserpacket
import parserprintf
import parserstatus
from parseriec import ParserInfoErrorCritical

log = logging.getLogger('OpenParser')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


class OpenParser(parser.Parser):
    HEADER_LENGTH = 1

    SERFRAME_MOTE2PC_DATA = ord('D')
    SERFRAME_MOTE2PC_STATUS = ord('S')
    SERFRAME_MOTE2PC_VERBOSE = ParserInfoErrorCritical.LogSeverity.SEVERITY_VERBOSE
    SERFRAME_MOTE2PC_INFO = ParserInfoErrorCritical.LogSeverity.SEVERITY_INFO
    SERFRAME_MOTE2PC_WARNING = ParserInfoErrorCritical.LogSeverity.SEVERITY_WARNING
    SERFRAME_MOTE2PC_SUCCESS = ParserInfoErrorCritical.LogSeverity.SEVERITY_SUCCESS
    SERFRAME_MOTE2PC_ERROR = ParserInfoErrorCritical.LogSeverity.SEVERITY_ERROR
    SERFRAME_MOTE2PC_CRITICAL = ParserInfoErrorCritical.LogSeverity.SEVERITY_CRITICAL
    SERFRAME_MOTE2PC_SNIFFED_PACKET = ord('P')
    SERFRAME_MOTE2PC_PRINTF = ord('F')

    SERFRAME_PC2MOTE_SETDAGROOT = ord('R')
    SERFRAME_PC2MOTE_DATA = ord('D')
    SERFRAME_PC2MOTE_TRIGGERSERIALECHO = ord('S')
    SERFRAME_PC2MOTE_COMMAND = ord('C')

    SERFRAME_ACTION_YES = ord('Y')
    SERFRAME_ACTION_NO = ord('N')
    SERFRAME_ACTION_TOGGLE = ord('T')

    def __init__(self, mqtt_broker_address):
        # log
        log.debug("create instance")

        # initialize parent class
        super(OpenParser, self).__init__(self.HEADER_LENGTH)

        # subparser objects
        self.parser_status = parserstatus.ParserStatus()
        self.parser_verbose = ParserInfoErrorCritical(self.SERFRAME_MOTE2PC_VERBOSE)
        self.parser_info = ParserInfoErrorCritical(self.SERFRAME_MOTE2PC_INFO)
        self.parser_warning = ParserInfoErrorCritical(self.SERFRAME_MOTE2PC_WARNING)
        self.parser_success = ParserInfoErrorCritical(self.SERFRAME_MOTE2PC_SUCCESS)
        self.parser_error = ParserInfoErrorCritical(self.SERFRAME_MOTE2PC_ERROR)
        self.parser_critical = ParserInfoErrorCritical(self.SERFRAME_MOTE2PC_CRITICAL)
        self.parser_data = parserdata.ParserData(mqtt_broker_address)
        self.parser_packet = parserpacket.ParserPacket()
        self.parser_printf = parserprintf.ParserPrintf()

        # register subparsers
        self._add_sub_parser(
            index=0,
            val=self.SERFRAME_MOTE2PC_DATA,
            parser=self.parser_data,
        )
        self._add_sub_parser(
            index=0,
            val=self.SERFRAME_MOTE2PC_STATUS,
            parser=self.parser_status,
        )
        self._add_sub_parser(
            index=0,
            val=self.SERFRAME_MOTE2PC_VERBOSE,
            parser=self.parser_verbose,
        )
        self._add_sub_parser(
            index=0,
            val=self.SERFRAME_MOTE2PC_INFO,
            parser=self.parser_info,
        )
        self._add_sub_parser(
            index=0,
            val=self.SERFRAME_MOTE2PC_WARNING,
            parser=self.parser_warning,
        )
        self._add_sub_parser(
            index=0,
            val=self.SERFRAME_MOTE2PC_SUCCESS,
            parser=self.parser_success,
        )
        self._add_sub_parser(
            index=0,
            val=self.SERFRAME_MOTE2PC_ERROR,
            parser=self.parser_error,
        )
        self._add_sub_parser(
            index=0,
            val=self.SERFRAME_MOTE2PC_CRITICAL,
            parser=self.parser_critical,
        )
        self._add_sub_parser(
            index=0,
            val=self.SERFRAME_MOTE2PC_SNIFFED_PACKET,
            parser=self.parser_packet,
        )
        self._add_sub_parser(
            index=0,
            val=self.SERFRAME_MOTE2PC_PRINTF,
            parser=self.parser_printf,
        )
