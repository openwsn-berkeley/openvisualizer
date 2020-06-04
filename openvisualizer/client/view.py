from __future__ import print_function

import datetime
import errno
import logging
import socket
import threading
import time
from abc import ABCMeta, abstractmethod
from xmlrpclib import Fault

from blessed import Terminal


class View(threading.Thread):
    __metaclass__ = ABCMeta

    def __init__(self, proxy, mote_id, refresh_rate):
        super(View, self).__init__()

        self.rpc_server = proxy.rpc_server
        self.term = Terminal()
        self.quit = False

        self.refresh_rate = refresh_rate
        self.mote_id = mote_id
        self.title = ''
        self.error_msg = ''

    def run(self):
        while not self.quit:
            try:
                mote_state = self.rpc_server.get_mote_state(self.mote_id)
            except Fault as err:
                logging.error("Caught fault from server")
                self.close()
                self.error_msg = err.faultString
            except socket.error as err:
                if errno.ECONNREFUSED:
                    logging.error("Connection refused error")
                    self.print_connrefused_msg()
                    time.sleep(1)
                else:
                    logging.critical("Unknown socket error")
                    print(self.term.home + self.term.red_on_black + err)
                    View.block()
            else:
                self.render(mote_state)
                time.sleep(self.refresh_rate)

        logging.info("Returning from thread")

    @abstractmethod
    def render(self, ms=None):
        print(self.term.home + self.term.clear())
        print(self.term.home, end='')
        self.print_banner()

    def close(self):
        logging.info("Closing thread")
        self.quit = True

    @staticmethod
    def block():
        while True:
            time.sleep(1)

    def print_banner(self):
        time = datetime.datetime.now().strftime("%H:%M:%S,%f")
        title, meta, ma, ra = self._build_banner()
        print(self.term.home + self.term.bold_white_on_seagreen + title + self.term.normal, end='')
        print(self.term.white_on_seagreen + meta.rjust(ma), end='')
        print(self.term.white_on_seagreen + '{:>{}}'.format(time, ra), end='')
        print(self.term.clear_eol() + self.term.normal + '\n')

    def print_connrefused_msg(self):
        msg = "CONN. REFUSED"
        title, meta, ma, ra = self._build_banner()
        print(self.term.home + self.term.bold_white_on_indianred + title + self.term.normal, end='')
        print(self.term.white_on_indianred + meta.rjust(ma), end='')
        print(self.term.white_on_indianred + '{:>{}}'.format(msg, ra), end='')
        print(self.term.clear_eol() + self.term.normal + '\n')

    def _build_banner(self):
        w = self.term.width
        title = '[{}]'.format(self.title)
        meta_info = 'MOTE-ID: {} -- RR: {}'.format(self.mote_id, self.refresh_rate)
        middle_aligned = abs(int(w / 2) + int(len(meta_info) / 2) - len(title))
        right_aligned = abs(int(w / 2) - int(len(meta_info) / 2))
        return title, meta_info, middle_aligned, right_aligned
