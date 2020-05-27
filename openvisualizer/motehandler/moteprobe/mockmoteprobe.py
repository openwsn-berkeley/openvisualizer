# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

from moteprobe import MoteProbe


# ============================ class ===================================

class MockMoteProbe(MoteProbe):
    def __init__(self, mock_name, daemon=False, buffer=None):

        self.trigger_rcv = False
        self._blocking = False
        self._buffer = buffer

        # initialize the parent class
        MoteProbe.__init__(self, portname=mock_name, daemon=daemon)

        self.send_to_parser = self.receive_data_from_mote_probe
        self.send_to_parser_data = None

    @property
    def buffer(self):
        with self.data_lock:
            return self._buffer

    @buffer.setter
    def buffer(self, value):
        with self.data_lock:
            self._buffer = value

    @property
    def serial(self):
        return None

    @property
    def blocking(self):
        with self.data_lock:
            return self._blocking

    @blocking.setter
    def blocking(self, value):
        with self.data_lock:
            self._blocking = value

    # ======================== public =================================

    def receive_data_from_mote_probe(self, data):
        self.send_to_parser_data = data

    # ======================== private =================================

    def _send_data(self, data):
        pass

    def _rcv_data(self):
        if self.quit:
            return '0x00'
        else:
            while not self.quit and (self.blocking or self.buffer is None):
                pass
            if self.buffer:
                tmp_buffer = self.buffer
                self.buffer = None
                return tmp_buffer
            else:
                return '0x00'

    def _detach(self):
        pass

    def _attach(self):
        pass
