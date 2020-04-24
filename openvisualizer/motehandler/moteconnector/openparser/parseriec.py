# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import struct

import verboselogs
from enum import IntEnum

import defines
from parser import Parser
from parserexception import ParserException

verboselogs.install()
log = logging.getLogger('ParserIEC')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


class ParserInfoErrorCritical(Parser):
    HEADER_LENGTH = 1

    class LogSeverity(IntEnum):
        SEVERITY_VERBOSE = ord('V')
        SEVERITY_INFO = ord('I')
        SEVERITY_WARNING = ord('W')
        SEVERITY_SUCCESS = ord('U')
        SEVERITY_ERROR = ord('E')
        SEVERITY_CRITICAL = ord('C')

    def __init__(self, severity):
        assert self.LogSeverity(severity)

        # log
        log.debug("create instance")

        # initialize parent class
        super(ParserInfoErrorCritical, self).__init__(self.HEADER_LENGTH)

        # store params
        self.severity = severity

        # store error info
        self.error_info = {}

    # ======================== public ==========================================

    def parse_input(self, data):

        # log
        log.debug("received data {0}".format(data))

        # parse packet
        try:
            mote_id, component, error_code, arg1, arg2 = struct.unpack('>HBBhH', ''.join([chr(c) for c in data]))
        except struct.error:
            raise ParserException(ParserException.ExceptionType.DESERIALIZE.value,
                                  "could not extract data from {0}".format(data))

        if (component, error_code) in self.error_info.keys():
            self.error_info[(component, error_code)] += 1
        else:
            self.error_info[(component, error_code)] = 1

        if error_code == 37:
            # replace args of sixtop command/return code id by string
            arg1 = defines.sixtop_returncode[arg1]
            arg2 = defines.sixtop_statemachine[arg2]

        # turn into string
        output = "{MOTEID:x} [{COMPONENT}] {ERROR_DESC}".format(
            COMPONENT=self._translate_component(component),
            MOTEID=mote_id,
            ERROR_DESC=self._translateErrorDescription(error_code, arg1, arg2),
        )

        # log
        if self.severity == self.LogSeverity.SEVERITY_VERBOSE:
            log.verbose(output)
        elif self.severity == self.LogSeverity.SEVERITY_INFO:
            log.info(output)
        elif self.severity == self.LogSeverity.SEVERITY_WARNING:
            log.warning(output)
        elif self.severity == self.LogSeverity.SEVERITY_SUCCESS:
            log.success(output)
        elif self.severity == self.LogSeverity.SEVERITY_ERROR:
            log.error(output)
        elif self.severity == self.LogSeverity.SEVERITY_CRITICAL:
            log.critical(output)
        else:
            raise SystemError("unexpected severity={0}".format(self.severity))

        return 'error', data

    # ======================== private =========================================

    def _translate_component(self, component):
        try:
            return defines.components[component]
        except KeyError:
            return "unknown component code {0}".format(component)

    def _translateErrorDescription(self, error_code, arg1, arg2):
        try:
            return defines.errorDescriptions[error_code].format(
                arg1, arg2)
        except KeyError:
            return "unknown error {0} arg1={1} arg2={2}".format(error_code, arg1, arg2)
