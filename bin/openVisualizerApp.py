# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

'''
Contains application model for OpenVisualizer. Expects to be called by 
top-level UI module.  See main() for startup use.
'''
import sys
import os
import logging
import json
import time
import subprocess

from openvisualizer.OVtracer import OVtracer

log = logging.getLogger('openVisualizerApp')

from coap                           import coap, \
                                           coapDefines

from openvisualizer.eventBus        import eventBusMonitor
from openvisualizer.eventLogger     import eventLogger
from openvisualizer.moteProbe       import moteProbe
from openvisualizer.moteConnector   import moteConnector
from openvisualizer.moteState       import moteState
from openvisualizer.coapServer      import coapServer
from openvisualizer.RPL             import RPL
from openvisualizer.JRC             import JRC
from openvisualizer.openBenchmarkAgent import openBenchmarkAgent
from openvisualizer.openLbr         import openLbr
from openvisualizer.openTun         import openTun
from openvisualizer.RPL             import topology
from openvisualizer                 import appdirs
from openvisualizer.remoteConnectorServer   import remoteConnectorServer

import openvisualizer.openvisualizer_utils as u
    
class OpenVisualizerApp(object):
    '''
    Provides an application model for OpenVisualizer. Provides common,
    top-level functionality for several UI clients.
    '''
    
    def __init__(self,confdir,datadir,logdir,simulatorMode,numMotes,trace,debug,usePageZero,simTopology,iotlabmotes,testbed,benchmark,pathTopo,mqtt_broker_address,opentun_null):
        
        # store params
        self.confdir              = confdir
        self.datadir              = datadir
        self.logdir               = logdir
        self.simulatorMode        = simulatorMode
        self.numMotes             = numMotes
        self.trace                = trace
        self.debug                = debug
        self.usePageZero          = usePageZero
        self.iotlabmotes          = iotlabmotes
        self.testbed              = testbed
        self.benchmark            = benchmark
        self.pathTopo             = pathTopo
        self.mqtt_broker_address  = mqtt_broker_address

        # local variables
        self.eventBusMonitor      = eventBusMonitor.eventBusMonitor()
        self.openLbr              = openLbr.OpenLbr(usePageZero)

        # run CoAP server in testing mode
        # this mode does not open a real socket, rather uses PyDispatcher for sending/receiving messages
        # We interface this mode with OpenVisualizer to run JRC co-located with the DAG root
        self.coapServer           = coap.coap(udpPort=coapDefines.DEFAULT_UDP_PORT,
                                              testing=True,
                                              socketUdp=coapServer.coapDispatcher)
        self.rpl                  = RPL.RPL()
        self.jrc                  = JRC.JRC(self.coapServer)
        self.topology             = topology.topology()
        self.openBenchmarkAgent   = None
        self.DAGrootList          = []
        # create openTun call last since indicates prefix
        self.openTun              = openTun.create(opentun_null)
        if self.simulatorMode:
            from openvisualizer.SimEngine import SimEngine, MoteHandler
            
            self.simengine        = SimEngine.SimEngine(simTopology)
            self.simengine.start()
        
        # import the number of motes from json file given by user (if the pathTopo option is enabled)
        if self.pathTopo and self.simulatorMode:
            try:
                topoConfig = open(pathTopo)
                topo = json.load(topoConfig)
                self.numMotes = len(topo['motes'])
            except Exception as err:
                print err
                app.close()
                os.kill(os.getpid(), signal.SIGTERM)

        # create a moteProbe for each mote
        if self.simulatorMode:
            self.testEnvironment = 'opensim'
            # in "simulator" mode, motes are emulated
            sys.path.append(os.path.join(self.datadir, 'sim_files'))
            import oos_openwsn
            
            MoteHandler.readNotifIds(os.path.join(self.datadir, 'sim_files', 'openwsnmodule_obj.h'))
            self.moteProbes       = []
            for _ in range(self.numMotes):
                moteHandler       = MoteHandler.MoteHandler(oos_openwsn.OpenMote())
                self.simengine.indicateNewMote(moteHandler)
                self.moteProbes  += [moteProbe.moteProbe(mqtt_broker_address, emulatedMote=moteHandler)]
        elif self.iotlabmotes:
            self.testEnvironment = 'iotlab-tcp'
            # in "IoT-LAB" mode, motes are connected to TCP ports
            
            self.moteProbes       = [
                moteProbe.moteProbe(mqtt_broker_address, iotlabmote=p) for p in self.iotlabmotes.split(',')
            ]
        elif self.testbed:
            self.testEnvironment = self.testbed
            motesfinder = moteProbe.OpentestbedMoteFinder(testbed=self.testbed, mqtt_broker_address=self.mqtt_broker_address)
            self.moteProbes       = [
                moteProbe.moteProbe(mqtt_broker_address, testbedmote=p)
                for p in motesfinder.get_opentestbed_motelist()
            ]
            
        else:
            self.testEnvironment = 'local'
            # in "hardware" mode, motes are connected to the serial port
            self.moteProbes       = [
                moteProbe.moteProbe(mqtt_broker_address, serialport=p) for p in moteProbe.findSerialPorts()
            ]
        
        # create a moteConnector for each moteProbe
        self.moteConnectors       = [
            moteConnector.moteConnector(mp) for mp in self.moteProbes
        ]
        
        # create a moteState for each moteConnector
        self.moteStates           = [
            moteState.moteState(mc) for mc in self.moteConnectors
        ]
        
        self.eventLoggers         = [
            eventLogger.eventLogger(ms) for ms in self.moteStates
        ]

        if self.testbed:
            # at least, when we use OpenTestbed, we don't need
            # Rover. Don't instantiate remoteConnectorServer which
            # consumes a lot of CPU.
            self.remoteConnectorServer = None
        else:
            self.remoteConnectorServer = remoteConnectorServer.remoteConnectorServer()

        # boot all emulated motes, if applicable
        if self.simulatorMode:
            self.simengine.pause()
            now = self.simengine.timeline.getCurrentTime()
            for rank in range(self.simengine.getNumMotes()):
                moteHandler = self.simengine.getMoteHandler(rank)
                self.simengine.timeline.scheduleEvent(
                    now,
                    moteHandler.getId(),
                    moteHandler.hwSupply.switchOn,
                    moteHandler.hwSupply.INTR_SWITCHON
                )
            self.simengine.resume()

       
        # import the topology from the json file
        if self.pathTopo and self.simulatorMode:
            
            # delete each connections automatically established during motes creation
            ConnectionsToDelete = self.simengine.propagation.retrieveConnections()
            for co in ConnectionsToDelete :
                fromMote = int(co['fromMote'])
                toMote = int(co['toMote'])
                self.simengine.propagation.deleteConnection(fromMote,toMote)

            motes = topo['motes']
            for mote in motes :
                mh = self.simengine.getMoteHandlerById(mote['id'])
                mh.setLocation(mote['lat'], mote['lon'])
            
            # implements new connections
            connect = topo['connections']
            for co in connect:
                fromMote = int(co['fromMote'])
                toMote = int(co['toMote'])
                pdr = float(co['pdr'])
                self.simengine.propagation.createConnection(fromMote,toMote)
                self.simengine.propagation.updateConnection(fromMote,toMote,pdr)
            
            # store DAGroot moteids in DAGrootList
            DAGrootL = topo['DAGrootList']
            for DAGroot in DAGrootL :
                hexaDAGroot = hex(DAGroot)
                hexaDAGroot = hexaDAGroot[2:]
                prefixLen = 4 - len(hexaDAGroot)
                
                prefix =""
                for i in range(prefixLen):
                    prefix += "0"
                moteid = prefix+hexaDAGroot
                self.DAGrootList.append(moteid)

        # If cloud-based benchmarking service is requested, start the agent
        if self.benchmark:

            # give some time to OV to discover nodes' EUI-64 addresses
            motes = {}
            for ms in self.moteStates:
                attempt = 0
                while ms.getStateElem(ms.ST_IDMANAGER).get_info()['64bAddr'] == '':
                    if attempt >= 10:
                        motes['invalid_eui64_' + ms.getStateElem(ms.ST_IDMANAGER).get_info()['serial']] = {
                            'serialPort': ms.getStateElem(ms.ST_IDMANAGER).get_info()['serial']}
                        break
                    attempt += 1
                    time.sleep(1)
                motes[ ms.getStateElem(ms.ST_IDMANAGER).get_info()['64bAddr'] ] = { 'serialPort' : ms.getStateElem(ms.ST_IDMANAGER).get_info()['serial'] }

            self.openBenchmarkAgent = openBenchmarkAgent.OpenBenchmarkAgent(
                mqttBroker=self.mqtt_broker_address,
                coapServer=self.coapServer,
                firmware='openwsn-{0}'.format(subprocess.check_output(["git", "describe", "--tags"]).strip()),
                testbed=self.testEnvironment,
                motes=motes,
                scenario=self.benchmark
            )
        
        # start tracing threads
        if self.trace:
            import openvisualizer.OVtracer
            logging.config.fileConfig(
                                os.path.join(self.confdir,'trace.conf'),
                                {'logDir': _forceSlashSep(self.logdir, self.debug)})
            OVtracer.OVtracer()
        
    #======================== public ==========================================
    
    def close(self):
        '''Closes all thread-based components'''
        
        log.info('Closing OpenVisualizer')
        self.openTun.close()
        self.rpl.close()
        self.jrc.close()
        for probe in self.moteProbes:
            probe.close()
        if self.openBenchmarkAgent:
            self.openBenchmarkAgent.close()
        self.coapServer.close()
                
    def getMoteState(self, moteid):
        '''
        Returns the moteState object for the provided connected mote.
        
        :param moteid: 16-bit ID of mote
        :rtype:        moteState or None if not found
        '''
        for ms in self.moteStates:
            idManager = ms.getStateElem(ms.ST_IDMANAGER)
            if idManager and idManager.get16bAddr():
                addr = ''.join(['%02x'%b for b in idManager.get16bAddr()])
                if addr == moteid:
                    return ms
        else:
            return None

    def getMotesConnectivity(self):
        motes  = []
        states = []
        edges  = []

        for ms in self.moteStates:
            idManager = ms.getStateElem(ms.ST_IDMANAGER)
            if idManager and idManager.get16bAddr():
                src_s = ''.join(['%02X'%b for b in idManager.get16bAddr()])
                motes.append(src_s)
            neighborTable = ms.getStateElem(ms.ST_NEIGHBORS)
            for neighbor in neighborTable.data:
                if len(neighbor.data)==0:
                    break
                if neighbor.data[0]['used']==1 and neighbor.data[0]['parentPreference']==1:
                    dst_s =''.join(['%02X' %b for b in neighbor.data[0]['addr'].addr[-2:]])
                    edges.append({ 'u':src_s, 'v':dst_s })
                    break

        motes = list(set(motes))
        for mote in motes:
            d = { 'id': mote, 'value': { 'label': mote } } 
            states.append(d)
        return states, edges
        
    def refreshRoverMotes(self, roverMotes):
        '''Connect the list of roverMotes to openvisualiser.

        :param roverMotes : list of the roverMotes to add
        '''
        # create a moteConnector for each roverMote
        for roverIP, value in roverMotes.items() :
            if not isinstance(value , str):
                for rm in roverMotes[roverIP] :
                        exist = False
                        for mc in self.moteConnectors :
                            if mc.serialport == rm :
                                exist = True
                                break
                        if not exist :
                            moc = moteConnector.moteConnector(rm)
                            self.moteConnectors       += [moc]
                            self.moteStates += [moteState.moteState(moc)]
        self.remoteConnectorServer.initRoverConn(roverMotes)

    def removeRoverMotes(self, roverIP, moteList):
        ''' Remove moteconnect and motestates from list (NOT implemented: quit())
            Stop ZMQ connection
        :param roverIP
        '''

        for moteid in moteList:
            ms = self.getMoteState(moteid)
            if ms:
                self.moteConnectors.remove(ms.moteConnector)
                self.moteStates.remove(ms)
            else:
                for mss in self.moteStates:
                    if moteid == mss.moteConnector.serialport:
                        self.moteConnectors.remove(mss.moteConnector)
                        self.moteStates.remove(mss)
        self.remoteConnectorServer.closeRoverConn(roverIP)



    def getMoteDict(self):
        '''
        Returns a dictionary with key-value entry: (moteid: serialport)
        '''
        moteDict = {}
        for ms in self.moteStates:
            addr = ms.getStateElem(moteState.moteState.ST_IDMANAGER).get16bAddr()
            if addr:
                moteDict[''.join(['%02x' % b for b in addr])] = ms.moteConnector.serialport
            else:
                moteDict[ms.moteConnector.serialport] = None
        return moteDict


