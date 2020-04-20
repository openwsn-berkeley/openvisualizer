# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

"""
Standalone script to generate the StackDefines.py file.

This script extracts all the information it needs from the openwsn.h
header file (part of the openwsn-fw repository), and generate the
StackDefines.py file (part of the openwsn-sw repository).

To run it, just double-click on this file.

To have to check out the openwsn-fw and openwsn-sw side-by-side, i.e.
you should have a directory with two subdirectories openwsn-fw/ and
openwsn-sw/ somewhere on your computer.

.. moduleauthor:: Thomas Watteyne <watteyne@eecs.berkeley.edu>
                   August 2010
"""

import os
import re
import time

# ============================ defines =========================================

INPUT_FILE = os.path.join('../..', '..', '..', 'openwsn-fw', 'inc', 'opendefs.h')
INPUT_FILE_SIXTOP = os.path.join('../..', '..', '..', 'openwsn-fw', 'openstack', '02b-MAChigh', 'sixtop.h')
OUTPUT_FILE = 'StackDefines.py'


# ============================ helpers =========================================

def gen_component_codes():
    # find component codes in opendefs.h
    codes_found = []
    for line in open(INPUT_FILE, 'r'):
        m = re.search('\s*COMPONENT_(\S*)\s*=\s*(\S*),\s*', line)
        if m:
            name = m.group(1)
            try:
                code = int(m.group(2), 16)
            except ValueError:
                print "WARNING: {0} is not a hex number".format(m.group(2))
            else:
                codes_found.append((code, name))

    # turn into text
    output = ["components = {"]
    output += ["{0:>4}: \"{1}\",".format(a, b) for (a, b) in codes_found]
    output += ["}"]
    output = '\n'.join(output)

    return output


def gen_error_descriptions():
    # find error codes in opendefs.h
    codes_found = []
    for line in open(INPUT_FILE, 'r'):
        m = re.search('\s*ERR_\S*\s*=\s*(\S*),\s*//\s*([\S\s]*)', line)
        if m:
            desc = m.group(2).strip()
            try:
                code = int(m.group(1), 16)
            except ValueError:
                print "WARNING: {0} is not a hex number".format(m.group(2))
            else:
                codes_found.append((code, desc))

    # turn into text
    output = ["errorDescriptions = {"]
    output += ["{0:>4}: \"{1}\",".format(a, b) for (a, b) in codes_found]
    output += ["}"]
    output = '\n'.join(output)

    return output


def gen_sixtop_return_codes():
    # find sixtop return codes in sixtop.h
    codes_found = []
    for line in open(INPUT_FILE_SIXTOP, 'r'):
        m = re.search('\s*#define\s*IANA_6TOP_RC_(\S*)\s*(\S*)\s*\S*\s*(\S*)\s*\S*\s*[\S\s]*', line)
        if m:
            name = m.group(3)
            try:
                code = int(m.group(2), 16)
            except ValueError:
                print "WARNING: {0} is not a hex number".format(m.group(2))
            else:
                codes_found.append((code, name))

    # turn into text
    output = ["sixtop_returncode = {"]
    output += ["{0:>4}: \"{1}\",".format(a, b) for (a, b) in codes_found]
    output += ["}"]
    output = '\n'.join(output)

    return output


def gen_sixtop_state_machine():
    # find sixtop state codes in sixtop.h
    codes_found = []
    for line in open(INPUT_FILE_SIXTOP, 'r'):
        m = re.search('\s*SIX_STATE_(\S*)\s*=\s*(\S*),\s*', line)
        if m:
            name = m.group(1)
            try:
                code = int(m.group(2), 16)
            except ValueError:
                print "WARNING: {0} is not a hex number".format(m.group(2))
            else:
                codes_found.append((code, name))

    # turn into text
    output = ["sixtop_statemachine = {"]
    output += ["{0:>4}: \"{1}\",".format(a, b) for (a, b) in codes_found]
    output += ["}"]
    output = '\n'.join(output)

    return output


# ============================ main ============================================

def main():
    # check if we can access the opendefs.h and sixtop file
    if os.path.exists(INPUT_FILE) and os.path.exists(INPUT_FILE_SIXTOP):

        # gather the information
        output = []
        output += ["# DO NOT EDIT DIRECTLY!"]
        output += ["# This file was generated automatically by GenStackDefines.py"]
        output += ["# on {0}".format(time.strftime("%a, %d %b %Y %H:%M:%S"))]
        output += ["#"]
        output += [""]
        output += [gen_component_codes()]
        output += [""]
        output += [gen_error_descriptions()]
        output += [""]
        output += [gen_sixtop_return_codes()]
        output += [""]
        output += [gen_sixtop_state_machine()]
        output += [""]
        output = '\n'.join(output)

        # write to file
        file = open(OUTPUT_FILE, 'w')
        file.write(output)
        file.close()

        print "{0} created successfully.".format(OUTPUT_FILE)

    else:
        # we can NOT access the openwsn.h file

        # print error message
        output = []
        output += ["ERROR: could not open the following file"]
        output += ["   {0}".format(INPUT_FILE)]
        output += [""]
        output += ["Do you have the openwsn-fw and openwsn-sw repositories"]
        output += ["checked out side-by-side?"]
        output = '\n'.join(output)
        print output

    raw_input('\nScript ended. Press enter to close.')


if __name__ == '__main__':
    main()
