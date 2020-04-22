# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

from enum import Enum


class ParserException(Exception):
    class ExceptionType(Enum):
        GENERIC = 1
        TOO_SHORT = 2
        WRONG_LENGTH = 3
        UNKNOWN_OPTION = 4
        NO_KEY = 5
        DESERIALIZE = 6

    descriptions = {
        ExceptionType.GENERIC: 'generic parsing error',
        ExceptionType.TOO_SHORT: 'data too short',
        ExceptionType.WRONG_LENGTH: 'data of the wrong length',
        ExceptionType.UNKNOWN_OPTION: 'no parser key',
        ExceptionType.NO_KEY: 'no key',
        ExceptionType.DESERIALIZE: 'deserialization error',
    }

    def __init__(self, error_code, details=None):
        self.error_code = error_code
        self.details = details

    def __str__(self):
        try:
            output = self.descriptions[self.error_code]
            if self.details:
                output += ': ' + str(self.details)
            return output
        except KeyError:
            return "Unknown error: #" + str(self.error_code)
