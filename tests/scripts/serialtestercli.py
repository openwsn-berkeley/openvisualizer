#!/usr/bin/env python2

import logging.handlers
import sys

from opencli import OpenCli
from openvisualizer.motehandler.moteprobe.serialtester import SerialTester
from openvisualizer.motehandler.moteprobe import moteprobe

logHandler = logging.handlers.RotatingFileHandler(
    'SerialTesterCli.log',
    maxBytes=2000000,
    backupCount=5,
    mode='w')

logHandler.setFormatter(logging.Formatter("%(asctime)s [%(name)s:%(levelname)s] %(message)s"))


class SerialTesterCli(OpenCli):

    def __init__(self, mote_probe_handler, mote_connector_handler):

        # store params
        self.moteProbe_handler = mote_probe_handler
        self.mote_connector_handler = mote_connector_handler

        # initialize parent class
        super(SerialTesterCli, self).__init__("Serial Tester", self._quit_cb)

        # add commands
        self.register_command(
            'pklen',
            'pl',
            'test packet length, in bytes',
            ['pklen'],
            self._handle_pklen
        )
        self.register_command(
            'numpk',
            'num',
            'number of test packets',
            ['numpk'],
            self._handle_numpk
        )
        self.register_command(
            'timeout',
            'tout',
            'timeout for answer, in seconds',
            ['timeout'],
            self._handle_timeout
        )
        self.register_command(
            'trace',
            'trace',
            'activate console trace',
            ['on/off'],
            self._handle_trace
        )
        self.register_command(
            'testserial',
            't',
            'test serial port',
            [],
            self._handle_testserial
        )
        self.register_command(
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

    # ======================== public ==========================================

    # ======================== private =========================================

    # ===== CLI command handlers

    def _handle_pklen(self, params):
        self.mote_connector_handler.set_test_pkt_length(int(params[0]))

    def _handle_numpk(self, params):
        self.mote_connector_handler.set_num_test_pkt(int(params[0]))

    def _handle_timeout(self, params):
        self.mote_connector_handler.set_timeout(int(params[0]))

    def _handle_trace(self, params):
        if params[0] in [1, 'on', 'yes']:
            self.mote_connector_handler.set_trace(SerialTesterCli._indicate_trace)
        else:
            self.mote_connector_handler.set_trace(None)

    def _handle_testserial(self, params):
        self.mote_connector_handler.test(blocking=False)

    def _handle_stats(self, params):
        stats = self.mote_connector_handler.get_stats()
        output = []
        for k in ['numSent', 'numOk', 'numCorrupted', 'numTimeout']:
            output += ['- {0:<15} : {1}'.format(k, stats[k])]
        output = '\n'.join(output)
        print output

    @staticmethod
    def _indicate_trace(debug_text):
        print debug_text

    # ===== helpers

    def _quit_cb(self):
        self.mote_connector_handler.quit()
        self.moteProbe_handler.close()


# ============================ main ============================================


def main():
    mqtt_broker_address = 'argus.paris.inria.fr'

    # get serial port name
    if len(sys.argv) == 2:
        serialport_name = sys.argv[1]
        serialport = (serialport_name, moteprobe.BAUDRATE_LOCAL_BOARD)
        mote_probe_handler = moteprobe.MoteProbe(serial_port=serialport, mqtt_broker_address=None)
    else:
        try:
            test_mode = raw_input('Serialport or OpenTestbed? (0: serialport, 1: opentestbed) ')
        except KeyboardInterrupt:
            return
        if test_mode == '0':
            try:
                serialport_name = raw_input('Serial port to connect to (e.g. COM3, /dev/ttyUSB1): ')
            except KeyboardInterrupt:
                return
            serialport = (serialport_name, moteprobe.BAUDRATE_LOCAL_BOARD)

            # create a MoteProbe from serial port
            mote_probe_handler = moteprobe.MoteProbe(serial_port=serialport, mqtt_broker_address=None)
        elif test_mode == '1':
            try:
                testbed_mote = raw_input('Testbed mote to connect to (e.g. 00-12-4b-00-14-b5-b6-0b): ')
            except KeyboardInterrupt:
                return
                # create a MoteProbe from opentestbed
            mote_probe_handler = moteprobe.MoteProbe(mqtt_broker_address=mqtt_broker_address,
                                                     testbedmote_eui64=testbed_mote)
        else:
            raw_input("Wrong input! Press Enter to quit..")
            return

    # create a SerialTester to attached to the MoteProbe
    mote_connector_handler = SerialTester(mote_probe_handler)

    # create an open CLI
    cli = SerialTesterCli(mote_probe_handler, mote_connector_handler)
    cli.start()


# ============================ application logging =============================


for loggerName in ['SerialTester', 'MoteProbe', 'OpenHdlc']:
    temp = logging.getLogger(loggerName)
    temp.setLevel(logging.DEBUG)
    temp.addHandler(logHandler)

if __name__ == "__main__":
    main()