#============================ main ============================================
import logging.config
from argparse       import ArgumentParser

DEFAULT_MOTE_COUNT = 3

def main(parser=None):
    '''
    Entry point for application startup by UI. Parses common arguments.
    
    :param parser:  Optional ArgumentParser passed in from enclosing UI module
                    to allow that module to pre-parse specific arguments
    :rtype:         openVisualizerApp object
    '''
    if parser is None:
        parser = ArgumentParser()
        
    _addParserArgs(parser)
    argspace = parser.parse_args()

    confdir, datadir, logdir = _initExternalDirs(argspace.appdir, argspace.debug)
    
    # Must use a '/'-separated path for log dir, even on Windows.
    logging.config.fileConfig(
        os.path.join(confdir,'logging.conf'), 
        {'logDir': _forceSlashSep(logdir, argspace.debug)}
    )

    if argspace.pathTopo:
        argspace.simulatorMode = True
        argspace.numMotes = 0
        argspace.simTopology = "fully-meshed"
        # --pathTopo
    elif argspace.numMotes > 0:
        # --simCount implies --sim
        argspace.simulatorMode = True
    elif argspace.simulatorMode:
        # default count when --simCount not provided
        argspace.numMotes = DEFAULT_MOTE_COUNT

    log.info('Initializing OpenVisualizerApp with options:\n\t{0}'.format(
            '\n    '.join(['appdir         = {0}'.format(argspace.appdir),
                           'sim            = {0}'.format(argspace.simulatorMode),
                           'simCount       = {0}'.format(argspace.numMotes),
                           'trace          = {0}'.format(argspace.trace),
                           'debug          = {0}'.format(argspace.debug),
                           'testbed        = {0}'.format(argspace.testbed),
                           'benchmark      = {0}'.format(argspace.benchmark),
                           'mqttBroker     = {0}'.format(argspace.mqtt_broker_address),
                           'usePageZero    = {0}'.format(argspace.usePageZero)],
            )))
    log.info('Using external dirs:\n\t{0}'.format(
            '\n    '.join(['conf     = {0}'.format(confdir),
                           'data     = {0}'.format(datadir),
                           'log      = {0}'.format(logdir)],
            )))
    log.info('sys.path:\n\t{0}'.format('\n\t'.join(str(p) for p in sys.path)))
        
    return OpenVisualizerApp(
        confdir             = confdir,
        datadir             = datadir,
        logdir              = logdir,
        simulatorMode       = argspace.simulatorMode,
        numMotes            = argspace.numMotes,
        trace               = argspace.trace,
        debug               = argspace.debug,
        usePageZero         = argspace.usePageZero,
        simTopology         = argspace.simTopology,
        iotlabmotes         = argspace.iotlabmotes,
        testbed             = argspace.testbed,
        pathTopo            = argspace.pathTopo,
        benchmark           = argspace.benchmark,
        mqtt_broker_address = argspace.mqtt_broker_address,
        opentun_null        = argspace.opentun_null
    )

