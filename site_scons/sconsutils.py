import os
import platform

from SCons.Script import *

""" Includes common SCons utilities, usable by SConstruct and any SConscript. """


def copy_simulation_fw(env, target):
    """
    Copies the firmware Python extension module from where it was built in the openwsn-fw firmware repository, into the
    bin data/sim_files directory tree. Stores architecture-specific module versions (amd64, x86) into an OS-specific
    subdirectory of sim_files. Also copies the file directly into the sim_files directory for local use if
    architecture and OS match.

    Assumes the environment includes two entries:
    * 'FW_DIR'     entry with the path to the openwsn-fw repository
    * 'SIMHOSTOPT' architecture and OS of the extension module, like 'amd64-linux'

    :param target: Provides a unique pseudo-target for the Command to perform the copy.
    """

    # in openwsn-fw, directory containing 'openwsnmodule_obj.h'
    inc_dir = os.path.join(env['FW_DIR'], 'bsp', 'boards', 'python')
    # in openwsn-fw, directory containing extension library
    lib_dir = os.path.join(env['FW_DIR'], 'build', 'python_gcc', 'projects', 'common')

    # Build source and destination pathnames.
    arch_and_os = env['SIMHOSTOPT'].split('-')
    lib_ext = 'pyd' if arch_and_os[1] == 'windows' else 'so'
    source_name = 'oos_openwsn.{0}'.format(lib_ext)
    dest_name = 'oos_openwsn-{0}.{1}'.format(arch_and_os[0], lib_ext)
    sim_dir = os.path.join('bin', 'sim_files')
    dest_dir = os.path.join(sim_dir, arch_and_os[1])

    cmd_list = [
        Copy(sim_dir, os.path.join(inc_dir, 'openwsnmodule_obj.h')),
        Mkdir(os.path.join(dest_dir)),
        Copy(os.path.join(dest_dir, dest_name), os.path.join(lib_dir, source_name)),
    ]

    # Copy the module directly to sim_files directory if it matches this host.
    if arch_and_os[0] == 'amd64':
        arch_match = platform.architecture()[0] == '64bit'
    else:
        arch_match = platform.architecture()[0] == '32bit'
    if arch_and_os[1] == 'windows':
        os_match = os.name == 'nt'
    else:
        os_match = os.name == 'posix'

    if arch_match and os_match:
        cmd_list.append(Copy(sim_dir, os.path.join(lib_dir, source_name)))

    return env.Command(target, '', cmd_list)
