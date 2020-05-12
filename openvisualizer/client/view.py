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

    def __init__(self, proxy, mote_id, refresh_rate=1, host='localhost', port=9000):
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
                    time.sleep(0.5)
                else:
                    logging.critical("Unknown socket error")
                    print(self.term.home + self.term.red_on_black + err)
                    self.spin_block()
            else:
                self.render(mote_state)
                time.sleep(self.refresh_rate)

        logging.info("Returning from thread")

    @abstractmethod
    def render(self, ms):
        raise NotImplementedError()

    def close(self):
        logging.info("Closing thread")
        self.quit = True

    def spin_block(self):
        while True:
            time.sleep(1)

    def print_banner(self):
        w = self.term.width
        time = "last update: " + datetime.datetime.now().strftime("%H:%M:%S")
        print(self.term.bold_white_on_seagreen + '[{}]'.format(self.title) + self.term.normal, end='')
        print(self.term.white_on_seagreen + time.rjust(w - int(len(time) / 2)), end='')
        print(self.term.clear_eol() + self.term.normal + '\n')

    def print_connrefused_msg(self):
        w = self.term.width
        msg = "connection failed"
        print(self.term.home + self.term.clear())
        print(self.term.home + self.term.bold_white_on_indianred + '[{}]'.format(self.title), end='')
        print(msg.rjust(w - 10), end='')
        print(self.term.clear_eol() + self.term.normal + '\n')
