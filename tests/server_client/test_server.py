import logging
import os
import tempfile
import time
from subprocess import Popen

from pytest import mark, param

LOG_FILE = 'openv-server.log'

logger = logging.getLogger(__name__)


@mark.parametrize('option, log',
                  [('', 'discovered following serial-port(s):'),
                   ('--sim=2', '- simulation              = 2'),
                   ('--sim=2', '[OPENWSN] booted'),
                   param('--sim=2 --no-boot', '[OPENWSN] booted', marks=mark.xfail(reason='motes not booted')),
                   ('--sim=2 --root=0001', 'Setting mote 0001 as root'),
                   ('--sim=2 --root=0001 --no-boot', 'Cannot set root')
                   ])
def test_start_server(option, log):
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

    # kill server and remove lock
    p.terminate()
    os.remove(os.path.join(tempfile.gettempdir(), 'openv-server.pid'))

    with open(LOG_FILE, 'r') as f:
        logs = "".join(f.readlines())
        assert log in logs
        assert 'Starting RPC server' in logs
