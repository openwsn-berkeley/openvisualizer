import sys

import opentunnull

if sys.platform.startswith('win32'):
    import opentunwindows

if sys.platform.startswith('linux'):
    import opentunlinux

if sys.platform.startswith('darwin'):
    import opentunmacos
