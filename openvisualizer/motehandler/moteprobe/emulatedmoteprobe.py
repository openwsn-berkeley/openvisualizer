# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import queue
from typing import TYPE_CHECKING

from .moteprobe import MoteProbe, MoteProbeNoData

if TYPE_CHECKING:
    from openvisualizer.simulator.simengine import MoteProcessInterface

log = logging.getLogger('MoteProbe')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


# ============================ functions ===============================


# ============================ class ===================================

class EmulatedMoteProbe(MoteProbe):
    def __init__(self, emulated_mote: 'MoteProcessInterface'):
        self.emulated_mote = emulated_mote
        self._serial = None

        if not self.emulated_mote:
            raise SystemError()

        name = 'emulated{0}'.format(self.emulated_mote.mote_id)
        # initialize the parent class
        MoteProbe.__init__(self, portname=name, daemon=True)

    # ======================== private =================================

    def _send_data(self, data):
        hdlc_data = self.hdlc.hdlcify(data)
        self.serial.rx.put([ord(b) for b in hdlc_data])

    def _rcv_data(self):
        try:
            return "".join([chr(b) for b in self.serial.tx.get_nowait()[0]])
        except queue.Empty:
            raise MoteProbeNoData()

    def _detach(self):
        log.info("Exiting EmulatedMoteProbe")

    @property
    def serial(self):
        return self._serial

    def _attach(self):
        self._serial = self.emulated_mote.uart
