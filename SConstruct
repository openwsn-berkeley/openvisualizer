# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import os
import platform

import SCons
import sconsutils

#============================ banner ==========================================

banner  = [""]
banner += [" ___                 _ _ _  ___  _ _ "]
banner += ["| . | ___  ___ ._ _ | | | |/ __>| \ |"]
banner += ["| | || . \/ ._>| ' || | | |\__ \|   |"]
banner += ["`___'|  _/\___.|_|_||__/_/ <___/|_\_|"]
banner += ["     |_|                  openwsn.org"]
banner += [""]

print '\n'.join(banner)

#============================ SCons environment ===============================

#===== help text

Help('''
Usage:
    scons [options] runtui
    scons copy-simfw
    scons <sdist|upload|sdist-native>
    scons unittests
    scons docs

Targets:
    runov:
        Runs the OpenVisualizer application. The application is run from the build/runui/ directory. By default it does
        not require superuser/administrator privileges.

        Options
          --sim         Run in simulator mode with default count of motes.
          --simCount=n  Run in simulator mode with 'n' motes.
          --pathTopo    Run in simulator mode with data imported from a previous topology saved in a json file.
          --opentun     Use TUN device to route to the Internet (requires superuser privileges, e.g., sudo).
          --host        Specify host to deploy webserver. Default is 'localhost'.
          --port        Specify port on which webserver will listen.
          --simTopo=<linear|fully-meshed>
          --mqtt-broker Specify the address of the mqtt-broker used for logging, e.g., 'argus.paris.inria.fr'.
                        Force a certain topology for simulation.
          --nosimcopy   Skips copying simulation firmware at startup from the openwsn-fw directory.
          --ovdebug     Enable debug mode; more detailed logging
          --usePageZero Use page number 0 in page dispatch of 6lowpan packet (only works within one-hop).

    copy-simfw:
        Copy files for the simulator, generated from an OpenWSN firmware build on this host. Assumes firmware top-level
        directory is '../../../openwsn-fw'.

        Options
          --simhost=<platform-os>
                        Platform and OS for firmware; supports creation of a
                        setup package with multiple variants. Defaults to the
                        platform-OS on which SCons is running. Valid entries:
                        amd64-linux, x86-linux, amd64-windows, x86-windows

    sdist:
        Generate a standard Python source distribution archive (for setup.py) in build{0}dist directory. Installs data
        files to the openvisualizer package directory.

    upload:
        Uploads sdist archive to PyPI. The user must be registered as an Owner or Maintainer of OpenVisualizer.
        The user's PyPI credentials must be stored in their home directory .pypirc file.

    sdist-native:
        Linux only Generate a standard Python source distribution archive (for setup.py) in build{0}dist directory.
        Installs to native directories for the OS on which this command is run. This command *must* be run on a Linux
        host to generate a Linux target archive. Installs data files to /usr/local/share.

    serialtest:
        Runs a serial test on a connected mote.

    unittest:
        Runs unittests of the openvisualizer package.

    docs:
        Generate source documentation in build{0}html directory
'''.format(os.sep))


# Define base environment
env = Environment(
    ENV = {'PATH' : os.environ['PATH']}
)

# Must define with absolute path since SCons construction may occur in a subdirectory via SConscript.
env['ROOT_BUILD_DIR'] = os.path.join(os.getcwd(), 'build')
env['ROOT_PROJECT_DIR'] = os.path.join(os.getcwd())

# External openwsn-fw repository directory. An environment variable makes it easy to change since it depends on the host
# running this script.
env['FW_DIR']         = os.path.join('..', 'openwsn-fw')

def default(env,target,source):
    print SCons.Script.help_text

Default(env.Command('default', None, default))

# Define environment and options common to all run... targets
runnerEnv = env.Clone()

AddOption('--sim',
    dest      = 'simOpt',
    default   = False,
    action    = 'store_true')
runnerEnv['SIMOPT'] = GetOption('simOpt')

AddOption('--simCount',
    dest      = 'simCount',
    default   = 0,
    type      = 'int')
runnerEnv['SIMCOUNT'] = GetOption('simCount')

AddOption('--host',
    dest      = 'host',
    default   = '0.0.0.0',
    type      = 'string')
runnerEnv['HOST'] = GetOption('host')

AddOption('--port',
    dest      = 'port',
    default   = '8080',
    type      = 'int')
runnerEnv['PORT'] = GetOption('port')

AddOption('--trace',
    dest      = 'traceOpt',
    default   = False,
    action    = 'store_true')
runnerEnv['TRACE'] = GetOption('traceOpt')

AddOption('--simTopo',
    dest      = 'simTopology',
    default   = '',
    type      = 'string')
runnerEnv['SIMTOPOLOGY'] = GetOption('simTopology')

AddOption('--pathTopo',
    dest      = 'pathTopo',
    default   = '',
    action    = 'store')
runnerEnv['PATHTOPO'] = GetOption('pathTopo')

AddOption('--nosimcopy',
    dest      = 'simcopyOpt',
    default   = True,
    action    = 'store_true')
runnerEnv['SIMCOPYOPT'] = GetOption('simcopyOpt')

AddOption('--opentestbed',
    dest      = 'opentestbed',
    default   = False,
    action    = 'store_true')