def _addParserArgs(parser):
    parser.add_argument('-a', '--appDir', 
        dest       = 'appdir',
        default    = '.',
        action     = 'store',
        help       = 'working directory'
    )
    parser.add_argument('-s', '--sim', 
        dest       = 'simulatorMode',
        default    = False,
        action     = 'store_true',
        help       = 'simulation mode, with default of {0} motes'.format(DEFAULT_MOTE_COUNT)
    )
    parser.add_argument('-n', '--simCount', 
        dest       = 'numMotes',
        type       = int,
        default    = 0,
        help       = 'simulation mode, with provided mote count'
    )
    parser.add_argument('-t', '--trace',
        dest       = 'trace',
        default    = False,
        action     = 'store_true',
        help       = 'enables memory debugging'
    )
    parser.add_argument('-st', '--simTopology',
        dest       = 'simTopology',
        default    = '',
        action     = 'store',
        help       = 'force a certain toplogy (simulation mode only)'
    )
    parser.add_argument('-d', '--debug',
        dest       = 'debug',
        default    = False,
        action     = 'store_true',
        help       = 'enables application debugging'
    )
    parser.add_argument('-pagez', '--usePageZero',
        dest       = 'usePageZero',
        default    = False,
        action     = 'store_true',
        help       = 'use page number 0 in page dispatch (only works with one-hop)'
    )
    parser.add_argument('-iotm', '--iotlabmotes',
        dest       = 'iotlabmotes',
        default    = '',
        action     = 'store',
        help       = 'comma-separated list of IoT-LAB motes (e.g. "wsn430-9,wsn430-34,wsn430-3")'
    )
    parser.add_argument('-tb', '--testbed',
        dest       = 'testbed',
        default    = False,
        choices    = ['opentestbed', 'iotlab', 'wilab'],
        action     = 'store',
        help       = 'connect remote motes from a --testbed over OpenTestbed serial-MQTT bridge.'
    )
    parser.add_argument('-b', '--benchmark',
        dest       = 'benchmark',
        default    = False,
        choices    = ['building-automation', 'home-automation', 'industrial-monitoring', 'demo-scenario'],
        action     = 'store',
        help       = 'trigger --benchmark scenario using OpenBenchmark cloud service. see benchmark.6tis.ch'
    )
    parser.add_argument('--mqtt-broker-address',
        dest       = 'mqtt_broker_address',
        default    = 'argus.paris.inria.fr',
        action     = 'store',
        help       = 'MQTT broker address to use'
    )
    parser.add_argument('--opentun-null',
        dest       = 'opentun_null',
        default    = False,
        action     = 'store_true',
        help       = 'don\'t use TUN device'
    )
    parser.add_argument('-i', '--pathTopo', 
        dest       = 'pathTopo',
        default    = '',
        action     = 'store',
        help       = 'a topology can be loaded from a json file'
    )
    parser.add_argument('-ro', '--root',
        dest       = 'root',
        default    = '',
        action     = 'store',
        help       = 'set mote associated to serial port as root'
    )


