#!/usr/bin/env python2

import logging
import time

import os
import signal
import click
import coloredlogs

from openvisualizer.motehandler.moteprobe import serialmoteprobe
from openvisualizer.motehandler.moteprobe.serialmoteprobe import SerialMoteProbe
from openvisualizer.motehandler.moteprobe.iotlabmoteprobe import IotlabMoteProbe
from openvisualizer.motehandler.moteprobe.serialtester import SerialTester

for logger in [logging.getLogger(__name__), serialmoteprobe.log]:
    coloredlogs.install(logger=logger, fmt="%(asctime)s [%(name)s:%(levelname)s] %(message)s", datefmt="%H:%m:%S",
                        level='ERROR')


def serialtest_tracer(msg):
    if '---' in msg:
        click.secho('\n' + msg, fg='blue', bold=True)
    elif 'received' in msg:
        click.secho(msg, fg='green')
    else:
        click.secho(msg)


@click.command()
@click.option('--port', default='/dev/ttyUSB1', show_default=True, help='Serial port to test')
@click.option('--baudrate', default=115200, show_default=True, help='Specify baudrate')
@click.option('--verbose', is_flag=True, help='Enable debug output from serialtester')
@click.option('--iotlab-mote', help='Iotlab mote')
@click.option('--iotlab-user', default=None, help='Iotlab account user')
@click.option( '--iotlab-passwd', default=None, help='Iotlab account password')
@click.option('-r', '--runs', default=100, show_default=True, help='Test iterations')
@click.option('-l', '--pktlen', default=100, show_default=True, help='Length of the echo packet')
@click.option('-t', '--timeout', default=2, show_default=True, help='Timeout on echo reception (in seconds)')
def cli(port, baudrate, iotlab_mote, iotlab_user, iotlab_passwd,
        verbose, runs, pktlen, timeout):
    """ Serial Tester tool """

    click.secho("Serial Tester Script...", bold=True)

    moteprobe = None

    try:
        if iotlab_mote:
            moteprobe = IotlabMoteProbe(
                iotlab_mote=iotlab_mote,
                iotlab_user=iotlab_user,
                iotlab_passwd=iotlab_passwd,
                baudrate=baudrate,
                )
            while moteprobe._socket is None:
                time.sleep(0.1)
        else:
            moteprobe = SerialMoteProbe(port=port, baudrate=baudrate)
            while moteprobe._serial is None:
                time.sleep(0.1)

        logger.info("initialized serial object")

        tester = SerialTester(moteprobe)

        if verbose:
            tester.set_trace(serialtest_tracer)

        tester.set_num_test_pkt(runs)
        tester.set_test_pkt_length(pktlen)
        tester.set_timeout(timeout)

        click.secho("\nTest Setup:", bold=True)
        click.secho("----------------")
        click.secho("Iterations: {:>6}".format(runs))
        click.secho("Packet length: {:>3}".format(pktlen))
        click.secho("Echo timeout: {:>4}".format(timeout))

        click.secho("\nTest Progress:\n")
        # start test
        if verbose:
            tester.test(blocking=True)
        else:
            tester.test(blocking=False)

            with click.progressbar(range(runs)) as bar:
                for x in bar:
                    while tester.stats['numOk'] < x:
                        time.sleep(0.2)

        time.sleep(0.5)
        res = tester.get_stats()
        click.secho("\n\nTest Statistics:", bold=True)
        click.secho("----------------")
        click.secho("Pkts send: {:>8}".format(res['numSent']))
        click.secho("Echo success: {:>5}".format(res['numOk']), fg='green')
        click.secho("Echo timeout: {:>5}".format(res['numTimeout']), fg='yellow')
        click.secho("Echo corrupted: {:>3}".format(res['numCorrupted']), fg='red')
    except KeyboardInterrupt:
        click.secho("\nKeyboard Interrupt, forced exit!")
    finally:
        click.secho("\nexiting...\n")
        if moteprobe:
            moteprobe.close()
            moteprobe.join()
        os.kill(os.getpid(), signal.SIGTERM)


if __name__ == '__main__':
    cli()
