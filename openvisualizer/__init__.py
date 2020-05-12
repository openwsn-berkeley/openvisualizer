import os

VERSION = '2.0.0'

PACKAGE_NAME = 'openvisualizer'

FW_DEFINITIONS = os.path.join(os.environ['OPENWSN_FW_BASE'], 'inc', 'opendefs.h')
FW_SIXTOP_DEFINITIONS = os.path.join(os.environ['OPENWSN_FW_BASE'], 'openstack', '02b-MAChigh', 'sixtop.h')

DEFAULT_LOGGING_CONF = os.path.join("config", "logging.conf")
WINDOWS_COLORS = os.path.join('config', 'colors_win.conf')
UNIX_COLORS = os.path.join('config', 'colors_unix.conf')