runnerEnv['OPENTESTBED'] = GetOption('opentestbed')

AddOption('--mqtt-broker',
    dest      = 'mqtt_broker',
    default   = '',
    type      = 'string')
runnerEnv['MQTT_BROKER'] = GetOption('mqtt_broker')

AddOption('--opentun',
    dest      = 'opentun',
    default   = False,
    action    = 'store_true')
runnerEnv['OPENTUN'] = GetOption('opentun')

AddOption('--ovdebug',
    dest      = 'debugOpt',
    default   = False,
    action    = 'store_true')
runnerEnv['DEBUGOPT'] = GetOption('debugOpt')

AddOption('--usePageZero',
    dest      = 'usePageZero',
    default   = False,
    action    = 'store_true')
runnerEnv['USEPAGEZERO'] = GetOption('usePageZero')

#============================ SCons targets ===================================

#===== copy-simfw

simhosts = ['amd64-linux','x86-linux','amd64-windows','x86-windows']
if os.name == 'nt':
    defaultIndex = 2 if platform.architecture()[0]=='64bit' else 3
else:
    defaultIndex = 0 if platform.architecture()[0]=='64bit' else 1

AddOption('--simhost',
    dest      = 'simhostOpt',
    default   = simhosts[defaultIndex],
    type      = 'choice',
    choices   = simhosts)

# Must copy SIMHOSTOPT to runner environment since it also reads sconsutils.py.
env['SIMHOSTOPT']       = GetOption('simhostOpt')
runnerEnv['SIMHOSTOPT'] = env['SIMHOSTOPT']

Alias('copy-simfw', sconsutils.copy_simulation_fw(env, 'simcopy'))

#===== runov

# Must define run targets below the copy-simfw target so SIMHOSTOPT is available. Run targets may copy simulation
# firmware before starting.

app_dir = os.path.join('bin')
SConscript(os.path.join(app_dir, 'SConscript'), exports = {"env": runnerEnv})

# Copy variables for data files out of runner environment, to be used in
# dist targets below.
env['CONF_FILES'] = runnerEnv['CONF_FILES']
env['DATA_DIRS']  = runnerEnv['DATA_DIRS']

#===== sdist

def makeTreeSdist(env, target):
    '''
    Creates a target that requires creation of a source distribution. Uses
    the target name as a phony target to force the build. Supports 'sdist' and
    'upload' targets.

    First, copies the data files from the openVisualizerApp directory as data
    for the openvisualizer package. Then creates the source dist archive.
    Cleans up the temporary package data file.
    '''
    datadir = os.path.join('data')
    appdir  = os.path.join('bin')
    distdir = os.path.join('build', 'dist')
    topdir  = os.path.join('.')
    cmdlist = []

    cmdlist.append(Delete(distdir))
    cmdlist.append(Delete(datadir))
    cmdlist.append(Delete('openVisualizer.egg-info'))

    cmdlist.append(Mkdir(datadir))
    cmdlist.append(Copy(os.path.join(datadir, 'requirements.txt'),
                        os.path.join(topdir, 'requirements.txt')))
    for conf in env['CONF_FILES']:
        cmdlist.append(Copy(os.path.join(datadir, conf), os.path.join(appdir, conf)))
    for data in env['DATA_DIRS']:
        cmdlist.append(Copy(os.path.join(datadir, data), os.path.join(appdir, data)))

    sdistLines = ['python setup.py sdist',
                  '--formats=gztar,zip',
                  '--dist-dir {0}'.format(distdir)]
    if target == 'sdist':
        cmdlist.append(' '.join(sdistLines))
    elif target == 'upload':
        # Must first run sdist before upload
        cmdlist.append(' '.join(sdistLines + ['upload']))
    else:
        print 'Target "{0}" not supported'.format(target)

    cmdlist.append(Delete(datadir))
    cmdlist.append(Delete('openVisualizer.egg-info'))

    return env.Command(target, '', cmdlist)

Alias('sdist', makeTreeSdist(env, 'sdist'))
Alias('upload', makeTreeSdist(env, 'upload'))

#===== sdist-native

def makeNativeSdist(env):
    '''
    Creates the source dist archive for a OS-native install. Uses a
    phony target to force build.
    '''
    distdir = os.path.join('build', 'dist')

    return env.Command('native', '',
                    [
                    Delete(distdir),
                    Delete('MANIFEST'),
                    Copy('setup.py', 'nativeSetup.py'),
                    'python setup.py sdist --dist-dir {0}'.format(distdir),
                    Delete('setup.py'),
                    Delete('MANIFEST'),
                    ])

Alias('sdist-native', makeNativeSdist(env))

#===== unittest

# scan for SConscript contains unit tests
dirs = [
    os.path.join('openvisualizer', 'motehandler', 'moteprobe'),
    os.path.join('openvisualizer', 'openlbr'),
    os.path.join('openvisualizer', 'rpl'),
]

for d in dirs:
    SConscript(os.path.join(d, 'SConscript'), exports = {"env": env})

Alias('unittests', ['unittests_moteProbe', 'unittests_openLbr', 'unittests_RPL'])

#===== docs

SConscript(
    os.path.join('docs', 'SConscript'),
    exports = {"env": env},
)
