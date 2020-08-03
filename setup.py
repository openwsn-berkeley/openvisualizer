import os

from setuptools import setup, find_packages

from openvisualizer import VERSION, PACKAGE_NAME

web_static = 'client/web_files/static'
web_templates = 'client/web_files/templates'


# Cannot create this list with pip.req.parse_requirements() because it requires
# the pwd module, which is Unix only.
def _read_requirements(file_name):
    """
    Returns list of required modules for 'install_requires' parameter. Assumes
    requirements file contains only module lines and comments.
    """
    requirements = []
    with open(os.path.join(file_name)) as f:
        for line in f:
            if not line.startswith('#'):
                requirements.append(line)
    return requirements


INSTALL_REQUIREMENTS = _read_requirements('requirements.txt')

# read the contents of your README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md')) as f:
    LONG_DESCRIPTION = f.read()

setup(
    name=PACKAGE_NAME,
    packages=find_packages(exclude=['tests', '*.tests', 'tests.*', '*.tests.*']),
    python_requires='<=2.7.18',
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'openv-server = openvisualizer.__main__:main',
            'openv-client = openvisualizer.client.main:cli',
            'openv-serial = scripts.serialtester_cli:cli',
            'openv-tun = scripts.ping_responder:cli',
        ],
    },
    install_requires=INSTALL_REQUIREMENTS,
    # Must extract zip to edit conf files.
    zip_safe=False,
    version=VERSION,
    author='Thomas Watteyne',
    author_email='watteyne@eecs.berkeley.edu',
    description='Wireless sensor network monitoring and visualization tool',
    long_description_content_type='text/markdown',
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
)
