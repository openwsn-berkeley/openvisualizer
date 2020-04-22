#!/usr/bin/env python2

# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

"""
Helper module to fix the Python path.

There are different ways to run the OpenVisualizer:
- from SCons (e.g. "scons rungui"), in which case the project is run from the openvisualizer/ root directory
- by double-clicking on the OpenVisualizerGui.py or OpenVisualizerCli.py files, in which case, the program is run from
the openvisualizer\bin\openVisualizerApp directory.

The function below ensure that, if the program is run by double-clicking, the
Python PATH is set up correctly.
"""

import os
import sys


def update_path():
    sys.path.insert(0, os.path.join('..', '..', '..'))  # root


update_path()
