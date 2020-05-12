import os

from setuptools import setup, find_packages

from openvisualizer import VERSION, PACKAGE_NAME

web_static = 'web_files/static'
web_templates = 'web_files/templates'

with open('README.md') as f:
    LONG_DESCRIPTION = f.read()

# Create list of required modules for 'install_requires' parameter. Cannot create this list with
# pip.req.parse_requirements() because it requires the pwd module, which is Unix only. Assumes requirements file
# contains only module lines and comments.

dep_list = []
with open(os.path.join('requirements.txt')) as f:
    for line in f:
        if not line.startswith('#'):
            dep_list.append(line)

setup(
    name=PACKAGE_NAME,
    packages=find_packages(exclude=['tests', 'docs']),
    package_data={
        'openvisualizer': [
            'config/*.conf',
            '/'.join([web_static, 'css', '*']),
            '/'.join([web_static, 'font-awesome', 'css', '*']),
            '/'.join([web_static, 'font-awesome', 'fonts', '*']),
            '/'.join([web_static, 'images', '*']),
            '/'.join([web_static, 'js', '*.js']),
            '/'.join([web_static, 'js', 'plugins', 'metisMenu', '*']),
            '/'.join([web_templates, '*'])
        ],
        '': [
            'requirements.txt'
        ]
    },
    entry_points={
        'console_scripts': [
            'openv-server = openvisualizer.__main__:main',
            'openv-client = openvisualizer.client.main:cli'
        ]
    },
    install_requires=dep_list,
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
)
