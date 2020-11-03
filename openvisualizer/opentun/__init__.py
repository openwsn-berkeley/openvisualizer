import sys

from . import opentunnull  # noqa: F401

if sys.platform.startswith('win32'):
    from . import opentunwindows  # noqa: F401

if sys.platform.startswith('linux'):
    from . import opentunlinux  # noqa: F401

if sys.platform.startswith('darwin'):
    from . import opentunmacos  # noqa: F401
