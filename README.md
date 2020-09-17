OpenVisualizer
==============

![](https://img.shields.io/badge/python-2.7-green)


OpenVisualizer (OV) is part of UC Berkeley's OpenWSN project. It provides monitoring, visualization and simulation of OpenWSN-based wireless sensor network. See the project [home page][] for more information. The project works in tandem with the OpenWSN firmware hosted at [openwsn-fw][]. OpenVisualizer interfaces with locally connected hardware, the OpenTestBed infrastructure, [IoT-LAB][] or an emulated OpenWSN network.

## Table of Contents
* [Installation](#installation)
    - [Setting up the virtualenv](#setting-up-the-virtualenv)
    - [Installing on OSX or Linux](#installing-on-osx-or-linux)
    - [Installing on Windows](#installing-on-windows)
    - [Developers](#developers)
* [Architecture](#architecture)
    - [OpenVisualizer Server](#server)
    - [OpenVisualizer Client](#client)
* [Manual](#manual)
    - [Quick Start](#quick-start)
    - [Hardware](#hardware)
    - [Simulation mode](#simulation-mode)
    - [IoT-LAB](#iotlab)
    - [OpenTestBed](#opentestbed) 
* [Documentation](#docs)
* [Testing](#testing)
* [Contributing](#contributing)
* [Contact](#contact)


## Installation <a name="installation"></a>
OpenVisualizer is distributed through [PyPi][]. The only thing you need is a working Python 2.7 installation and pip. We recommend installing OpenVisualizer in a virtual environment. It makes it easier to manage multiple Python projects which require different Python versions and if something goes wrong you can simply delete the virtual environment without affecting your OS.

### Setting up the virtualenv <a name="setting-up-the-virtualenv"></a>
Install the virtualenv package, in case you do not already have it:

```bash
$ pip install virtualenv
```

Create a virtual environment (the name can be anything, here we use the name _**venv**_):

```bash
$ python -m virtualenv <NAME_OF_YOUR_VIRTUAL_ENV>
```

Once installed you need to activate the virtual environment. On Linux or OSX:

```bash
$ source venv/bin/activate
```

On Windows (instructions have been tested for Windows CMD only):

```bash
$ .\venv\Scripts\activate
```

### Installing on OSX or Linux
Once you have your virtual environment set up you can simply install OpenVisualizer as follows:

```bash
(venv) $ pip install openvisualizer
```

Pip will download and install all the dependencies. 

### Installing on Windows
On Windows the instructions are:

```bash
(venv) $ pip install openvisualizer
```

After installing OpenVisualizer you need to remove the package `pyreadline`. The latter is a dependency of the `coloredlogs` package which is used to enabled colored logging output in OpenVisualizer. However, the `pyreadline` package is outdated and buggy on Windows 10. To prevent issues, you should remove it, the log coloring will still work without `pyreadline` installed.

```bash
(venv) $ pip uninstall pyreadline
```

### Developers
If you wish to develop for OpenVisualizer or mess around with the code, you should follow these steps:
1. Setup a virtual environment (as described above) and activate the environment
2. Clone the repository

```bash
(venv) $ git clone git@github.com:openwsn-berkeley/openvisualizer.git
```
3. Checkout the appropriate branch
4. Move to the root of the git repository and install the tools
```bash
(venv) $ pip install -e .
```
The last command will locally install the Python package in an editable form. If you change your Python code the package will automatically use your new code.

## Architecture <a name="architecture"></a>

The architecture of OpenVisualizer is split into two main components:

* **OpenVisualizer Server**
* **OpenVisualizer Client**

![openvisualizer-architecture](https://raw.githubusercontent.com/openwsn-berkeley/openvisualizer/develop/images/ov_arch.png)

### OpenVisualizer Server <a name="server"></a>
The _OpenVisualizer Server_ contains all the code to interface with a mesh network consisting of motes running the OpenWSN firmware. The server can interact with locally connected hardware or with a networks deployed on [IoT-LAB][] or the OpenTestBed. Alternatively, the server can simulate a network and run the firmware code on emulated motes, locally on your computer. To achieve mote emulation, the OpenWSN firmware is compiled as a Python C extension. Mote emulation is particularly useful when you don't have hardware at hand or for debugging purposes. Inside the `openvisualizer` Python package there are several subpackages. All of the subpackages, with exception of the package called `client`, implement different parts of the _OpenVisualizer Server_. Some important features are:

* **motehandler:** interfaces directly with the motes and the network. It allows other components of the _OpenVisualizer Server_ and the _OpenVisualizer Clients_ to communicate with the individual motes. In parallel, the `motehandler` package maintains important status information about each mote in the network and provides parsing of the network and mote logging output.
* **jrc:** provides an implementation of the "Join Request Proxy". The JRC plays an important role when nodes want to join an existing network securely.
* **rpl:** implements RPL source routing for the mesh and provides the user with network topology information.
* **opentun & openlbr:** are packages that parse network traffic between the mesh and the Internet. The `opentun` package specifically allows OpenVisualizer to route network traffic between the Internet and the mesh.

The _OpenVisualizer Server_ also serves as a remote procedure call (RPC) server. It exposes a set of methods that are used by _OpenVisualizer Clients_ to inspect, monitor and manipulate the network or individual motes. 

### OpenVisualizer Client <a name="client"></a>
There are two types of clients: the _terminal client_ and the _web interface client_. Both clients are started with the same command and connect to the _OpenVisualizer Server_. They subsequently use RPC calls to interact with the network and the motes. They query the server for network and mote status information and display the results either directly in the terminal or through the web interface.

The image below shows an instance of _OpenVisualizer Server_ (on the left), and five connected _OpenVisualizer Clients_ (on the right). Each client displays information about a specific mote, i.e., the neighbor table, the TSCH schedule, the packet queue pressure, general mote information, and MAC-layer statistics.

![openv-client](https://raw.githubusercontent.com/openwsn-berkeley/openvisualizer/develop/images/openv-client.png)


## Manual <a name="manual"></a>

### Quick Start <a name="quick-start"></a>
#### Prerequisites
OpenVisualizer depends on the firmware code hosted in the [openwsn-fw][] repository. Before you can run OpenVisualizer you should clone you the [openwsn-fw][] and define an environment variable called `OPENWSN_FW_BASE` which points to the root of your local [openwsn-fw][] directory.

```bash
$ git clone git@github.com:openwsn-berkeley/openwsn-fw.git
$ export OPENWSN_FW_BASE=<PATH_TO_OPENWSN-FW>
```

Alternatively you could use the `--fw-path` option when you launch the _OpenVisualizer Server_.

#### Usage
There are two basic commands:

* **openv-server** 
* **openv-client**

**openv-server**

The `openv-server` command starts the _OpenVisualizer Server_. Depending on the provide options it will:

* Scan the local serial ports (`/dev/tty*` on Unix or `COM*` on Windows) for connected hardware, see [hardware](#hardware)
* Launch an emulated mesh network, see [simulation](#simulation-mode)
* Connect to [IoT-LAB][], see [iotlab](#iotlab)
* Use Inria's OpenTestBed, see [opentestbed](#opentestbed)

All the available options can be listed with the following command:

```bash
(venv) $ openv-server --help
```

**openv-client**

The `openv-client` command can change the parameters of the network and the server of display information. It takes several options and subcommands. More information can be displayed as follows:

```bash
(venv) $ openv-client --help
```

Most `openv-client` commands will issue a single call to the _OpenVisualizer Server_ and exit immediately. For example the following command sets the mote with identifier AF8B, as the DAG root of the network. 

```bash
(venv) $ openv-client root AF8B
```

| ![openv-client](https://raw.githubusercontent.com/openwsn-berkeley/openvisualizer/develop/images/openv-client-root.png) |
| :----------------------------------------------------------: |
| *We try to set mote 0001 as DAG root by running the `openv-client root` command. During the first attempt the OpenVisualizer Server is not active and the command fails. We then start a server instance in another terminal window and retry our command. This time the command is successful.* |

Other useful commands are:

* **boot**: only available when the server is running a simulated network and when the emulated motes have not yet booted. By default the server will immediately boot the emulated motes, but you can change this behavior by adding the `--no-boot` option.
*  **motes**: lists the addresses of the connected motes

| ![openv-client](https://raw.githubusercontent.com/openwsn-berkeley/openvisualizer/develop/images/openv-client-motes.png) |
| :----------------------------------------------------------: |
| *The addresses of the emulated motes before the network was formed and after network formation.* |

* **shutdown**: kills the server

The final subcommand of the `openv-client` is called `view`. It can display several types of mote or network status information. You can list the different _views_ as follows:

```bash
(venv) $ openv-client view --help
```

Each _view_ command works in the same way. It starts a thread that periodically queries the server for a specific bit of information for a specified mote. It then displays this information nicely by using the Python package `blessed`, a wrapper around the Python`curses` module, or through the web browser (when you use the _view_ called _web_).  The option `--refresh-rate=<x>` (not available for the _web view_) can change how often the _view_ is updated, i.e., queries the _OpenVisualizer Server_ (default is 1s). 

| ![openv-client](https://raw.githubusercontent.com/openwsn-berkeley/openvisualizer/develop/images/openv-client-views.png) |
| :----------------------------------------------------------: |
| *The top terminal panel shows the output of the OpenVisualizer Server. On the bottom there are two active views, schedule and neighbors, each in there own terminal panel* |

In the bottom-left terminal panel:

```bash
(venv) $ openv-client view schedule 0001
```

In the bottom-right terminal panel:

```bash
(venv) $ openv-client view neigbors 0001
```

The web view can be started as follows:

```bash
(venv) $ openv-client view web
```

Web view (main tab)            |  Web view (topology tab) 
:-------------------------:|:-------------------------:
![openv-client-web1](https://raw.githubusercontent.com/openwsn-berkeley/openvisualizer/develop/images/webview-motes.png)  | ![openv-client-web2](https://raw.githubusercontent.com/openwsn-berkeley/openvisualizer/develop/images/webview-topology.png) 

### Hardware <a name="hardware"></a>

### Simulation mode <a name="simulation-mode"></a>
### IoT-LAB <a name="iotlab"></a>
#### Prerequisites

- A valid IoT-LAB [account](https://www.iot-lab.info/testbed/signup)
- A set of flashed nodes. You can flash [IoT-LAB][] directly on the web interface or through their CLI tools. (refer to IoT-LAB [documentation](https://www.iot-lab.info/tutorials/iotlab-experimenttools-client/) for this)

#### Usage

Its possible to connect the _OpenVisualizer Server_ with the [IoT-LAB][] infrastructure. A depiction of how the connection is set up can be found below.

|![](https://www.iot-lab.info/wp-content/uploads/2017/06/tuto_m3_clitools_exp.jpg)|
|:--:|
| *IoT-LAB connections* |

When OpenVisualizer is not running on the SSH frontend (see figure above) a ssh-tunnel is opened to connect
to the IoT-LAB motes' TCP port.

You can specify the motes to connect to by using the `--iotlab-motes` option, it receives a list of IoT-LAB motes'`network_addresses` (e.g.,  `m3-4.grenoble.iot-lab.info`).

When _OpenVisualizer Server_ runs directly on the SSH frontend you can use the short address notation, e.g., `m3-4`.

- SSH frontend:

    ```bash
    (venv) $ openv-server --iotlab-motes m3-4 m3-5.
    ```

- Locally:

    ```bash
    (venv) $ openv-server --iotlab-motes m3-4.grenoble.iot-lab.info m3-5.grenoble.iot-lab.info
    ```

You can authenticate to [IoT-LAB][] upfront by running:

```bash
(venv)  $ iotlab-auth -u <login>
```

Otherwise you need to pass your username and password as additional parameters:

```bash
(venv)  $ openv-server --iotlab-motes m3-10 m3-11 --user <USERNAME> --password <PASSWORD>
```

### OpenTestBed <a name="opentestbed"></a>

Running the _OpenVisualizer Server_ as a frontend for the OpenTestBed is as simple as:

```bash
(venv) $ openv-server --opentestbed
```
The server connects in the background to the MQTT server that gathers the data from the testbed and subscribes to the appropriate topics.

## Documentation <a name="docs"></a>

The docs can be generated through Sphinx. Navigate to the root of the project and run the following the command:

```bash
(venv) $ sphinx-build -b html docs build
```

* docs is the source directory
* build will contain the output

More information can be found on the [Sphinx webpage](https://www.sphinx-doc.org/en/master/usage/quickstart.html)

## Testing <a name="testing"></a>

### Testing the serial communication
The OpenWSN firmware uses the serial port extensively to communicate with OpenVisualizer and route packets (when in DAGroot mode). It is thus important that serial communication works well. To verify the serial communication between the hardware motes and your computer you can use the `openv-serial` tool.

| ![openv-serial](https://raw.githubusercontent.com/openwsn-berkeley/openvisualizer/develop/images/openv-serial.png) |
|:--:|
| *openv-serial tool for testing the serial communication* |

### Testing the TUN interface
To route packets between the Internet and the OpenWSN mesh network, OpenVisualizer uses a TUN interface. To create such an interface you need root privileges on your system. To test if everything works properly, you can run `openv-tun`.

| ![openv-tun](https://raw.githubusercontent.com/openwsn-berkeley/openvisualizer/develop/images/openv-tun.png) |
|:--:|
| *openv-tun tool for testing the TUN interface* |


## Contributing <a name="contributing"></a>
Contributions are always welcome. We use `flake8` to enforce the Python PEP-8 style guide. The Travis builder verifies new pull requests and it fails if the Python code does not follow the style guide.

You can check locally if your code changes comply with PEP-8. First, install the main `flake8` package and two `flake8` plugins:

```bash
(venv) pip install flake8
(venv) pip install pep8-naming
(venv) pip install flake8-commas
```

Move to the root of the OpenVisualizer project and run:

```bash
(venv) flake8 --config=tox.ini
```

If flake does not generate any output, your code passes the test; alternatively, you can check the return code:

```bash
(venv) flake8 --config=tox.ini
(venv) echo $?
0
```

## Contact <a name="contact"></a>


[home page]: https://openwsn.atlassian.net/wiki/display/OW/OpenVisualizer

[PyPi]: https://pypi.org/

[mailing list]: https://openwsn.atlassian.net/wiki/display/OW/Mailing+List

[issue report]: https://openwsn.atlassian.net

[IoT-LAB]: https://www.iot-lab.info/

[openwsn-fw]: https://github.com/openwsn-berkeley/openwsn-fw

[openwsn-dashboard]: https://openwsn-dashboard.eu-gb.mybluemix.net/ui/

[OpenTestbed]: https://github.com/openwsn-berkeley/opentestbed

[localhost:8080]: http://localhost:8080/
