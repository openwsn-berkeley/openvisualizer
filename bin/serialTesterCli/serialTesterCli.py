import sys
import os

if __name__=='__main__':
    here = sys.path[0]
    sys.path.insert(0, os.path.join(here, '..', '..'))                     # openvisualizer/
    sys.path.insert(0, os.path.join(here, '..', '..', '..', 'openCli'))    # openCli/
    
from openvisualizer.motehandler.moteprobe import moteprobe
from openvisualizer.motehandler.moteconnector.SerialTester import SerialTester
from OpenCli                                     import OpenCli

class serialTesterCli(OpenCli):
    
    def __init__(self,moteProbe_handler,moteConnector_handler):
        
        # store params
        self.moteProbe_handler     = moteProbe_handler
        self.moteConnector_handler = moteConnector_handler
    
        # initialize parent class
        OpenCli.__init__(self,"Serial Tester",self._quit_cb)
        
        # add commands
        self.registerCommand(
            'pklen',
            'pl',
            'test packet length, in bytes',
            ['pklen'],
            self._handle_pklen
        )
        self.registerCommand(
            'numpk',
            'num',
            'number of test packets',
            ['numpk'],
            self._handle_numpk
        )
        self.registerCommand(
            'timeout',
            'tout',
            'timeout for answer, in seconds',
            ['timeout'],
            self._handle_timeout
        )
        self.registerCommand(
            'trace',
            'trace',
            'activate console trace',
            ['on/off'],
            self._handle_trace
        )
        self.registerCommand(
            'testserial',
            't',
            'test serial port',
            [],
            self._handle_testserial
        )
        self.registerCommand(
            'stats',
            'st',
            'print stats',
            [],
            self._handle_stats
        )
        
        # by default, turn trace on
        self._handle_pklen([10])
        self._handle_numpk([1])
        self._handle_timeout([1])
        self._handle_trace([1])
        
    #======================== public ==========================================
    
    #======================== private =========================================
    
    #===== CLI command handlers
    
    def _handle_pklen(self,params):
        self.moteConnector_handler.setTestPktLength(int(params[0]))
    
    def _handle_numpk(self,params):
        self.moteConnector_handler.setNumTestPkt(int(params[0]))
    
    def _handle_timeout(self,params):
        self.moteConnector_handler.setTimeout(int(params[0]))
    
    def _handle_trace(self,params):
        if params[0] in [1,'on','yes']:
            self.moteConnector_handler.setTrace(self._indicate_trace)
        else:
            self.moteConnector_handler.setTrace(None)
    
    def _handle_testserial(self,params):
        self.moteConnector_handler.test(blocking=False)
    
    def _handle_stats(self,params):
        stats = self.moteConnector_handler.getStats()
        output  = []
        for k in ['numSent','numOk','numCorrupted','numTimeout']:
            output += ['- {0:<15} : {1}'.format(k,stats[k])]
        output  = '\n'.join(output)
        print output
    
    def _indicate_trace(self,debugText):
        print debugText
    
    #===== helpers
    
    def _quit_cb(self):
        self.moteConnector_handler.quit()
        self.moteProbe_handler.close()

#============================ main ============================================

def main():
    
    moteProbe_handler        = None
    moteConnector_handler    = None
    mqtt_broker_address      = 'argus.paris.inria.fr'
    
    # get serial port name
    if len(sys.argv)>1:
        serialportname = sys.argv[1]
    else:
        test_mode = raw_input('Serialport or OpenTestbed? (0: serialport, 1: opentestbed)')
        if test_mode == '0':
            serialportname = raw_input('Serial port to connect to (e.g. COM3, /dev/ttyUSB1): ')
            serialport = (serialportname, moteprobe.BAUDRATE_LOCAL_BOARD)
            # create a MoteProbe from serial port
            moteProbe_handler = moteprobe.MoteProbe(mqtt_broker_address=mqtt_broker_address, serial_port=serialport)
        elif test_mode == '1':
            testbedmote = raw_input('testbed mote to connect to (e.g. 00-12-4b-00-14-b5-b6-0b): ')
            # create a MoteProbe from opentestbed
            moteProbe_handler = moteprobe.MoteProbe(mqtt_broker_address=mqtt_broker_address, testbedmote_eui64=testbedmote)
        else:
            raw_input("wrong input! Press Enter to quit..")
            return
        
    # create a SerialTester to attached to the MoteProbe
    moteConnector_handler = SerialTester(moteProbe_handler)
    
    # create an open CLI
    cli = serialTesterCli(moteProbe_handler,moteConnector_handler)
    cli.start()

#============================ application logging =============================
import logging.handlers
logHandler = logging.handlers.RotatingFileHandler(
    'serialTesterCli.log',
    maxBytes=2000000,
    backupCount=5,
    mode='w'
)
logHandler.setFormatter(logging.Formatter("%(asctime)s [%(name)s:%(levelname)s] %(message)s"))
for loggerName in [
        'SerialTester',
        'moteprobe',
        'OpenHdlc',
    ]:
    temp = logging.getLogger(loggerName)
    temp.setLevel(logging.DEBUG)
    temp.addHandler(logHandler)
    
if __name__=="__main__":
    main()
