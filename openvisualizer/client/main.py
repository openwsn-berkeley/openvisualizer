import errno
import logging
import socket
import time
import xmlrpclib

import click

from openvisualizer.client.plugins.plugin import Plugin


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
            datefmt='%H:%M:%S'
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
def get_motes(proxy):
    """Print the address and serial-port of each mote connected to the Openvisualizer server."""

    try:
        mote_dict = proxy.rpc_server.get_mote_dict()
    except socket.error as err:
        if errno.ECONNREFUSED:
            click.secho("Connection refused. Is server running?", fg='red')
        else:
            click.echo(err)
    else:
        click.secho("Attached motes:", bold=True, underline=True)
        for addr, port in mote_dict.items():
            click.echo(" - {}\t [{}]".format(addr, port))


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
        click.secho("A fault occurred: {}".format(err.faultString), fg='red')
    else:
        for a in addresses:
            click.echo("Booting mote: {} ... ".format(a), nl=False)
            click.secho("Ok!", bold=True, fg='green')


@click.command()
@click.argument("port_or_address", nargs=1, type=str)
@pass_proxy
def root(proxy, port_or_address):
    """Set a mote as dagroot."""

    try:
        _ = proxy.rpc_server.set_root(port_or_address)
    except socket.error as err:
        if errno.ECONNREFUSED:
            click.secho("Connection refused. Is server running?", fg='red')
        else:
            click.echo(err)
        return
    except xmlrpclib.Fault as err:
        click.secho("Something went wrong -- {}".format(err.faultString), fg='red')
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


def start_view(plugins, proxy, mote, refresh_rate, graphic=None):
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
@pass_plugins
@pass_proxy
def macstats(proxy, plugins, mote, refresh_rate):
    start_view(plugins, proxy, mote, refresh_rate)


@click.command()
@click.option('--refresh-rate', default=1.0, help='Set the refresh rate of the view (in seconds)', type=float,
              show_default=True)
@click.option('--graphic', is_flag=True, help='Enables a graphic view of pktqueue')
@click.argument("mote", nargs=1, type=str)
@pass_plugins
@pass_proxy
def pktqueue(proxy, plugins, mote, graphic, refresh_rate):
    start_view(plugins, proxy, mote, refresh_rate, graphic)


@click.command()
@click.option('--refresh-rate', default=1.0, help='Set the refresh rate of the view (in seconds)', type=float,
              show_default=True)
@click.argument("mote", nargs=1, type=str)
@pass_plugins
@pass_proxy
def schedule(proxy, plugins, mote, refresh_rate):
    start_view(plugins, proxy, mote, refresh_rate)


@click.command()
@click.option('--refresh-rate', default=1.0, help='Set the refresh rate of the view (in seconds)', type=float,
              show_default=True)
@click.argument("mote", nargs=1, type=str)
@pass_plugins
@pass_proxy
def motestatus(proxy, plugins, mote, refresh_rate):
    start_view(plugins, proxy, mote, refresh_rate)


@click.command()
@click.option('--refresh-rate', default=1.0, help='Set the refresh rate of the view (in seconds)', type=float,
              show_default=True)
@click.argument("mote", nargs=1, type=str)
@pass_plugins
@pass_proxy
def msf(proxy, plugins, mote, refresh_rate):
    start_view(plugins, proxy, mote, refresh_rate)


cli.add_command(shutdown)
cli.add_command(list_methods)
cli.add_command(get_motes)
cli.add_command(boot)
cli.add_command(root)
cli.add_command(view)

view.add_command(macstats)
view.add_command(pktqueue)
view.add_command(schedule)
view.add_command(motestatus)
view.add_command(msf)
