# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import queue
from typing import TYPE_CHECKING

from openvisualizer.motehandler.moteprobe.moteprobe import MoteProbe, MoteProbeNoData
from openvisualizer.simulator.moteprocess import Uart

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

    def _send_data(self, data: str):
        hdlc_data = self.hdlc.hdlcify(data)
        self.serial.rx.put([ord(b) for b in hdlc_data])

    def _rcv_data(self):
        try:
            rcv = [b for b in self.serial.tx.get_nowait()[0]]
            return rcv
        except queue.Empty:
            raise MoteProbeNoData()

    def _detach(self):
        log.info("Exiting EmulatedMoteProbe")

    @property
    def serial(self):
        return self._serial

    def _attach(self) -> bool:
        """
        Attaches to the emulated mote's uart queue.

        :return: True
        """
        self._serial = self.emulated_mote.uart

        if isinstance(self._serial, Uart):
            return True
        else:
            return False
