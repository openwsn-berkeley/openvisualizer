# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
import logging
log = logging.getLogger('eventLogger')
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())

import threading
import traceback
import time
import json

class eventLogger(threading.Thread):
    
    def __init__(self,moteState):
        
        self.moteState                 = moteState
        self.serialport                = self.moteState.moteConnector.serialport
        self.logfile                   = 'eventLog_{0}.log'.format(self.serialport)
        self.output                    = {}
        
        # initialize the parent class
        threading.Thread.__init__(self)
        
        # start myself
        self.start()
    
    #======================== thread ==========================================
    
    def run(self):
        
        while True:
            with open(self.logfile,'a') as f:
                for key, value in self.moteState.state.items():
                    self.output[key] = value._toDict()["data"]
                    for item in self.output[key]:
                        f.write(str(item)+'\n')
                    # json_output = json.dumps(self.output)
                
            time.sleep(2)
        
    #======================== public ==========================================
    
    #======================== private =========================================