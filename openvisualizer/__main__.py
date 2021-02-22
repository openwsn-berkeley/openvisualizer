import logging
import logging.config
import os
import signal
import sys
from collections import namedtuple
from configparser import SafeConfigParser
from typing import Optional
from xmlrpc.server import SimpleXMLRPCServer

import appdirs
import click
import coloredlogs
import pkg_resources as pkg_rs

from openvisualizer import APPNAME, PACKAGE_NAME, DEFAULT_LOGGING_CONF, WINDOWS_COLORS, UNIX_COLORS, VERSION
from openvisualizer.server import OpenVisualizer

server_object: Optional[OpenVisualizer] = None


def sigint_handler(sig, frame):
    if server_object is not None:
        server_object.shutdown()


signal.signal(signal.SIGINT, sigint_handler)

log = logging.getLogger('Main')

ServerConfig = namedtuple('ServerConfig',
                          [
                              'host',
                              'port',
                              'wireshark_debug',
                              'tun',
                              'lconf',
                              'page_zero',
                              'mqtt_broker',
                              'root'
                          ])

pass_config = click.make_pass_decorator(ServerConfig, ensure=True)


class ColoredFormatter(coloredlogs.ColoredFormatter):
    """ Class that matches coloredlogs.ColoredFormatter arguments with logging.Formatter """

    def __init__(self, fmt=None, datefmt=None, style=None):
        self.parser = SafeConfigParser()

        if sys.platform.startswith('win32'):
            log_colors_conf = pkg_rs.resource_filename(PACKAGE_NAME, WINDOWS_COLORS)
        else:
            log_colors_conf = pkg_rs.resource_filename(PACKAGE_NAME, UNIX_COLORS)

        self.parser.read(log_colors_conf)

        ls = self.parse_section('levels', 'keys')
        fs = self.parse_section('fields', 'keys')

        coloredlogs.ColoredFormatter.__init__(self, fmt=fmt, datefmt=datefmt, level_styles=ls, field_styles=fs)

    def parse_section(self, section, option):
        dictionary = {}

        if not self.parser.has_section(section) or not self.parser.has_option(section, option):
            log.warning('Unknown section {} or option {}'.format(section, option))
            return dictionary

        subsections = map(str.strip, self.parser.get(section, option).split(','))

        for subsection in subsections:
            if not self.parser.has_section(str(subsection)):
                log.warning('Unknown section name: {}'.format(subsection))
                continue

            dictionary[subsection] = {}
            options = self.parser.options(subsection)

            for opt in options:
                res = self.parse_options(subsection, opt.strip().lower())
                if res is not None:
                    dictionary[subsection][opt] = res

        return dictionary

    def parse_options(self, section, option):
        res = None
        if option == 'bold' or option == 'faint':
            try:
                return self.parser.getboolean(section, option)
            except ValueError:
                log.error('Illegal value: {} for option: {}'.format(self.parser.get(section, option), option))
        elif option == 'color':
            try:
                res = self.parser.getint(section, option)
            except ValueError:
                res = self.parser.get(section, option)
        else:
            log.warning('Unknown option name: {}'.format(option))

        return res


@click.group(invoke_without_command=True)
@click.option('--host', default='localhost', help='Specify address of the OpenVisualizer server', show_default=True)
@click.option('--port', default=9000, help='Specify to port to use', show_default=True)
@click.option('--version', is_flag=True, help='Print version information OpenVisualizer')
@click.option('--tun', is_flag=True, help="Enable the TUN interface")
@click.option('--wireshark-debug', is_flag=True, help="Enable wireshark debugging")
@click.option('--lconf', default=pkg_rs.resource_filename(PACKAGE_NAME, DEFAULT_LOGGING_CONF),
              help="Provide a logging configuration")
