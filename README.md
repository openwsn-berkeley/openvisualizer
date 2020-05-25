OpenVisualizer
==============

![](https://img.shields.io/badge/python-2.7-green)


OpenVisualizer (OV) is part of UC Berkeley's OpenWSN project. It provides monitoring, visualization and simulation of OpenWSN-based wireless sensor network. See the project [home page][] for more information. The project works in tandem with the OpenWSN firmware hosted at [openwsn-fw][]. OpenVisualizer interfaces with locally connected hardware, the OpenTestBed infrastructure, [IoT-LAB][] or an emulated OpenWSN network.

## Table of Contents
* [Installation](#installation)
    - [Setting up the virtualenv](#setting-up-the-virtualenv)
    - [Installing on OSX or Linux](#installing-on-osx-or-linux)
    - [Installing on Windows](#installing-on-windows)
* [Architecture](#architecture)
* [Manual](#manual)
    - [Quick Start](#quick-start)
    - [Real hardware](#real-hardware)
    - [Mote emulation & network simulation](#simulation-mode)
    - [IoT-LAB](#iotlab)
    - [OpenTestBed](#opentestbed) 
* [Testing](#testing)
* [Contact](#contact)


## Installation <a name="installation"></a>
OpenVisualizer is distributed through [PyPi][]. The only thing you need is a working Python 2.7 installation and pip. We recommend installing OpenVisualizer in a virtual environment. If something goes wrong you can simply delete the virtual environment without affecting your OS.

### Setting up the virtualenv <a name="setting-up-the-virtualenv"></a>
Install the virtualenv package, in case you do not already have it:

```bash
> pip install virtualenv
```

Create a virtual environment (the name can be anything, here we use the name _**venv**_):

```bash
> python -m virtualenv <NAME_OF_YOUR_VIRTUAL_ENV>
```

Once installed you need to activate the virtual environment. On Linux or OSX:

```bash
> source venv/bin/activate
```

On Windows (when you are using PowerShell, you might have to change the execution policy):

```bash
> .\venv\Scripts\activate
```

### Installing on OSX or Linux
Once you have your virtualenv set up you can simply type:

```bash
(venv) > pip install openvisualizer
```

Pip will download and install all the dependencies. 

### Installing on Windows
On Windows the instructions are almost the same.

```bash
(venv) > pip install openvisualizer
```

After installing OpenVisualizer you need to remove the package `pyreadline`. The latter is a dependency of the `coloredlogs` package which is used to enabled colored logging output in OpenVisualizer. However, the `pyreadline` package is outdated and buggy on Windows 10. To prevent issues, you should remove it, the log coloring will still work without `pyreadline` installed.

```bash
(venv) > pip uninstall pyreadline
```

## Architecture <a name="architecture"></a>

![openvisualizer-architecture](images/ov_arch.png)

The architecture of OpenVisualizer is split into two main components:

* **OpenVisualizer Server**
* **OpenVisualizer Client**

### OpenVisualizer Server
The _OpenVisualizer Server_ contains all the code to interface with a mesh network consisting of motes running the OpenWSN firmware. The server can also simulate a network and run the firmware code on emulated motes. To achieve mote emulation, the OpenWSN firmware is compiled as a Python C extension. Mote emulation is particulary useful when you don't have the appropriate hardware or for debugging purposes. Inside the `openvisualizer` Python package there are several subpackages. All of the subpackages, with exception of the package called `client`, implement different parts of the _OpenVisualizer Server_. Some important components are:

* **motehandler** package enables direct communication between the motes, other components of the _OpenVisualizer Server_ and the _OpenVisualizer Clients_. The motehandler package maintains important information about each mote in the network and provides parsing of the network and mote logs.
* **jrc** package provides an implementation of the "Join Request Proxy". The JRC plays an important role when nodes want to join an existing network securely.
* **rpl** package implements RPL source routing for the mesh and provides the user with network topology information.
* **opentun & openlbr** are packages that parse network traffic between the mesh and the Internet. The opentun package specifically allows OpenVisualizer to route network traffic between the Internet and the mesh.

The _OpenVisualizer Server_ is a remote procedure call (RPC) server. It exposes a set of methods that are used by _OpenVisualizer Clients_ to inspect, monitor and manipulate the network or individual motes. 

### OpenVisualizer Client
There are two types of clients: the _terminal client_ and the _web interface client_. Both clients are started with the same command and connect to the _OpenVisualizer Server_. They subsequently use RPC calls to interact with the network and the motes. They query the server for network and mote status information and display the results either directly in the terminal or through the web interface.


## Manual <a name="manual"></a>

### Quick Start <a name="quick-start"></a>
#### Prerequisites
OpenVisualizer is depend on the firmware code hosted in the [openwsn-fw][] repository. Before you can run OpenVisualizer you should clone you the [openwsn-fw][] and define an environment variable called **OPENWSN_FW_BASE** which points to the root of the clone [openwsn-fw][] directory.

```bash
> git clone git@github.com:openwsn-berkeley/openwsn-fw.git
> export OPENWSN_FW_BASE=<PATH_TO_OPENWSN-FW>`
```

Alternatively you could use the `--fw-path` option when you launch the _OpenVisualizer Server_.

#### Usage
There are two basic commands:

* **openv-server** 
* **openv-client**

The _openv-server_ command starts the _OpenVisualizer Server_, and depending on the provide options, scans the local serial ports for connected hardware, launches an emulated mesh network, connects to IoTLab or use Inria's OpenTestBed. All the options can be listed as follows:

```bash
> (venv) openv-server --help
```

The _openv-client_ command can change the parameters of the network and the server of display information. It takes several options and subcommands. More information can be displayed as follows:

```bash
> (venv) openv-client --help
```

### Real hardware <a name="real-hardware"></a>
### Simulation mode <a name="simulation-mode"></a>
### IoT-LAB <a name="iotlab"></a>
#### Prerequisites

- A valid IoT-LAB [account](https://www.iot-lab.info/testbed/signup)
- A set of flashed nodes. You can flash IoT-LAB directly on the web interface or through the CLI tools. (refer to IoT-LAB [documentation](https://www.iot-lab.info/tutorials/iotlab-experimenttools-client/) for this)

#### Usage

Its possible to interface with nodes running on [IoT-LAB][]. A depiction of how the connection is set up can be found below.

![](https://www.iot-lab.info/wp-content/uploads/2017/06/tuto_m3_clitools_exp.jpg)

When OpenVisualizer is not running on the SSH frontend (see figure above) a ssh-tunnel is opened to connect
to the IoT-LAB motes' TCP port.

You can specify the motes to connect to by using the `--iotlab-motes` option, it receives a list of IoT-LAB motes'`network_addresses` (e.g.,  `m3-4.grenoble.iot-lab.info`).

When OpenVisualizer Server runs directly on the SSH frontend you can use the short address notation, e.g., `m3-4`.

- SSH frontend:

    $ openv-server --iotlab-motes m3-4 m3-5.

- Locally:

    $ openv-server --iotlab-motes m3-4.grenoble.iot-lab.info m3-5.grenoble.iot-lab.info

You can authenticate to IoT-LAB upfront by running:

    $  iotlab-auth -u <login>

Otherwise you need to pass your username and password as additional parameters:

    $ openv-server --iotlab-motes m3-10 m3-11 --user <USERNAME> --password <PASSWORD>

## Testing


[home page]: https://openwsn.atlassian.net/wiki/display/OW/OpenVisualizer

[PyPi]: https://pypi.org/

[mailing list]: https://openwsn.atlassian.net/wiki/display/OW/Mailing+List

[issue report]: https://openwsn.atlassian.net

[IoT-LAB]: https://www.iot-lab.info/

[openwsn-fw]: https://github.com/openwsn-berkeley/openwsn-fw

[openwsn-dashboard]: https://openwsn-dashboard.eu-gb.mybluemix.net/ui/

[OpenTestbed]: https://github.com/openwsn-berkeley/opentestbed

[localhost:8080]: http://localhost:8080/
