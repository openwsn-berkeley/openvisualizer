#!/usr/bin/env python3

import logging
import time

import click

from openvisualizer.motehandler.moteprobe.emulatedmoteprobe import EmulatedMoteProbe
from openvisualizer.motehandler.moteprobe.serialmoteprobe import SerialMoteProbe
from openvisualizer.motehandler.moteprobe.serialtester import SerialTester
from openvisualizer.simulator.simengine import SimEngine


@click.command()
@click.argument('port', required=True, nargs=1, type=str)
@click.option('--baudrate', default=115200, show_default=True, help='Specify baudrate')
@click.option('--verbose', is_flag=True, help='Enable debug output from serialtester')
@click.option('-r', '--runs', default=100, show_default=True, help='Test iterations')
@click.option('-l', '--pktlen', default=100, show_default=True, help='Length of the echo packet')
@click.option('-t', '--timeout', default=2, show_default=True, help='Timeout on echo reception (in seconds)')
def cli(port, baudrate, verbose, runs, pktlen, timeout):
    """ Serial Tester tool """

    click.secho("Serial Tester Script...", bold=True)

    if port.lower().startswith('emulated'):
        is_simulated = True
        simulator = SimEngine(1)
        smp = EmulatedMoteProbe(simulator.mote_interfaces[0])
        simulator.start()
    else:
        is_simulated = False
        smp = SerialMoteProbe(port=port, baudrate=baudrate)

    while smp.serial is None:
        time.sleep(0.1)

    tester = SerialTester(smp)

    tester.set_num_test_pkt(runs)
    tester.set_test_pkt_length(pktlen)
    tester.set_timeout(timeout)

    # wait until booted
    if is_simulated:
        click.echo('Waiting for booting node')
        time.sleep(2)

    # start test
    click.secho("\nTest Setup:", bold=True)
    click.secho("----------------")
    click.secho("Iterations: {:>6}".format(runs))
    click.secho("Packet length: {:>3}".format(pktlen))
    click.secho("Echo timeout: {:>4}".format(timeout))

    click.echo('\n\nStart test...')
    tester.test(blocking=True)

    res = tester.get_stats()
    click.secho("\n\nTest Statistics:", bold=True)
    click.secho("----------------")
    click.secho("Pkts send: {:>8}".format(res['numSent']))
    click.secho("Echo success: {:>5}".format(res['numOk']), fg='green')
    click.secho("Echo timeout: {:>5}".format(res['numTimeout']), fg='yellow')
    click.secho("Echo corrupted: {:>3}".format(res['numCorrupted']), fg='red')

    click.secho("\nKill with Ctrl-C.\n")

    smp.close()
    smp.join()


if __name__ == "__main__":
    cli()