@click.option('--page-zero', is_flag=True, help="Uses page number 0 in page dispatch (only works with single hop)")
@click.option('--mqtt-broker', default=None, type=str, help='Specify address MQTT server for network stats.')
@click.option('--root', type=str, help='Mark a mote as DAGroot, e.g. /dev/ttyUSB* or COM*')
@click.pass_context
def cli(ctx, host, port, version, wireshark_debug, tun, lconf, page_zero, mqtt_broker, root):
    banner = [""]
    banner += [" ___                 _ _ _  ___  _ _ "]
    banner += ["| . | ___  ___ ._ _ | | | |/ __>| \\ |"]
    banner += ["| | || . \\/ ._>| ' || | | |\\__ \\|   |"]
    banner += ["`___'|  _/\\___.|_|_||__/_/ <___/|_\\_|"]
    banner += ["     |_|                  openwsn.org"]
    banner += [""]

    click.secho('\n'.join(banner))

    if version:
        click.echo(f"OpenVisualizer (server) v{VERSION}")
        sys.exit(0)

    if ctx.invoked_subcommand is None:
        click.echo('Use one of the following subcommands: ', nl=False)
        click.secho('hardware, simulation, iotlab, or testbed', bold=True)
        sys.exit(0)

    if tun and os.name == 'posix' and not os.getuid() == 0:
        res = click.prompt("TUN requires admin privileges, (C)ontinue without privileges and with TUN or (A)bort",
                           default="A")
        if res != "C":
            sys.exit(0)

    # create directories to store logs and application data
    try:
        os.makedirs(appdirs.user_log_dir(APPNAME))
    except OSError as err:
        if err.errno != 17:
            log.critical(err)
            return

    try:
        os.makedirs(appdirs.user_data_dir(APPNAME))
    except OSError as err:
        if err.errno != 17:
            log.critical(err)
            return

    ctx.obj = ServerConfig(host, port, wireshark_debug, tun, lconf, page_zero, mqtt_broker, root)
    load_logging_conf(ctx.obj)


@click.command()
@click.option('--baudrate', default=['115200'], help='A list of baudrates to test', show_default=True)
@click.option('--port_mask', help='Define a port mask for probing hardware, e.g., /dev/ttyUSB*')
@pass_config
def hardware(config, baudrate, port_mask):
    """ OpenVisualizer in hardware mode."""

    start_server(OpenVisualizer(config, OpenVisualizer.Mode.HARDWARE, baudrate=baudrate, port_mask=port_mask), config)


@click.command()
@pass_config
@click.argument('num_of_motes', nargs=1, type=int)
@click.option('--topology', default='fully-meshed', help='Specify the simulation topology', show_default=True)
def simulation(config, num_of_motes, topology):
    """ OpenVisualizer in simulation mode."""

    start_server(
        OpenVisualizer(config, OpenVisualizer.Mode.SIMULATION, num_of_motes=num_of_motes, topology=topology), config)


@click.command()
@pass_config
def testbed(config):
    """ Attaches OpenVisualizer to the opentestbed. """
    pass
    # TODO: need to verify
    click.secho("Temporarily disabled")
    # start_server(OpenVisualizer(config, OpenVisualizer.Mode.TESTBED), config)


@click.command()
@pass_config
def iotlab(config):
    """ Attaches OpenVisualizer to IoT-LAB."""
    pass
    # TODO: need to verify
    click.secho("Temporarily disabled")
    # start_server(OpenVisualizer(config, OpenVisualizer.Mode.IOTLAB), config)


def start_server(server_instance, config):
    global server_object
    server_object = server_instance
    with SimpleXMLRPCServer((config.host, config.port), allow_none=True, logRequests=False,
                            bind_and_activate=False) as server:

        server.allow_reuse_address = True

        server.server_bind()
        server.server_activate()

        server.register_instance(server_instance, allow_dotted_names=False)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def load_logging_conf(config):
    try:
        logging.config.fileConfig(fname=config.lconf, defaults={'log_dir': appdirs.user_log_dir(APPNAME)})
    except IOError as err:
        log.error(f"Failed to load config: {err}")


cli.add_command(hardware)
cli.add_command(simulation)
cli.add_command(testbed)
cli.add_command(iotlab)

if __name__ == "__main__":
    cli()
