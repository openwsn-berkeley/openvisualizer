# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import os
import re
import signal
import socket
import time
from contextlib import closing

import sshtunnel
from iotlabcli import auth

from moteprobe import MoteProbe, MoteProbeNoData

log = logging.getLogger('MoteProbe')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


# ============================ class ===================================

class IotlabMoteProbe(MoteProbe):
    IOTLAB_SSH_TIMEOUT = 2  # seconds
    IOTLAB_SOCKET_TIMEOUT = 2  # seconds
    IOTLAB_MOTE_TCP_PORT = 20000

    IOTLAB_FRONTEND_BASE_URL = 'iot-lab.info'

    def __init__(self, iotlab_mote, iotlab_user=None, iotlab_passwd=None,
                 iotlab_key_file=None, iotlab_key_pas=None, xonxoff=True):

        self.iotlab_mote = iotlab_mote

        if self.IOTLAB_FRONTEND_BASE_URL in self.iotlab_mote:
            # Recover user credentials
            self.iotlab_user, self.iotlab_passwd = auth.get_user_credentials(
                iotlab_user,
                iotlab_passwd
                )
            # Recover ssh key and password
            self.iotlab_key_file = iotlab_key_file
            self.iotlab_key_pas = iotlab_key_pas
            # match the site from the mote's address
            reg = r'[0-9a-zA-Z\-]+-\d+\.([a-z]+)'
            match = re.search(reg, iotlab_mote)
            self.iotlab_site = match.group(1)
        self._ssh_tunnel = None
        self._socket = None
        self.xonxoff = xonxoff
        self._cts = False

        # initialize the parent class
        MoteProbe.__init__(self, portname=iotlab_mote)

    # ======================== public ==================================

    @classmethod
    def probe_iotlab_motes(cls, iotlab_motes, iotlab_user, iotlab_passwd,
                           iotlab_key_file, iotlab_key_pas):
        mote_probes = []
        probe = None
        log.debug("Probing motes: {}".format(iotlab_motes))
        try:
            for mote in iotlab_motes:
                log.debug("Probe {}".format(mote))
                try:
                    probe = cls(
                        iotlab_mote=mote,
                        iotlab_user=iotlab_user,
                        iotlab_passwd=iotlab_passwd,
                        iotlab_key_file=iotlab_key_file,
                        iotlab_key_pas=iotlab_key_pas,)
                    while probe.socket is None and probe.isAlive():
                        pass
                    if probe.test_serial(pkts=2):
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
        log.success(
            "Discovered following iotlab-motes: {}".format(valid_motes))
        return mote_probes

    @property
    def socket(self):
        return self._socket

    @property
    def ssh_tunnel(self):
        return self._ssh_tunnel

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
            data = self._socket.recv(rx_bytes)
            if self.xonxoff:
                self._set_cts(data)
            return data
        except socket.timeout:
            raise MoteProbeNoData

    def _send_data(self, data):
        hdlc_data = self.hdlc.hdlcify(data)
        hdlc_len = len(bytearray(hdlc_data))
        bytes_written = 0
        while not self.quit and bytes_written != hdlc_len:
            if self.xonxoff and not self._cts:
                continue
            else:
                bytes_written += self._socket.send(hdlc_data)

    def _detach(self):
        if self._socket is not None:
            log.debug('closing socket to {}'.format(self._portname))
            self._socket.close()

        if self._ssh_tunnel is not None:
            log.debug('stopping ssh tunnel to {}'.format(self._portname))
            self._ssh_tunnel.stop()

    def _attach(self):
        if hasattr(self, 'iotlab_site'):
            port = self._get_free_port()
            sshtunnel.SSH_TIMEOUT = self.IOTLAB_SSH_TIMEOUT
            self._ssh_tunnel = sshtunnel.open_tunnel(
                '{}.{}'.format(self.iotlab_site,
                               self.IOTLAB_FRONTEND_BASE_URL),
                ssh_pkey=self.iotlab_key_file,
                ssh_private_key_password=self.iotlab_key_pas,
                ssh_username=self.iotlab_user,
                ssh_password=self.iotlab_passwd,
                remote_bind_address=(self.iotlab_mote,
                                     self.IOTLAB_MOTE_TCP_PORT),
                local_bind_address=('0.0.0.0', port))
            self._ssh_tunnel.start()
            time.sleep(0.1)

            log.debug('{}: ssh tunnel started'.format(self.iotlab_mote))

            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.IOTLAB_SOCKET_TIMEOUT)
            self._socket.connect(('127.0.0.1', port))

            log.debug('{}: socket connected'.format(self.iotlab_mote))
        else:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((self.iotlab_mote, self.IOTLAB_MOTE_TCP_PORT))
