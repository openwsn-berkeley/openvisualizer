import logging
import os
import time
from subprocess import Popen

from pytest import mark, param

LOG_FILE = 'openv-server.log'

logger = logging.getLogger(__name__)


@mark.parametrize('option, logs',
                  [('', ['Discovered serial-port(s):']),  # testing plain openv-server boot (1)
                   ('--sim=2',  # boot openv-server with 2 emulated motes (2)
                    ['- simulation              = 2',
                     '- simulation topology     = Pister-hack',
                     '- auto-boot sim motes     = True',
                     '[OPENWSN] booted']),
                   # verify emulated moted do not boot
                   param('--sim=2 --no-boot', ['[OPENWSN] booted'], marks=mark.xfail(reason='motes not booted')),
                   ('--simtopo=linear',  # specify a simulation topology but do not set a number of emulated motes (3)
                    ['Simulation topology specified but no --sim=<x> given, switching to hardware mode',
                     'Discovered serial-port(s):']),
                   ('--sim=5 --root=0001',  # set simulation with five motes and specify root mote (4)
                    ['Setting mote 0001 as root',
                     '- simulation topology     = Pister-hack',
                     '- auto-boot sim motes     = True',
                     '- simulation              = 5']),
                   ('--sim=2 --root=0001 --no-boot',  # do not boot motes but try to set root (5)
                    ['Cannot set root',
                     '- set root                = 0001',
                     '- auto-boot sim motes     = False']),
                   ('--sim=2 --no-boot --load-topology=0002-star.json',  # specify sim options and load topology (6)
                    ['option might be overwritten by the configuration in \'0002-star.json\'']),
                   ])
def test_start_server(option, logs):
    try:
        os.remove(LOG_FILE)
    except OSError:
        logger.warning('Could not remove old log file: {}'.format(LOG_FILE))
        pass
    opts = option.split(' ')
    arguments = ['openv-server']
    if opts != ['']:
        arguments.extend(opts)
    p = Popen(arguments)

    # give the server time to boot
    time.sleep(3)

    # kill server
    p.terminate()

    with open(LOG_FILE, 'r') as f:
        output = "".join(f.readlines())
        for log in logs:
            assert log in output
    assert 'Starting RPC server' in output
