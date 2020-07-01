# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import os
import signal

import serial

from moteprobe import MoteProbe, MoteProbeNoData

try:
    import _winreg as winreg
except ImportError:
    import glob
    import platform

log = logging.getLogger('MoteProbe')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


# ============================ class ===================================

class SerialMoteProbe(MoteProbe):
    def __init__(self, port, baudrate):
        self._port = port
        self._baudrate = baudrate
        self._serial = None

        # initialize the parent class
        MoteProbe.__init__(self, portname=port)

    # ======================== public ==================================

    @property
    def baudrate(self):
        with self.data_lock:
            return self._baudrate

    @property
    def serial(self):
        return self._serial

    @classmethod
    def probe_serial_ports(cls, baudrate, port_mask=None):
        ports = cls._get_ports_from_mask(port_mask)
        mote_probes = []
        probe = None

        log.warning("Probing motes: {} at baudrates {}".format(ports, baudrate))

        try:
            for port in ports:
                try:
                    probe = cls(port=port, baudrate=115200)
                    while probe._serial is None:
                        pass
                    for baud in baudrate:
                        log.debug("Probe port {} at baudrate {}".format(port, baud))
                        probe._serial.baudrate = baud
                        if probe.test_serial(pkts=2):
                            mote_probes.append(probe)
                            break
                except Exception as e:
                    if probe:
                        probe.close()
                        probe.join()
                    log.error(e)
        except KeyboardInterrupt:
            # graceful exit
            for mote in mote_probes:
                mote.close()
                mote.join()
            if probe:
                probe.close()
                probe.join()
            os.kill(os.getpid(), signal.SIGTERM)
        valid_motes = ['{0}'.format(p._portname) for p in mote_probes]
        log.success("Discovered serial-port(s): {0}".format(valid_motes))

        return mote_probes

    # ======================== private =================================

    def _send_data(self, data):
        hdlc_data = self.hdlc.hdlcify(data)
        bytes_written = 0
        self._serial.flush()
        while bytes_written != len(bytearray(hdlc_data)):
            bytes_written += self._serial.write(hdlc_data)

    def _rcv_data(self, rx_bytes=1):
        data = self._serial.read(rx_bytes)
        if data == 0:
            raise MoteProbeNoData
        else:
            return data

    def _detach(self):
        if self._serial is not None:
            log.warning('closing serial port {}'.format(self._portname))
            self._serial.close()

    def _attach(self):
        log.debug("attaching to serial port: {} @ {}".format(self._port, self._baudrate))
        self._serial = serial.Serial(self._port, self._baudrate, timeout=1, xonxoff=True, rtscts=False, dsrdtr=False)
        log.debug("self._serial: {}".format(self._serial))

    @staticmethod
    def _get_ports_from_mask(port_mask=None):
        ports = []

        if port_mask is None:
            if os.name == 'nt':
                path = 'HARDWARE\\DEVICEMAP\\SERIALCOMM'
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
                    for i in range(winreg.QueryInfoKey(key)[1]):
                        try:
                            val = winreg.EnumValue(key, i)
                        except WindowsError:
                            pass
                        else:
                            ports.append(str(val[1]))
                except WindowsError:
                    pass
            elif os.name == 'posix':
                if platform.system() == 'Darwin':
                    port_mask = ['/dev/tty.usbserial-*']
                else:
                    port_mask = ['/dev/ttyUSB*']
                for mask in port_mask:
                    ports += [s for s in glob.glob(mask)]
        else:
            for mask in port_mask:
                ports += [s for s in glob.glob(mask)]

        return ports
