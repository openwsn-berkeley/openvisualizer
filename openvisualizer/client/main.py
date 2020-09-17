import errno
import json
import logging
import socket
import time
import xmlrpclib

import bottle
import click

from openvisualizer.client.plugins.plugin import Plugin
from openvisualizer.client.utils import transform_into_ipv6
from openvisualizer.client.webserver import WebServer
from openvisualizer.motehandler.motestate.motestate import MoteState


class Proxy(object):
    def __init__(self, host, port):
        url = 'http://{}:{}'.format(host, str(port))
        self.rpc_server = xmlrpclib.ServerProxy(url)


pass_proxy = click.make_pass_decorator(Proxy, ensure=True)
pass_plugins = click.make_pass_decorator(Plugin, ensure=True)


@click.group()
@click.option('--server', default='localhost', help='Specify address of the Openvisualizer server')
@click.option('--port', default=9000, help='Specify to port to use')
@click.option('--debug', is_flag=True, help="Enable debugging")
@click.pass_context
def cli(ctx, server, port, debug):
    ctx.obj = Proxy(server, port)
    if debug:
        logging.basicConfig(
            filename='openv-client.log',
            filemode='w',
            level=logging.DEBUG,
            format='%(asctime)s [%(name)s:%(levelname)s] %(message)s',
            datefmt='%H:%M:%S',
        )


@click.command()
@click.confirmation_option()
@pass_proxy
def shutdown(proxy):
    """Shutdown the Openvisualizer server"""

    click.echo("Shutting down Openvisualizer server ...  ", nl=False)
    try:
        proxy.rpc_server.shutdown()
    except socket.error:
        pass
    click.secho("Ok!", fg='green', bold=True)


@click.command()
@pass_proxy
def list_methods(proxy):
    """List all methods supported by the Openvisualizer server."""

    try:
        methods = proxy.rpc_server.system.listMethods()
    except socket.error as err:
        if errno.ECONNREFUSED:
            click.secho("Connection refused. Is server running?", fg='red')
        else:
            click.echo(err)
    else:
        click.secho("List of support calls:", bold=True, underline=True)
        for method in methods:
            if not str(method).startswith("system"):
                click.echo(" - {}".format(method))


@click.command()
@pass_proxy
def wireshark_debug(proxy):
    """ Toggles wireshark debugging. When on it shows packets exchanged in the OpenWSN network in Wireshark. """
    try:
        status = proxy.rpc_server.get_wireshark_debug()
        if status:
            _ = proxy.rpc_server.disable_wireshark_debug()
        else:
            _ = proxy.rpc_server.enable_wireshark_debug()

        click.echo("{} --> {}".format(status, proxy.rpc_server.get_wireshark_debug()))
    except xmlrpclib.Fault as err:
        click.secho("Server fault: {}".format(err.faultString), fg='red')
        return
    except socket.error as err:
        if errno.ECONNREFUSED:
            click.secho("Connection refused. Is server running?", fg='red')
        else:
            click.echo(err)
        return

    click.secho('Ok!', fg='green')


