import sys

import opentunnull  # noqa: F401

if sys.platform.startswith('win32'):
    import opentunwindows  # noqa: F401

if sys.platform.startswith('linux'):
    import opentunlinux  # noqa: F401

if sys.platform.startswith('darwin'):
    import opentunmacos  # noqa: F401
