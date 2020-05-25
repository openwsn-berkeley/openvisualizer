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
#### IotLab support


##### Prerequisites

    - Valid Iot-Lab [account](https://www.iot-lab.info/testbed/signup)
    - Running experiment with already flashed nodes, this can be done directly
      on the web interface or using the cli tools. (refer to IoT-Lab
      [documentation](https://www.iot-lab.info/tutorials/iotlab-experimenttools-client/) for this)

##### Usage

Its possible to interface with nodes running on [Iot-Lab](https://www.iot-lab.info/).

A description of how the connection is set can be found below.

![](https://www.iot-lab.info/wp-content/uploads/2017/06/tuto_m3_clitools_exp.jpg)

When not on the ssh-frontend (see figure above) a ssh-tunnel is opened to connect
to the motes tcp port.

You can specify the motes to connect to with `--iotlab-motes` option, it receives
a list of iotlab motes `network_address` such as `m3-4.grenoble.iot-lab.info`,
when connecting directly on the ssh frontend you can pass the shortened version
`m3-4`.

e.g. on ssh frontend:

    $ openv-server --iotlab-motes m3-4 m3-5.

e.g. on ssh frontend:

    $ openv-server --iotlab-motes m3-4.grenoble.iot-lab.info m3-5.grenoble.iot-lab.info

You can authenticate your iotlab before hand by running:

    $  iotlab-auth -u <login>

Otherwise you need to pass your username and password as additional parameters:

    $ openv-server --iotlab-motes m3-10 m3-11 --user <USERNAME> --password <PASSWORD>

#### Other useful options

## Testing
    

[home page]: https://openwsn.atlassian.net/wiki/display/OW/OpenVisualizer

[PyPi]: https://pypi.org/

[mailing list]: https://openwsn.atlassian.net/wiki/display/OW/Mailing+List

[issue report]: https://openwsn.atlassian.net

[openwsn-dashboard]: https://openwsn-dashboard.eu-gb.mybluemix.net/ui/

[OpenTestbed]: https://github.com/openwsn-berkeley/opentestbed

[localhost:8080]: http://localhost:8080/
