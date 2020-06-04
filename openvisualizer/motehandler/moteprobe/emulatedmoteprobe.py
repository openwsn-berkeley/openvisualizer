# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging

from moteprobe import MoteProbe

log = logging.getLogger('MoteProbe')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


# ============================ functions ===============================


# ============================ class ===================================

class EmulatedMoteProbe(MoteProbe):
    def __init__(self, emulated_mote):
        self.emulated_mote = emulated_mote
        self._serial = None

        if not self.emulated_mote:
            raise SystemError()

        name = 'emulated{0}'.format(self.emulated_mote.get_id())
        # initialize the parent class
        MoteProbe.__init__(self, portname=name, daemon=True)

    # ======================== private =================================

    def _send_data(self, data):
        hdlc_data = self.hdlc.hdlcify(data)
        bytes_written = 0
        while bytes_written != len(bytearray(hdlc_data)):
            bytes_written += self.serial.write(hdlc_data)

    def _rcv_data(self):
        return self.serial.read()

    def _detach(self):
        pass

    @property
    def serial(self):
        return self._serial

    def _attach(self):
        self._serial = self.emulated_mote.bsp_uart
