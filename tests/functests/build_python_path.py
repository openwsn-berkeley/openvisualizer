# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

"""
Helper module to fix the Python path.

There are different ways to run the OpenVisualizer:
- from SCons (e.g. "scons runtui"), in which case the project is run from the openvisualizer/ root directory
- by double-clicking on the python files, e.g. opentui.py, in which case, the program is run from
the openvisualizer/bin/ directory.

The function below ensures that, if the program is run by double-clicking, the Python PATH is set up correctly.
"""

import os
import sys


def update_path():
    """
    This function determines whether the program is run from SCons or from the source file. In the former case,
    the path is already set up correctly. In the latter case, this function adjusts the path.
    """

    # do NOT update if running from SCons
    # TODO: this method is relatively fragile

    ui_file = sys.argv[-1]
    print ui_file

    if ui_file.startswith('functests'):
        sys.path.insert(0, os.path.join('..'))
    elif 'test_' in ui_file:
        sys.path.insert(0, os.path.join('..', '..'))  # root


update_path()
