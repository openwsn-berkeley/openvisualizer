#!/usr/bin/env python2

import logging
import threading

import time
from datetime import timedelta


class NullLogHandler(logging.Handler):
    def emit(self, record):
        pass


log = logging.getLogger('OpenCli')
log.setLevel(logging.DEBUG)
log.addHandler(NullLogHandler())


class OpenCli(threading.Thread):
    """ Base class for the SerialTesterCli class. Thread which handles CLI commands entered by the user.  """

    CMD_LEVEL_USER = "user"
    CMD_LEVEL_SYSTEM = "system"

    def __init__(self, app_name, quit_cb):

        # slot params
        self.startTime = time.time()
        self.app_name = app_name
        self.quit_cb = quit_cb

        # local variables
        self.command_lock = threading.Lock()
        self.commands = []
        self.go_on = True

        # logging

        # initialize parent class
        super(OpenCli, self).__init__()

        # give this thread a name
        self.name = 'OpenCli'

        # register system commands (user commands registers by child object)
        self._register_command_internal(
            self.CMD_LEVEL_SYSTEM,
            'help',
            'h',
            'print this menu',
            [],
            self._handle_help)

        self._register_command_internal(
            self.CMD_LEVEL_SYSTEM,
            'info',
            'i',
            'information about this application',
            [],
            OpenCli._handle_info)
        self._register_command_internal(
            self.CMD_LEVEL_SYSTEM,
            'quit',
            'q',
            'quit this application',
            [],
            self._handle_quit)
        self._register_command_internal(
            self.CMD_LEVEL_SYSTEM,
            'uptime',
            'ut',
            'how long this application has been running',
            [],
            self._handle_uptime)

    def run(self):
        print '{0} - OpenWSN project\n'.format(self.app_name)
        print "Type 'quit' to shutdown\n"

        while self.go_on:

            # CLI stops here each time a user needs to call a command
            params = raw_input('> ')

            # log
            log.debug('Following command entered:' + params)

            params = params.split()
            if len(params) < 1:
                continue

            if len(params) == 2 and params[1] == '?':
                if not self._print_usage_from_name(params[0]):
                    if not self._print_usage_from_alias(params[0]):
                        print ' unknown command or alias \'' + params[0] + '\''
                continue

            # find this command
            found = False
            with self.command_lock:
                for command in self.commands:
                    if command['name'] == params[0] or command['alias'] == params[0]:
                        found = True
                        cmd_params = command['params']
                        cmd_callback = command['callback']
                        break

            # call its callback or print error message
            if found:
                if len(params[1:]) == len(cmd_params):
                    cmd_callback(params[1:])
                else:
                    if not self._print_usage_from_name(params[0]):
                        self._print_usage_from_alias(params[0])
            else:
                print ' unknown command or alias \'' + params[0] + '\''

    # ======================== public ==========================================

    def register_command(self, name, alias, description, params, callback):

        self._register_command_internal(self.CMD_LEVEL_USER, name, alias, description, params, callback)

    # ======================== private =========================================

    def _register_command_internal(self, cmd_level, name, alias, description, params, callback):

        if self._does_command_exist(name):
            raise SystemError("command {0} already exists".format(name))

        with self.command_lock:
            self.commands.append({
                'cmdLevel': cmd_level,
                'name': name,
                'alias': alias,
                'description': description,
                'params': params,
                'callback': callback,
            })

    def _print_usage_from_name(self, command_name):
        return self._print_usage(command_name, 'name')

    def _print_usage_from_alias(self, command_alias):
        return self._print_usage(command_alias, 'alias')

    def _print_usage(self, name, param_type):

        usage_string = None

        with self.command_lock:
            for command in self.commands:
                if command[param_type] == name:
                    usage_string = []
                    usage_string += ['usage: {0}'.format(name)]
                    usage_string += [" <{0}>".format(p) for p in command['params']]
                    usage_string = ''.join(usage_string)

        if usage_string:
            print usage_string
            return True
        else:
            return False

    def _does_command_exist(self, cmd_name):

        return_val = False

        with self.command_lock:
            for cmd in self.commands:
                if cmd['name'] == cmd_name:
                    return_val = True

        return return_val

    # === command handlers (system commands only, a child object creates more)

    def _handle_help(self, params):
        output = []
        output += ['Available commands:']

        with self.command_lock:
            for command in self.commands:
                output += [' - {0} ({1}): {2}'.format(command['name'], command['alias'], command['description'])]

        print '\n'.join(output)

    @staticmethod
    def _handle_info(params):
        output = []
        output += ['General status of the application']
        output += ['']
        output += ['current time: {0}'.format(time.ctime())]
        output += ['']
        output += ['{0} threads running:'.format(threading.activeCount())]

        for t in threading.enumerate():
            output += ['- {0}'.format(t.getName())]

        output += ['']
        output += ['This is thread {0}.'.format(threading.currentThread().getName())]

        print '\n'.join(output)

    def _handle_quit(self, params):

        # call the quit callback
        self.quit_cb()

        # kill this thead
        self.go_on = False

    def _handle_uptime(self, params):

        up_time = timedelta(seconds=time.time() - self.startTime)

        print 'Running since {0} ({1} ago)'.format(
            time.strftime("%m/%d/%Y %H:%M:%S", time.localtime(self.startTime)), up_time)


if __name__ == '__main__':
    def quit_callback():
        print "quitting!"


    def echo_cb(params):
        print "echo {0}!".format(params)


    cli = OpenCli("Standalone Sample App", quit_callback)
    cli.register_command('echo',
                         'e',
                         'echoes the first param',
                         ['string to echo'],
                         echo_cb)
    cli.start()
