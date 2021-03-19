# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import os
import signal
import socket
import time
from contextlib import closing
from typing import Optional, List

import sshtunnel

from openvisualizer.motehandler.moteprobe.moteprobe import MoteProbe, MoteProbeNoData

log = logging.getLogger('MoteProbe')
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())


# ============================ class ===================================

class IotlabMoteProbe(MoteProbe):
    IOTLAB_SSH_TIMEOUT = 2  # seconds
    IOTLAB_SOCKET_TIMEOUT = 2  # seconds
    IOTLAB_MOTE_TCP_PORT = 20000

    IOTLAB_FRONTEND_BASE_URL = 'iot-lab.info'

    def __init__(self,
                 iotlab_mote: str,
                 iotlab_user: str,
                 iotlab_key_file: str,
                 iotlab_site: Optional[str] = None,
                 xonxoff: bool = True,
                 debug: bool = False):

        if iotlab_site is not None:
            self.iotlab_mote = "".join([iotlab_mote, ".", iotlab_site, ".", self.IOTLAB_FRONTEND_BASE_URL])
        else:
            self.iotlab_mote = iotlab_mote

        log.info(self.iotlab_mote)

        self.debug = debug
        self.iotlab_user = iotlab_user
        self.iotlab_key_file = iotlab_key_file
        self.iotlab_site = iotlab_site
        self.iotlab_tunnel = None
        self.xonxoff = xonxoff
        self._cts = False
        self.socket = None

        # initialize the parent class
        super().__init__(portname=iotlab_mote, daemon=True)

    # ======================== public ==================================

    @classmethod
    def probe_iotlab_motes(cls,
                           iotlab_motes: List[str],
                           iotlab_user: str,
                           iotlab_key_file: str,
                           iotlab_site: Optional[str] = None,
                           debug=False):
        mote_probes = []
        probe = None
        log.debug("probing motes: {}".format(iotlab_motes))
        try:
            for mote in iotlab_motes:
                log.debug("probe {}".format(mote))
                try:
                    probe = cls(mote, iotlab_user, iotlab_key_file, iotlab_site, debug)

                    while probe.socket is None and probe.isAlive():
                        pass
                    if probe.test_serial():
                        log.success("{} Ok.".format(probe._portname))
                        mote_probes.append(probe)
                    else:
                        # Exit unresponsive moteprobe threads
                        probe.close()
                        probe.join()
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
        log.success("discovered following iotlab-motes: {}".format(valid_motes))

        return mote_probes

    @property
    def serial(self):
        return self.socket

    # ======================== private =================================

    @staticmethod
    def _get_free_port():
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('', 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    def _set_cts(self, data):
        xoff_idx = -1
        xon_idx = -1
        if chr(self.XON) in data:
            xon_idx = len(data) - 1 - data[::-1].index(chr(self.XON))
        if chr(self.XOFF) in data:
            xoff_idx = len(data) - 1 - data[::-1].index(chr(self.XOFF))
        if xoff_idx > xon_idx:
            self._cts = False
        elif xon_idx > xoff_idx:
            self._cts = True

    def _rcv_data(self, rx_bytes=1024):
        try:
            data = self.socket.recv(rx_bytes)
            if self.xonxoff:
                self._set_cts(data)
            return data
        except socket.timeout:
            raise MoteProbeNoData

    def _send_data(self, data: str):
        if self.socket is None:
            return

        hdlc_data = bytearray([ord(b) for b in self.hdlc.hdlcify(data)])
        hdlc_len = len(hdlc_data)
        bytes_written = 0

        while not self.quit and bytes_written != hdlc_len:
            if self.xonxoff and not self._cts:
                continue
            else:
                bytes_written += self.socket.send(hdlc_data)

    def _detach(self):
        if self.socket is not None:
            log.debug('closing socket to {}'.format(self._portname))
            self.socket.close()

        if self.iotlab_tunnel is not None:
            log.debug('stopping ssh tunnel to {}'.format(self._portname))
            self.iotlab_tunnel.stop()

    def _attach(self) -> bool:
        """
        Tries to ssh into the IoT-LAB frontend and connect to the running motes' serial port.

        :return: True if successful else False
        """

        if self.IOTLAB_FRONTEND_BASE_URL in self.iotlab_mote:
            port = self._get_free_port()
            sshtunnel.SSH_TIMEOUT = self.IOTLAB_SSH_TIMEOUT

            server = '{}.{}'.format(self.iotlab_site, self.IOTLAB_FRONTEND_BASE_URL)

            log.info(f'Opening SSH tunnel to: {server}')

            try:
                self.iotlab_tunnel = sshtunnel.open_tunnel(server,
                                                           ssh_username=self.iotlab_user,
                                                           ssh_private_key=self.iotlab_key_file,
                                                           debug_level=self.debug,
                                                           remote_bind_address=(
                                                               self.iotlab_mote, self.IOTLAB_MOTE_TCP_PORT),
                                                           local_bind_address=('0.0.0.0', port))
                self.iotlab_tunnel.start()
            except (sshtunnel.BaseSSHTunnelForwarderError, ValueError):
                log.error("Failed to open ssh tunnel, perhaps invalid credentials? Add '-d' to enable debugging.")
                return False

            time.sleep(0.1)

            log.debug('{}: ssh tunnel started'.format(self.iotlab_mote))

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # self.socket.settimeout(self.IOTLAB_SOCKET_TIMEOUT)
            self.socket.connect(('127.0.0.1', port))

            log.debug('{}: socket connected'.format(self.iotlab_mote))
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.iotlab_mote, self.IOTLAB_MOTE_TCP_PORT))

        return True
