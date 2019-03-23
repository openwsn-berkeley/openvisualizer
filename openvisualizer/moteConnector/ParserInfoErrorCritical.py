# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
import logging
log = logging.getLogger('ParserInfoErrorCritical')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

import struct

from ParserException import ParserException
import Parser
from pydispatch import dispatcher
import json

import StackDefines

class ParserInfoErrorCritical(Parser.Parser):
    
    HEADER_LENGTH       = 1
    
    SEVERITY_INFO       = ord('I')
    SEVERITY_ERROR      = ord('E')
    SEVERITY_CRITICAL   = ord('C')
    SEVERITY_ALL        = [SEVERITY_INFO,
                           SEVERITY_ERROR,
                           SEVERITY_CRITICAL,]
    
    def __init__(self,severity):
        assert severity in self.SEVERITY_ALL
        
        # log
        log.info("create instance")
        
        # store params
        self.severity   = severity

        self.numPacketDropped = {
            'queue_overflow':          0,
            'maxmium_retries_reached': 0,
            'uinject_packet':          0,
        }
        
        # initialize parent class
        Parser.Parser.__init__(self,self.HEADER_LENGTH)
    
    #======================== public ==========================================
    
    def parseInput(self,input):
        
        # log
        if log.isEnabledFor(logging.DEBUG):
            log.debug("received data {0}".format(input))
        
        # parse packet
        try:
           (moteId,
            callingComponent,
            error_code,
            arg1,
            arg2) = struct.unpack('>HBBHH',''.join([chr(c) for c in input]))
        except struct.error:
            raise ParserException(ParserException.DESERIALIZE,"could not extract data from {0}".format(input))

        if error_code == 27:
            # this is large time correction info, 
            (arg1, arg2) = struct.unpack('>hH',''.join([chr(c) for c in input[-4:]]))

        
        # turn into string
        output = "{MOTEID:x} [{COMPONENT}] {ERROR_DESC}".format(
            COMPONENT  = self._translateCallingComponent(callingComponent),
            MOTEID     = moteId,
            ERROR_DESC = self._translateErrorDescription(error_code,arg1,arg2),
        )
        
        # log
        if   self.severity==self.SEVERITY_INFO:
            log.info(output)
        elif self.severity==self.SEVERITY_ERROR:
            log.error(output)
        elif self.severity==self.SEVERITY_CRITICAL:
            log.critical(output)
        else:
            raise SystemError("unexpected severity={0}".format(self.severity))
        
        return 'error', input
    
    #======================== private =========================================
    
    def _translateCallingComponent(self,callingComponent):
        try:
            return StackDefines.components[callingComponent]
        except KeyError:
            return "unknown component code {0}".format(callingComponent)
    
    def _translateErrorDescription(self,error_code,arg1,arg2):
        try:
            if error_code == 59:
                arg1 = StackDefines.sixtop_returncode[arg1]
                arg2 = StackDefines.sixtop_statemachine[arg2]

            if error_code == 18:
                # forwarding packet is dropped
                if arg1 == 0:
                    self.numPacketDropped['queue_overflow'] += 1
                elif arg1 == 1:
                    self.numPacketDropped['maxmium_retries_reached'] += 1

            if error_code == 73:
                # uinject packet is dropped
                self.numPacketDropped['uinject_packet'] += 1

            return StackDefines.errorDescriptions[error_code].format(arg1,arg2)
        except KeyError:
            return "unknown error {0} arg1={1} arg2={2}".format(error_code,arg1,arg2)