@click.command()
@pass_proxy
def motes(proxy):
    """Print the address and serial-port of each mote connected to the Openvisualizer server."""
    try:
        temp_mote_dict = proxy.rpc_server.get_mote_dict()
        addr_port_dict = {}

        # check if we have all the info resolve the entire IPv6 address
        if None not in temp_mote_dict.values():
            for addr in temp_mote_dict:
                mote_state = proxy.rpc_server.get_mote_state(addr)
                id_manager = json.loads(mote_state[MoteState.ST_IDMANAGER])[0]
                full_addr = transform_into_ipv6(id_manager['myPrefix'][:-9] + '-' + id_manager['my64bID'][:-5])
                addr_port_dict[full_addr] = temp_mote_dict[addr]
        else:
            logging.warning("Not all addresses could be resolved.")

    except socket.error as err:
        if errno.ECONNREFUSED:
            click.secho("Connection refused. Is server running?", fg='red')
        else:
            click.echo(err)
    except xmlrpclib.Fault as err:
        click.secho("Caught server fault -- {}".format(err), fg='red')
    else:
        # if we were unable to resolve all the IPv6 addresses, use the intermediate results
        if len(addr_port_dict) != len(temp_mote_dict):
            addr_port_dict = temp_mote_dict

        i = 0
        port, addr = None, None
        while port is None and i < len(addr_port_dict):
            addr, port = addr_port_dict.items()[i]
            i += 1

        len_addr = len(addr) if addr is not None else 0
        len_port = len(port) if port is not None else 0

        heading = " | {:^{}} | {:^{}} | {:^13} |".format("MOTE ID",
                                                         str(max(15, len_addr)), "PORT",
                                                         str(max(15, len_port)), 'STATUS')

        click.echo("".join([" "] + ["-"] * (len(heading) - 1)))
        click.echo(heading)
        click.echo("".join([" "] + ["-"] * (len(heading) - 1)))
        for addr, port in addr_port_dict.items():
            if port is None:
                click.echo(" | {:^15} | {:^15} | ".format(port, addr), nl='')
                click.secho("{:^13}".format('No response'), fg='red', nl='')
                click.echo(" |")
            else:
                click.echo(" | {:^15} | {:^15} | ".format(addr, port), nl='')
                click.secho("{:^13}".format('Ok!'), fg='green', nl='')
                click.echo(" |")
        click.echo("".join([" "] + ["-"] * (len(heading) - 1)))


@click.command()
@click.option('--mote', default='all', help='Specify the mote(s) to (re)boot', show_default=True, type=str)
@pass_proxy
def boot(proxy, mote):
    """Boot motes attached to Openvisualizer."""
    addresses = mote.split(',')
    try:
        _ = proxy.rpc_server.boot_motes(addresses)
    except socket.error as err:
        if errno.ECONNREFUSED:
            click.secho("Connection refused. Is server running?", fg='red')
        else:
            click.echo(err)
    except xmlrpclib.Fault as err:
        click.secho("Caught server fault -- {}".format(err.faultString), fg='red')
    else:
        for a in addresses:
            click.echo("Booting mote: {} ... ".format(a), nl=False)
            click.secho("Ok!", bold=True, fg='green')


@click.command()
@click.option('--rpc-host', default='localhost', help='Host address for webserver', show_default=True)
@click.option('--rpc-port', default='9000', help='Port number for webserver', show_default=True)
@click.option('--web-host', default='localhost', help='Host address for webserver', show_default=True)
@click.option('--web-port', default='8080', help='Port number for webserver', show_default=True)
@click.option('--debug', default='DEBUG', help='provide debug level [DEBUG, INFO, WARNING, ERROR, CRITICAL]',
              show_default=True)
def web(rpc_host, rpc_port, web_port, web_host, debug):
    """ Start a web server which acts as an RPC client for OpenVisualizer Server."""

    bottle_server = bottle.Bottle()

    WebServer(bottle_server, (rpc_host, rpc_port), debug)

    if debug != 'DEBUG':
        bottle.debug(False)
        bottle_server.run(host=web_host, port=web_port, quiet=True)
    else:
        bottle.debug(True)
        bottle_server.run(host=web_host, port=web_port)


@click.command()
@click.argument("port_or_address", nargs=1, type=str, required=False)
@pass_proxy
def root(proxy, port_or_address):
    """Set a mote as dagroot or get the current's DAG root address."""

    if port_or_address is None:
        try:
            dag_root = proxy.rpc_server.get_dagroot()

            if dag_root is None:
                click.echo("No DAG root configured\n")
                click.echo(click.get_current_context().get_help())
                return

            dag_root = "".join('%02x' % b for b in dag_root)
            mote_state = proxy.rpc_server.get_mote_state(dag_root)
        except socket.error as err:
            if errno.ECONNREFUSED:
                click.secho("Connection refused. Is server running?", fg='red')
            else:
                click.echo(err)
            return
        except xmlrpclib.Fault as err:
            click.secho("Caught server fault -- {}".format(err.faultString), fg='red')
        else:
            id_manager = json.loads(mote_state[MoteState.ST_IDMANAGER])[0]

            click.echo('Current DAG root: {}'.format(
                transform_into_ipv6(id_manager['myPrefix'][:-9] + '-' + id_manager['my64bID'][:-5])))

    else:
        try:
            _ = proxy.rpc_server.set_root(port_or_address)
        except socket.error as err:
            if errno.ECONNREFUSED:
                click.secho("Connection refused. Is server running?", fg='red')
            else:
                click.echo(err)
            return
        except xmlrpclib.Fault as err:
            click.secho("Caught server fault -- {}".format(err.faultString), fg='red')
            click.secho("\nMake sure the motes are booted and provide a 16B mote address or a port ID to set the DAG "
                        "root.", fg='red')
            return

        click.secho('Ok!', fg='green', bold=True)


