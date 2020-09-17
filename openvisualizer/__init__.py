VERSION = '2.0.0'

PACKAGE_NAME = 'openvisualizer'
APPNAME = PACKAGE_NAME


# cannot use os.path.join according to pkg_resources
DEFAULT_LOGGING_CONF = '/'.join(("config", "logging.conf"))
WINDOWS_COLORS = '/'.join(('config', 'colors_win.conf'))
UNIX_COLORS = '/'.join(('config', 'colors_unix.conf'))
