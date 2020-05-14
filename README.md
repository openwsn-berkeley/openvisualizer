OpenVisualizer
==============

![](https://img.shields.io/badge/python-2.7-green)


OpenVisualizer (OV) is part of UC Berkeley's OpenWSN project. It provides monitoring, visualization and simulation of 
OpenWSN-based wireless sensor network. See the project [home page][] for more information.

## Table of Contents
* [Installation](#installation)
    - [Setting up the virtualenv](#setting-up-the-virtualenv)
    - [Installing on OSX or Linux](#installing-on-osx-or-linux)
    - [Installing on Windows](#installing-on-windows)
* [Background](#background)
* [Usage](#usage)
    - [Prerequisites](#prerequisites)
    - [Real hardware](#real-hardware)
    - [Simulation mode](#simulation-mode)
    - [Other useful options](#other-useful-options)
* [Testing](#testing)
* [Contact](#contact)


## Installation <a name="installation"></a>
OpenVisualizer is distributed through [PyPi][]. The only thing you need is a working Python 2.7 installation and pip.
We recommend installing OpenVisualizer in a virtual environment. If something goes wrong you can simply delete
the virtual environment without affecting your OS.

#### Setting up the virtualenv <a name="setting-up-the-virtualenv"></a>
Install the virtualenv package, in case you do not already have it:

`> pip install virtualenv`

Create a virtual environment (the name can be anything, here we use the name _**venv**_):

`> python -m virtualenv <NAME_OF_YOUR_VIRTUAL_ENV>`

Once installed you need to activate it (on Linux or OSX):

`> source venv/bin/activate`

Once installed you need to activate it (on Windows):

`> .\venv\Scripts\activate`

#### Installing on OSX or Linux
Once you have your virtualenv set up you can simply type:

`(venv) > pip install openvisualizer`

Pip will download and install all the dependancies. 

#### Installing on Windows
On Windows the instructions are almost the same.

`(venv) > pip install openvisualizer`

After installing you need to uninstall the package `pyreadline`. This package gets installed by `coloredlogs` which we 
use to provide coloring of the logs that are streamed to your terminal. However its is outdated and buggy on Windows 10. 
To prevent issues, you should remove it, the log coloring will still work without it.

`pip uninstall pyrreadline`

## Background

## Usage
#### Prerequisites
#### Real hardware
#### Simulation mode
#### Other useful options

## Testing
    

[home page]: https://openwsn.atlassian.net/wiki/display/OW/OpenVisualizer

[PyPi]: https://pypi.org/

[mailing list]: https://openwsn.atlassian.net/wiki/display/OW/Mailing+List

[issue report]: https://openwsn.atlassian.net

[openwsn-dashboard]: https://openwsn-dashboard.eu-gb.mybluemix.net/ui/

[OpenTestbed]: https://github.com/openwsn-berkeley/opentestbed

[localhost:8080]: http://localhost:8080/