@click.group(invoke_without_command=True)
@click.option('--list', is_flag=True, help='List all the supported view plugins')
@pass_plugins
def view(plugins, list):
    """ Display characteristics of the mesh network. """
    if list:
        click.secho("List all view plugins:", bold=True, underline=True)
        for plugin in plugins.views.keys():
            click.echo(" - {}".format(plugin))

    elif click.get_current_context().invoked_subcommand is None:
        click.echo(click.get_current_context().get_help())


def start_view(proxy, mote, refresh_rate, graphic=None):
    subcommand_name = click.get_current_context().info_name

    if graphic is not None:
        view_thread = Plugin.views[subcommand_name](proxy, mote, refresh_rate, graphic)
    else:
        view_thread = Plugin.views[subcommand_name](proxy, mote, refresh_rate)

    view_thread.daemon = True
    logging.info("Calling {} view thread from main client".format(subcommand_name))
    view_thread.start()

    try:
        while not view_thread.quit:
            time.sleep(0.5)
    except KeyboardInterrupt:
        view_thread.close()

    logging.info("Joining {} view thread from main client".format(subcommand_name))
    view_thread.join()

    if view_thread.error_msg != '':
        click.secho(view_thread.error_msg, fg='red')


@click.command()
@click.argument("mote", nargs=1, type=str)
@click.option('--refresh-rate', default=1.0, help='Set the refresh rate of the view (in seconds)', type=float,
              show_default=True)
@pass_proxy
def macstats(proxy, mote, refresh_rate):
    start_view(proxy, mote, refresh_rate)


@click.command()
@click.option('--refresh-rate', default=1.0, help='Set the refresh rate of the view (in seconds)', type=float,
              show_default=True)
@click.option('--graphic', is_flag=True, help='Enables a graphic view of pktqueue')
@click.argument("mote", nargs=1, type=str)
@pass_proxy
def pktqueue(proxy, mote, graphic, refresh_rate):
    start_view(proxy, mote, refresh_rate, graphic)


@click.command()
@click.option('--refresh-rate', default=1.0, help='Set the refresh rate of the view (in seconds)', type=float,
              show_default=True)
@click.argument("mote", nargs=1, type=str)
@pass_proxy
def schedule(proxy, mote, refresh_rate):
    start_view(proxy, mote, refresh_rate)


@click.command()
@click.option('--refresh-rate', default=1.0, help='Set the refresh rate of the view (in seconds)', type=float,
              show_default=True)
@click.argument("mote", nargs=1, type=str)
@pass_proxy
def motestatus(proxy, mote, refresh_rate):
    start_view(proxy, mote, refresh_rate)


@click.command()
@click.option('--refresh-rate', default=1.0, help='Set the refresh rate of the view (in seconds)', type=float,
              show_default=True)
@click.argument("mote", nargs=1, type=str)
@pass_proxy
def msf(proxy, mote, refresh_rate):
    start_view(proxy, mote, refresh_rate)


@click.command()
@click.option('--refresh-rate', default=1.0, help='Set the refresh rate of the view (in seconds)', type=float,
              show_default=True)
@click.argument("mote", nargs=1, type=str)
@pass_proxy
def neighbors(proxy, mote, refresh_rate):
    start_view(proxy, mote, refresh_rate)


cli.add_command(shutdown)
# cli.add_command(list_methods)
cli.add_command(wireshark_debug)
cli.add_command(motes)
cli.add_command(boot)
cli.add_command(root)
cli.add_command(view)

view.add_command(macstats)
view.add_command(pktqueue)
view.add_command(schedule)
view.add_command(motestatus)
view.add_command(msf)
view.add_command(neighbors)
view.add_command(web)
