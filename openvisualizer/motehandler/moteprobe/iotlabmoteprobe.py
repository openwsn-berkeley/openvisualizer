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

    def __init__(self, iotlab_mote, iotlab_user=None, iotlab_passwd=None):
        self.iotlab_mote = iotlab_mote

        if self.IOTLAB_FRONTEND_BASE_URL in self.iotlab_mote:
            # Recover user credentials
            self.iotlab_user, self.iotlab_passwd = auth.get_user_credentials(iotlab_user, iotlab_passwd)

            # match the site from the mote's address
            reg = r'[0-9a-zA-Z\-]+-\d+\.([a-z]+)'
            match = re.search(reg, iotlab_mote)
            self.iotlab_site = match.group(1)

        self.iotlab_tunnel = None
        self.socket = None

        # initialize the parent class
        MoteProbe.__init__(self, portname=iotlab_mote)

    # ======================== public ==================================

    @classmethod
    def probe_iotlab_motes(cls, iotlab_motes, iotlab_user, iotlab_passwd):
        mote_probes = []
        probe = None
        log.debug("probing motes: {}".format(iotlab_motes))
        try:
            for mote in iotlab_motes:
                log.debug("probe {}".format(mote))
                try:
                    probe = cls(
                        iotlab_mote=mote,
                        iotlab_user=iotlab_user,
                        iotlab_passwd=iotlab_passwd)
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

    def _rcv_data(self, rx_bytes=1024):
        try:
            return self.socket.recv(rx_bytes)
        except socket.timeout:
            raise MoteProbeNoData

    def _send_data(self, data):
        hdlc_data = self.hdlc.hdlcify(data)
        self.socket.send(hdlc_data)

    def _detach(self):
        if self.socket is not None:
            log.debug('closing socket to {}'.format(self._portname))
            self.socket.close()

        if self.iotlab_tunnel is not None:
            log.debug('stopping ssh tunnel to {}'.format(self._portname))
            self.iotlab_tunnel.stop()

    def _attach(self):
        if hasattr(self, 'iotlab_site'):
            port = self._get_free_port()
            sshtunnel.SSH_TIMEOUT = self.IOTLAB_SSH_TIMEOUT
            self.iotlab_tunnel = sshtunnel.open_tunnel('{}.{}'.format(self.iotlab_site, self.IOTLAB_FRONTEND_BASE_URL),
                                                       ssh_username=self.iotlab_user,
                                                       ssh_password=self.iotlab_passwd,
                                                       remote_bind_address=(
                                                           self.iotlab_mote, self.IOTLAB_MOTE_TCP_PORT),
                                                       local_bind_address=('0.0.0.0', port))
            self.iotlab_tunnel.start()
            time.sleep(0.1)

            log.debug('{}: ssh tunnel started'.format(self.iotlab_mote))

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.IOTLAB_SOCKET_TIMEOUT)
            self.socket.connect(('127.0.0.1', port))

            log.debug('{}: socket connected'.format(self.iotlab_mote))
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.iotlab_mote, self.IOTLAB_MOTE_TCP_PORT))
