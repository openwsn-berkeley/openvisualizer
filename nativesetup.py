import glob

from distutils.core import setup

from openvisualizer import appdirs
from openvisualizer import version

'''
This implementation of the traditional setup.py uses the application-level data_files parameter to store data files, 
rather than the package-level package_data parameter. We store these data files in operating system specific, i.e. 
"native", locations with the help of the appdirs utility. For example, shared data files on Linux are placed in 
"/usr/local/share/openvisualizer".

We use the site-level data and config directories because we expect the superuser to run OpenVisualizer, so user-level 
directories like "/home/<user>/.config" are not available.

For native file storage to work, the installer *must not* modify the location of these files at install time.

Use of the legacy distutils package also accommodates existing Linux packaging tools.
'''

VERSION = '.'.join([str(v) for v in version.VERSION])
data_dir = appdirs.site_data_dir('openvisualizer', 'OpenWSN')
conf_dir = appdirs.site_config_dir('openvisualizer', 'OpenWSN')
web_static = 'web_files/static'
web_tmpl = 'web_files/templates'
sim_data = 'sim_files'
with open('README.txt') as f:
    LONG_DESCRIPTION = f.read()


def app_dir_glob(globstr, subdir=''):
    appdir = 'bin'
    if subdir == '':
        return glob.glob('/'.join([appdir, globstr]))
    else:
        return glob.glob('/'.join([appdir, subdir, globstr]))


setup(
    name='openVisualizer',
    packages=['openvisualizer',
              'openvisualizer.bspemulator', 'openvisualizer.eventbus', 'openvisualizer.motehandler.moteconnector',
              'openvisualizer.moteprobe', 'openvisualizer.motehandler.motestate', 'openvisualizer.openlbr',
              'openvisualizer.opentun', 'openvisualizer.rpl', 'openvisualizer.simengine', 'openvisualizer.jrc'],
    package_dir={'': '.', 'openvisualizer': 'openvisualizer'},
    scripts=[app_dir_glob('openvisualizer_*.py'), app_dir_glob('webserver.py'), app_dir_glob('helpers')],
    # Copy sim_data files by extension so don't copy .gitignore in that directory.
    data_files=[(conf_dir, app_dir_glob('*.conf')),
                ('/'.join([data_dir, web_static, 'css']), app_dir_glob('*', '/'.join([web_static, 'css']))),
                ('/'.join([data_dir, web_static, 'font-awesome', 'css']),
                 app_dir_glob('*', '/'.join([web_static, 'font-awesome', 'css']))),
                ('/'.join([data_dir, web_static, 'font-awesome', 'fonts']),
                 app_dir_glob('*', '/'.join([web_static, 'font-awesome', 'fonts']))),
                ('/'.join([data_dir, web_static, 'images']), app_dir_glob('*', '/'.join([web_static, 'images']))),
                ('/'.join([data_dir, web_static, 'js']), app_dir_glob('*.js', '/'.join([web_static, 'js']))),
                ('/'.join([data_dir, web_static, 'js', 'plugins', 'metisMenu']),
                 app_dir_glob('*', '/'.join([web_static, 'js', 'plugins', 'metisMenu']))),
                ('/'.join([data_dir, web_tmpl]), app_dir_glob('*', web_tmpl)),
                ('/'.join([data_dir, sim_data]), app_dir_glob('*.so', sim_data)),
                ('/'.join([data_dir, sim_data]), app_dir_glob('*.py', sim_data)),
                ('/'.join([data_dir, sim_data]), app_dir_glob('*.h', sim_data))],
    version=VERSION,
    author='Thomas Watteyne',
    author_email='watteyne@eecs.berkeley.edu',
    description='OpenWSN wireless sensor network monitoring, visualization, and debugging tool',
    long_description=LONG_DESCRIPTION,
    url='http://www.openwsn.org/',
    keywords=['6TiSCH', 'Internet of Things', '6LoWPAN', 'sensor', 'mote'],
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
)
