# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import abc
import logging
import sys
import threading
import time

from pydispatch import dispatcher

from openvisualizer.motehandler.moteprobe import openhdlc
from openvisualizer.motehandler.moteprobe.serialtester import SerialTester
from openvisualizer.utils import format_string_buf, format_crash_message

log = logging.getLogger('MoteProbe')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


# ============================ class ===================================

class MoteProbeNoData(Exception):
    """ No data received from serial pipe """
    pass


# ============================ class ===================================

class MoteProbe(threading.Thread):
    __metaclass__ = abc.ABCMeta

    XOFF = 0x13
    XON = 0x11
    XONXOFF_ESCAPE = 0x12
    XONXOFF_MASK = 0x10

    # XOFF            is transmitted as [XONXOFF_ESCAPE,           XOFF^XONXOFF_MASK]==[0x12,0x13^0x10]==[0x12,0x03]
    # XON             is transmitted as [XONXOFF_ESCAPE,            XON^XONXOFF_MASK]==[0x12,0x11^0x10]==[0x12,0x01]
    # XONXOFF_ESCAPE  is transmitted as [XONXOFF_ESCAPE, XONXOFF_ESCAPE^XONXOFF_MASK]==[0x12,0x12^0x10]==[0x12,0x02]

    def __init__(self, portname, daemon=False):
        # initialize the parent class
        super(MoteProbe, self).__init__()

        self._portname = portname
        self.data_lock = threading.Lock()

        # hdlc frame parser object
        self.hdlc = openhdlc.OpenHdlc()
        # flag to permit exit from read loop
        self.quit = False
        # to be assigned, callback
        self.send_to_parser = None

        # frame parsing variables
        self.rx_buf = ''
        self.hdlc_flag = False
        self.receiving = False
        self.xonxoff_escaping = False

        # give this thread a name
        self.name = 'MoteProbe@' + self._portname

        # Non-daemonized MoteProbe does not consistently die on close(), so ensure MoteProbe does not persist.
        self.daemon = daemon

        # connect to dispatcher
        dispatcher.connect(self._send_data, signal='fromMoteConnector@' + self._portname)

        # start myself
        self.start()

    # ======================== thread ==================================

    def run(self):
        try:
            log.debug("start running")
            log.debug("attach to port {0}".format(self._portname))
            self._attach()

            while not self.quit:  # read bytes from serial pipe
                try:
                    rx_bytes = self._rcv_data()
                except MoteProbeNoData:
                    continue
                except Exception as err:
                    log.warning(err)
                    time.sleep(1)
                    break
                else:
                    self._parse_bytes(rx_bytes)
                if hasattr(self, 'emulated_mote'):
                    self.serial.done_reading()
            log.warning('{}; exit loop'.format(self._portname))
        except Exception as err:
            err_msg = format_crash_message(self.name, err)
            log.critical(err_msg)
            sys.exit(-1)
        finally:
            self._detach()

    # ======================== public ==================================

    @property
    def serial(self):
        raise NotImplementedError("Should be implemented by child class")

    @property
    def portname(self):
        with self.data_lock:
            return self._portname

    def close(self):
        """ Signal thread to exit """
        self.quit = True

    def test_serial(self, pkts=1, timeout=2):
        """ Probes serial pipe to test responsiveness """
        tester = SerialTester(self)
        tester.set_num_test_pkt(pkts)
        tester.set_timeout(timeout)
        tester.test(blocking=True)
        return tester.get_stats()['numOk'] >= 1

    # ======================== private =================================

    @abc.abstractmethod
    def _attach(self):
        raise NotImplementedError("Should be implemented by child class")

    @abc.abstractmethod
    def _detach(self):
        raise NotImplementedError("Should be implemented by child class")

    @abc.abstractmethod
    def _send_data(self, data):
        raise NotImplementedError("Should be implemented by child class")

    @abc.abstractmethod
    def _rcv_data(self):
        raise NotImplementedError("Should be implemented by child class")

    def _handle_frame(self):
        """ Handles a HDLC frame """
        valid_frame = False
        temp_buf = self.rx_buf
        try:
            self.rx_buf = self.hdlc.dehdlcify(self.rx_buf)

            if log.isEnabledFor(logging.DEBUG):
                log.debug("{}: {} dehdlcized input: {}".format(
                    self.name,
                    format_string_buf(temp_buf),
                    format_string_buf(self.rx_buf)))

            if self.send_to_parser:
                self.send_to_parser([ord(c) for c in self.rx_buf])

            valid_frame = True
        except openhdlc.HdlcException as err:
            log.warning('{}: invalid serial frame: {} {}'.format(self.name, format_string_buf(temp_buf), err))

        return valid_frame

    def _rx_buf_add(self, byte):
        """ Adds byte to buffer and escapes the XONXOFF bytes """
        if byte == chr(self.XONXOFF_ESCAPE):
            self.xonxoff_escaping = True
        else:
            if self.xonxoff_escaping is True:
                self.rx_buf += chr(ord(byte) ^ self.XONXOFF_MASK)
                self.xonxoff_escaping = False
            elif byte != chr(self.XON) and byte != chr(self.XOFF):
                self.rx_buf += byte

    def _parse_bytes(self, octets):
        """ Parses bytes received from serial pipe """
        for byte in octets:
            if not self.receiving:
                if self.hdlc_flag and byte != self.hdlc.HDLC_FLAG:
                    # start of frame
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug("%s: start of HDLC frame %s %s",
                                  self.name,
                                  format_string_buf(self.hdlc.HDLC_FLAG),
                                  format_string_buf(byte),
                                  )
                    self.receiving = True
                    # discard received self.hdlc_flag
                    self.hdlc_flag = False
                    self.xonxoff_escaping = False
                    self.rx_buf = self.hdlc.HDLC_FLAG
                    self._rx_buf_add(byte)
                elif byte == self.hdlc.HDLC_FLAG:
                    # received hdlc flag
                    self.hdlc_flag = True
                else:
                    # drop garbage
                    pass
            else:
                if byte != self.hdlc.HDLC_FLAG:
                    # middle of frame
                    self._rx_buf_add(byte)
                else:
                    # end of frame, received self.hdlc_flag
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug("{}: end of hdlc frame {}".format(self.name, format_string_buf(byte)))

                    self.hdlc_flag = True
                    self.receiving = False
                    self._rx_buf_add(byte)
                    valid_frame = self._handle_frame()

                    if valid_frame:
                        # discard valid frame self.hdlc_flag
                        self.hdlc_flag = False
