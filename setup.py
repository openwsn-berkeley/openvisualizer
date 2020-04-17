import glob
import os
import platform
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

from openvisualizer import version

'''
This implementation of the traditional setup.py uses the root package's package_data parameter to store data files, 
rather than the application-level data_files parameter. This arrangement organizes OpenVisualizer within a single tree 
of directories, and so is more portable.

In contrast to the native setup, the installer is free to relocate the tree of directories with install options for 
setup.py.

This implementation is based on setuptools, and builds the list of module dependencies by reading 'requirements.txt'.
'''

VERSION = '.'.join([str(v) for v in version.VERSION])
web_static = 'data/web_files/static'
web_templates = 'data/web_files/templates'
sim_data = 'data/sim_files'
with open('README.md') as f:
    LONG_DESCRIPTION = f.read()

# Create list of required modules for 'install_requires' parameter. Cannot create
# this list with pip.req.parse_requirements() because it requires the pwd module,
# which is Unix only.
# Assumes requirements file contains only module lines and comments.
deplist = []
with open(os.path.join('requirements.txt')) as f:
    for line in f:
        if not line.startswith('#'):
            deplist.append(line)


def app_dir_glob(globstr, subdir=''):
    app_dir = 'bin'
    if subdir == '':
        return glob.glob('/'.join([app_dir, globstr]))
    else:
        return glob.glob('/'.join([app_dir, subdir, globstr]))


class build_py(_build_py):
    """
    Extends setuptools build of openvisualizer package data at installation time.
    Selects and copies the architecture-specific simulation module from an OS-based
    subdirectory up to the parent 'sim_files' directory. Excludes the OS subdirectories
    from installation.
    """

    def build_package_data(self):
        _build_py.build_package_data(self)

        osname = 'windows' if os.name == 'nt' else 'linux'
        suffix = 'amd64' if platform.architecture()[0] == '64bit' else 'x86'
        file_ext = 'pyd' if os.name == 'nt' else 'so'

        sim_path = None
        for package, src_dir, build_dir, filenames in self.data_files:
            for filename in filenames:
                module_name = 'oos_openwsn-{0}.{1}'.format(suffix, file_ext)
                module_path = os.path.join(osname, module_name)
                if package == 'openvisualizer' and filename.endswith(module_path):
                    srcfile = os.path.join(src_dir, filename)
                    sim_path = os.path.join(build_dir, 'data', 'sim_files')
                    target = os.path.join(sim_path, 'oos_openwsn.{0}'.format(file_ext))
                    self.copy_file(srcfile, target)

        if sim_path:
            shutil.rmtree(os.path.join(sim_path, 'linux'))
            shutil.rmtree(os.path.join(sim_path, 'windows'))


setup(
    name='openVisualizer',
    packages=['openvisualizer',
              'openvisualizer.bspemulator', 'openvisualizer.eventbus', 'openvisualizer.motehandler.moteconnector',
              'openvisualizer.motehandler.moteprobe', 'openvisualizer.motehandler.motestate',
              'openvisualizer.openlbr', 'openvisualizer.opentun',
              'openvisualizer.rpl', 'openvisualizer.simengine', 'openvisualizer.jrc'],
    scripts=app_dir_glob('opentui.py'),
    package_dir={'': '.', 'openvisualizer': 'openvisualizer'},
    # Copy sim_data files by extension so don't copy .gitignore in that directory.
    package_data={'openvisualizer': [
        'data/*.conf',
        'data/requirements.txt',
        '/'.join([web_static, 'css', '*']),
        '/'.join([web_static, 'font-awesome', 'css', '*']),
        '/'.join([web_static, 'font-awesome', 'fonts', '*']),
        '/'.join([web_static, 'images', '*']),
        '/'.join([web_static, 'js', '*.js']),
        '/'.join([web_static, 'js', 'plugins', 'metisMenu', '*']),
        '/'.join([web_templates, '*']),
        '/'.join([sim_data, 'windows', '*.pyd']),
        '/'.join([sim_data, 'linux', '*.so']),
        '/'.join([sim_data, '*.h'])
    ]},
    install_requires=deplist,
    # Must extract zip to edit conf files.
    zip_safe=False,
    version=VERSION,
    author='Thomas Watteyne',
    author_email='watteyne@eecs.berkeley.edu',
    description='Wireless sensor network monitoring, visualization, and debugging tool',
    long_description=LONG_DESCRIPTION,
    url='https://openwsn.atlassian.net/wiki/display/OW/OpenVisualizer',
    keywords=['6TiSCH', 'Internet of Things', '6LoWPAN', '802.15.4e', 'sensor', 'mote'],
    platforms=['platform-independent'],
    license='BSD 3-Clause',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Communications',
        'Topic :: Home Automation',
        'Topic :: Internet',
        'Topic :: Software Development',
    ],
    cmdclass={'build_py': build_py},
)
