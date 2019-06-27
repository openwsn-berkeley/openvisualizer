OpenVisualizer
==============

OpenVisualizer (OV) is part of UC Berkeley's OpenWSN project. It provides 
monitoring, visualization, and debugging for an OpenWSN-based wireless sensor
network. See the project [home page][] for more information.

User Manual
-----------

**Run at Local**

If you have the wireless sensor nodes on your local, you can use the following command to start the OpenVisualizer:

```
    > cd OpenVisualizer
    > scons runweb
``` 

Then the OV starts a web server at [localhost:8080][] where you can see the mote information.
A online dashboard at [openwsn-dashboard][] is available for everyone to check the end-to-end performance at real-time.
The performance showing on the dashboard is based on the `uinject` application available in OpenWSN Firmware.
So just make sure uinject is enabled when you program your wireless sensor nodes.

**Run at Local without internet**

In case you don't have the internet access at the moment, you can disable the OV to connect to the dashboard by starting with following command:

```
    > scons runweb --mqtt-broker-address=null
```

**Run with OpenTestbed**

If you have programmed the OpenWSN firmware over the [OpenTestbed][], you can run OV with following command to monitor the nodes:

```
    > scons runweb --opentestbed --opentun-null
```

Installation
------------
You may install OpenVisualizer with the standard pip command line, as shown
below. See the pip [installation instructions][] if it is not installed 
already. You must be logged in with Windows administrator or Linux superuser
privileges to install to system-level directories.

```
    > pip install openVisualizer
```
    
Alternatively, you may download the OpenVisualizer archive, extract it, and
install with the standard Python setup.py command line, as shown below. This
command uses pip to retrieve other required Python libraries.

```
    > python setup.py install
```
    
Dependencies
------------
You also may need to separately install a driver for a USB-connected mote.
On Windows, a couple of other tools are required. See the OpenVisualizer 
[installation page][] for a list.

Running and Uninstalling
------------------------
Once everything is installed, you may run the web interface, GUI, or command 
line utiltity as described on the OpenVisualizer home page. 

To uninstall a pip-based installation, use the command line::

    > pip uninstall openVisualizer
    
Contact
-------

Please contact us via the [mailing list][] or an [issue report][] if you 
have any questions or suggestions.

Thanks!

[home page]: https://openwsn.atlassian.net/wiki/display/OW/OpenVisualizer

[installation instructions]: http://www.pip-installer.org/en/latest/installing.html

[installation page]: https://openwsn.atlassian.net/wiki/display/OW/Installation+and+Dependencies

[mailing list]: https://openwsn.atlassian.net/wiki/display/OW/Mailing+List

[issue report]: https://openwsn.atlassian.net

[openwsn-dashboard]: https://openwsn-dashboard.eu-gb.mybluemix.net/ui/

[OpenTestbed]: https://github.com/openwsn-berkeley/opentestbed

[localhost:8080]: http://localhost:8080/
