import os
import sys

from openvisualizer import appdirs


def force_slash_sep(ospath, debug):
    """
    Converts a Windows-based path to use '/' as the path element separator.
    :param ospath: A relative or absolute path for the OS on which this process is running
    :param debug: If true, print extra logging info
    """

    if os.sep == '/':
        return ospath

    head = ospath
    path_list = []
    while True:
        head, tail = os.path.split(head)
        if tail == '':
            path_list.insert(0, head.rstrip('\\'))
            break
        else:
            path_list.insert(0, tail)

    path_str = '/'.join(path_list)
    if debug:
        print path_str
    return path_str


def init_external_dirs(appdir, debug):
    """
    Find and define conf_dir for config files and data_dir for static data. Also
    return log_dir for logs. There are several possiblities, searched in the order
    described below.

    1. Provided from command line, appdir parameter
    2. In the directory containing openvisualizer_app.py
    3. In native OS site-wide config and data directories
    4. In the openvisualizer package directory

    The directories differ only when using a native OS site-wide setup.

    :param debug: If true, print extra logging info
    :returns: 3-Tuple with config dir, data dir, and log dir
    :raises: RuntimeError if files/directories not found as expected
    """
    if not appdir == '.':
        if not _verify_conf_path(appdir):
            raise RuntimeError('Config file not in expected directory: {0}'.format(appdir))
        if debug:
            print 'App data found via appdir'
        return appdir, appdir, appdir

    file_dir = os.path.dirname(__file__)
    if _verify_conf_path(file_dir):
        if debug:
            print 'App data found via openvisualizer_app.py'
        return file_dir, file_dir, file_dir

    conf_dir = appdirs.site_config_dir('openvisualizer', 'OpenWSN')
    # Must use system log dir on Linux since running as superuser.
    linux_log_dir = '/var/log/openvisualizer'
    if _verify_conf_path(conf_dir):
        if not sys.platform.startswith('linux'):
            raise RuntimeError('Native OS external directories supported only on Linux')

        data_dir = appdirs.site_data_dir('openvisualizer', 'OpenWSN')
        log_dir = linux_log_dir
        if os.path.exists(data_dir):
            if not os.path.exists(log_dir):
                os.mkdir(log_dir)
            if debug:
                print 'App data found via native OS'
            return conf_dir, data_dir, log_dir
        else:
            raise RuntimeError('Cannot find expected data directory: {0}'.format(data_dir))

    data_dir = os.path.join(os.path.dirname(u.__file__), 'data')
    if _verify_conf_path(data_dir):
        if sys.platform == 'win32':
            log_dir = appdirs.user_log_dir('openvisualizer', 'OpenWSN', opinion=False)
        else:
            log_dir = linux_log_dir
        if not os.path.exists(log_dir):
            # Must make intermediate directories on Windows
            os.makedirs(log_dir)
        if debug:
            print 'App data found via openvisualizer package'

        return data_dir, data_dir, log_dir
    else:
        raise RuntimeError('Cannot find expected data directory: {0}'.format(data_dir))


def _verify_conf_path(conf_dir):
    """ Returns True if OpenVisualizer conf files exist in the provided directory. """
    conf_path = os.path.join(conf_dir, 'openvisualizer.conf')
    return os.path.isfile(conf_path)