def _forceSlashSep(ospath, debug):
    '''
    Converts a Windows-based path to use '/' as the path element separator.
    
    :param ospath: A relative or absolute path for the OS on which this process
                   is running
    :param debug:  If true, print extra logging info
    '''
    if os.sep == '/':
        return ospath
        
    head     = ospath
    pathlist = []
    while True:
        head, tail = os.path.split(head)
        if tail == '':
            pathlist.insert(0, head.rstrip('\\'))
            break
        else:
            pathlist.insert(0, tail)
            
    pathstr = '/'.join(pathlist)
    if debug:
        print pathstr
    return pathstr
    
def _initExternalDirs(appdir, debug):    
    '''
    Find and define confdir for config files and datadir for static data. Also
    return logdir for logs. There are several possiblities, searched in the order
    described below.

    1. Provided from command line, appdir parameter
    2. In the directory containing openVisualizerApp.py
    3. In native OS site-wide config and data directories
    4. In the openvisualizer package directory

    The directories differ only when using a native OS site-wide setup.
    
    :param debug: If true, print extra logging info
    :returns: 3-Tuple with config dir, data dir, and log dir
    :raises: RuntimeError if files/directories not found as expected
    '''
    if not appdir == '.':
        if not _verifyConfpath(appdir):
            raise RuntimeError('Config file not in expected directory: {0}'.format(appdir))
        if debug:
            print 'App data found via appdir'
        return appdir, appdir, appdir
    
    filedir = os.path.dirname(__file__)
    if _verifyConfpath(filedir):
        if debug:
            print 'App data found via openVisualizerApp.py'
        return filedir, filedir, filedir
        
    confdir      = appdirs.site_config_dir('openvisualizer', 'OpenWSN')
    # Must use system log dir on Linux since running as superuser.
    linuxLogdir  = '/var/log/openvisualizer'
    if _verifyConfpath(confdir):
        if not sys.platform.startswith('linux'):
            raise RuntimeError('Native OS external directories supported only on Linux')
            
        datadir = appdirs.site_data_dir('openvisualizer', 'OpenWSN')
        logdir  = linuxLogdir
        if os.path.exists(datadir):
            if not os.path.exists(logdir):
                os.mkdir(logdir)
            if debug:
                print 'App data found via native OS'
            return confdir, datadir, logdir
        else:
            raise RuntimeError('Cannot find expected data directory: {0}'.format(datadir))

    datadir = os.path.join(os.path.dirname(u.__file__), 'data')
    if _verifyConfpath(datadir):
        if sys.platform == 'win32':
            logdir = appdirs.user_log_dir('openvisualizer', 'OpenWSN', opinion=False)
        else:
            logdir = linuxLogdir
        if not os.path.exists(logdir):
            # Must make intermediate directories on Windows
            os.makedirs(logdir)
        if debug:
            print 'App data found via openvisualizer package'
            
        return datadir, datadir, logdir
    else:
        raise RuntimeError('Cannot find expected data directory: {0}'.format(datadir))
                    
def _verifyConfpath(confdir):
    '''
    Returns True if OpenVisualizer conf files exist in the provided 
    directory.
    '''
    confpath = os.path.join(confdir, 'openvisualizer.conf')
    return os.path.isfile(confpath)
