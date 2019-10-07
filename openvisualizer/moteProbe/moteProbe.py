# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
import logging
log = logging.getLogger('moteProbe')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

import os
if os.name=='nt':       # Windows
   import _winreg as winreg
elif os.name=='posix':  # Linux
   import glob
   import platform      # To recognize MAC OS X
import threading

import serial
import socket
import time
import sys

import paho.mqtt.client as mqtt
import json
import Queue

from   pydispatch import dispatcher
import OpenHdlc
import openvisualizer.openvisualizer_utils as u
from   openvisualizer.moteConnector import OpenParser
from   openvisualizer.moteConnector.SerialTester import SerialTester

#============================ defines =========================================

BAUDRATE_LOCAL_BOARD  = 115200
BAUDRATE_IOTLAB       = 500000

#============================ functions =======================================

def findSerialPorts(isIotMotes=False):
    '''
    Returns the serial ports of the motes connected to the computer.
    
    :returns: A list of tuples (name,baudrate) where:
        - name is a strings representing a serial port, e.g. 'COM1'
        - baudrate is an int representing the baurate, e.g. 115200
    '''
    serialports = []
    
    if os.name=='nt':
        path = 'HARDWARE\\DEVICEMAP\\SERIALCOMM'
        skip = False
        try :
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
        except :
            # No mote is connected
            skip = True
        if not skip :
            for i in range(winreg.QueryInfoKey(key)[1]):
                try:
                    val = winreg.EnumValue(key,i)
                except:
                    pass
                else:
                    serialports.append( (str(val[1]),BAUDRATE_LOCAL_BOARD) )
    elif os.name=='posix':
        if platform.system() == 'Darwin':
            portMask = ['/dev/tty.usbserial-*']
        else:
            portMask = ['/dev/ttyUSB*']
        for mask in portMask :
            serialports += [(s,BAUDRATE_IOTLAB) for s in glob.glob(mask)]

    mote_ports = []

    if isIotMotes:
        # this is IoTMotes, use the ports directly
        mote_ports = serialports
    else:
        # Find all OpenWSN motes that answer to TRIGGERSERIALECHO commands
        for port in serialports:
            probe = moteProbe(mqtt_broker_address=None, serialport=(port[0],BAUDRATE_LOCAL_BOARD))
            while hasattr(probe, 'serial')==False:
                pass
            tester = SerialTester(probe)
            tester.setNumTestPkt(1)
            tester.setTimeout(2)
            tester.test(blocking=True)
            if tester.getStats()['numOk'] >= 1:
                mote_ports.append((port[0],BAUDRATE_LOCAL_BOARD));
            probe.close()
            probe.join()
    
    # log
    log.info("discovered following COM port: {0}".format(['{0}@{1}'.format(s[0],s[1]) for s in mote_ports]))
    
    return mote_ports

#============================ class ===========================================

class OpentestbedMoteFinder (object):

    OPENTESTBED_RESP_STATUS_TIMEOUT     = 10

    def __init__(self, testbed, mqtt_broker_address):
        self.testbed = testbed
        self.mqtt_broker_address = mqtt_broker_address
        self.opentestbed_motelist = set()
        
    def get_opentestbed_motelist(self):
        
        # create mqtt client
        mqtt_client                = mqtt.Client('FindMotes')
        mqtt_client.on_connect     = self._on_mqtt_connect
        mqtt_client.on_message     = self._on_mqtt_message
        mqtt_client.connect(self.mqtt_broker_address)
        mqtt_client.loop_start()
        
        # wait for a while to gather the response from otboxes
        time.sleep(self.OPENTESTBED_RESP_STATUS_TIMEOUT)
        
        # close the client and return the motes list
        mqtt_client.loop_stop()
        
        print "{0} motes are found".format(len(self.opentestbed_motelist))
        
        return self.opentestbed_motelist

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        
        print "connected to : {0}".format(self.mqtt_broker_address)
        
        client.subscribe('{0}/deviceType/box/deviceId/+/resp/status'.format(self.testbed))
        
        payload_status = {
            'token':       123,
        }
        # publish the cmd message
        client.publish(
            topic   = '{0}/deviceType/box/deviceId/all/cmd/status'.format(self.testbed),
            payload = json.dumps(payload_status),
        )


    def _on_mqtt_message(self, client, userdata, message):

        # get the motes list from payload
        payload_status = json.loads(message.payload)

        try:
            host = payload_status['returnVal']['host_name']
        except KeyError:
            host = payload_status['returnVal']['IP_address']
        except:
            host = ''
        
        for mote in payload_status['returnVal']['motes']:
            if 'EUI64' in mote:
                self.opentestbed_motelist.add(
                    (host, mote['EUI64'], self.testbed, self.mqtt_broker_address)
                )

class moteProbe(threading.Thread):
    
    MODE_SERIAL    = 'serial'
    MODE_EMULATED  = 'emulated'
    MODE_IOTLAB    = 'IoT-LAB'
    MODE_TESTBED   = 'opentestbed'
    MODE_ALL       = [
        MODE_SERIAL,
        MODE_EMULATED,
        MODE_IOTLAB,
        MODE_TESTBED,
    ]

    XOFF           = 0x13
    XON            = 0x11
    XONXOFF_ESCAPE = 0x12
    XONXOFF_MASK   = 0x10
    # XOFF            is transmitted as [XONXOFF_ESCAPE,           XOFF^XONXOFF_MASK]==[0x12,0x13^0x10]==[0x12,0x03]
    # XON             is transmitted as [XONXOFF_ESCAPE,            XON^XONXOFF_MASK]==[0x12,0x11^0x10]==[0x12,0x01]
    # XONXOFF_ESCAPE  is transmitted as [XONXOFF_ESCAPE, XONXOFF_ESCAPE^XONXOFF_MASK]==[0x12,0x12^0x10]==[0x12,0x02]
    
    def __init__(self,mqtt_broker_address,serialport=None,emulatedMote=None,iotlabmote=None,testbedmote=None):
        
        # verify params
        if   serialport:
            assert not emulatedMote
            assert not iotlabmote
            assert not testbedmote
            self.mode             = self.MODE_SERIAL
        elif emulatedMote:
            assert not serialport
            assert not iotlabmote
            assert not testbedmote
            self.mode             = self.MODE_EMULATED
        elif iotlabmote:
            assert not serialport
            assert not emulatedMote
            assert not testbedmote
            self.mode             = self.MODE_IOTLAB
        elif testbedmote:
            assert not serialport
            assert not emulatedMote
            assert not iotlabmote
            self.mode             = self.MODE_TESTBED
        else:
            raise SystemError()
        
        # store params
        if   self.mode==self.MODE_SERIAL:
            self.serialport         = serialport[0]
            self.baudrate           = serialport[1]
            self.portname           = self.serialport
        elif self.mode==self.MODE_EMULATED:
            self.emulatedMote       = emulatedMote
            self.portname           = 'emulated{0}'.format(self.emulatedMote.getId())
        elif self.mode==self.MODE_IOTLAB:
            self.iotlabmote         = iotlabmote
            self.portname           = 'IoT-LAB{0}'.format(iotlabmote)
        elif self.mode==self.MODE_TESTBED:
            (self.testbed_host, self.testbedmote_eui64, self.testbed, self.mqtt_broker_address) = testbedmote
            self.portname           = 'testbed_{0}_{1}_{2}'.format(self.testbed, self.testbed_host, self.testbedmote_eui64)
        else:
            raise SystemError()
        # at this moment, MQTT broker is used even if the mode is not
        # MODE_TESTBED; see moteConnector, OpenParser and ParserData.
        self.mqtt_broker_address = mqtt_broker_address

        # log
        log.info("creating moteProbe attaching to {0}".format(
                self.portname,
            )
        )
        
        # local variables
        self.hdlc                 = OpenHdlc.OpenHdlc()
        self.lastRxByte           = self.hdlc.HDLC_FLAG
        self.busyReceiving        = False
        self.inputBuf             = ''
        self.outputBuf            = []
        self.outputBufLock        = threading.RLock()
        self.dataLock             = threading.Lock()
        # flag to permit exit from read loop
        self.goOn                 = True
        
        self.sendToParser         = None # to be assigned
        
        if self.mode == self.MODE_TESTBED:
            # initialize variable for testbedmote
            self.serialbytes_queue       = Queue.Queue(maxsize=10) # create queue for receiving serialbytes messages
            
            # mqtt client
            self.mqttclient                = mqtt.Client()
            self.mqttclient.on_connect     = self._on_mqtt_connect
            self.mqttclient.on_message     = self._on_mqtt_message
            self.mqttclient.connect(self.mqtt_broker_address)
            self.mqttclient.loop_start()
        
        # initialize the parent class
        threading.Thread.__init__(self)
        
        # give this thread a name
        self.name                 = 'moteProbe@'+self.portname
        
        if self.mode in [self.MODE_EMULATED,self.MODE_IOTLAB]:
            # Non-daemonized moteProbe does not consistently die on close(),
            # so ensure moteProbe does not persist.
            self.daemon           = True
        
        # connect to dispatcher
        dispatcher.connect(
            self._sendData,
            signal = 'fromMoteConnector@'+self.portname,
        )
    
        # start myself
        self.start()
    
    #======================== thread ==========================================
    
    def run(self):
        try:
            # log
            log.info("start running")
        
            while self.goOn:     # open serial port
                
                # log 
                log.info("open port {0}".format(self.portname))
                
                if   self.mode==self.MODE_SERIAL:
                    self.serial = serial.Serial(self.serialport,self.baudrate,timeout=1,xonxoff=True,rtscts=False,dsrdtr=False)
                elif self.mode==self.MODE_EMULATED:
                    self.serial = self.emulatedMote.bspUart
                elif self.mode==self.MODE_IOTLAB:
                    self.serial = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                    self.serial.connect((self.iotlabmote,20000))
                elif self.mode==self.MODE_TESTBED:
                    # subscribe to topic: opentestbed/deviceType/mote/deviceId/00-12-4b-00-14-b5-b6-49/notif/frommoteserialbytes
                    self.mqtt_seriaqueue = self.serialbytes_queue
                else:
                    raise SystemError()
                
                while self.goOn: # read bytes from serial port
                    try:
                        if   self.mode==self.MODE_SERIAL:
                            rxBytes = self.serial.read(1)
                            if rxBytes == 0: # timeout
                                continue
                        elif self.mode==self.MODE_EMULATED:
                            rxBytes = self.serial.read()
                        elif self.mode==self.MODE_IOTLAB:
                            rxBytes = self.serial.recv(1024)
                        elif self.mode==self.MODE_TESTBED:
                            rxBytes = self.mqtt_seriaqueue.get()
                            rxBytes = [chr(i) for i in rxBytes]
                        else:
                            raise SystemError()
                    except Exception as err:
                        print err
                        log.warning(err)
                        time.sleep(1)
                        break
                    else:
                        for rxByte in rxBytes:
                            if      (
                                        (not self.busyReceiving)             and 
                                        self.lastRxByte==self.hdlc.HDLC_FLAG and
                                        rxByte!=self.hdlc.HDLC_FLAG
                                    ):
                                # start of frame
                                if log.isEnabledFor(logging.DEBUG):
                                    log.debug("{0}: start of hdlc frame {1} {2}".format(self.name, u.formatStringBuf(self.hdlc.HDLC_FLAG), u.formatStringBuf(rxByte)))
                                self.busyReceiving       = True
                                self.xonxoffEscaping     = False
                                self.inputBuf            = self.hdlc.HDLC_FLAG
                                self._addToInputBuf(rxByte)
                            elif    (
                                        self.busyReceiving                   and
                                        rxByte!=self.hdlc.HDLC_FLAG
                                    ):
                                # middle of frame
                                
                                self._addToInputBuf(rxByte)
                            elif    (
                                        self.busyReceiving                   and
                                        rxByte==self.hdlc.HDLC_FLAG
                                    ):
                                # end of frame
                                if log.isEnabledFor(logging.DEBUG):
                                    log.debug("{0}: end of hdlc frame {1} ".format(self.name, u.formatStringBuf(rxByte)))
                                self.busyReceiving       = False
                                self._addToInputBuf(rxByte)
                                
                                try:
                                    tempBuf = self.inputBuf
                                    self.inputBuf        = self.hdlc.dehdlcify(self.inputBuf)
                                    if log.isEnabledFor(logging.DEBUG):
                                        log.debug("{0}: {2} dehdlcized input: {1}".format(self.name, u.formatStringBuf(self.inputBuf), u.formatStringBuf(tempBuf)))
                                except OpenHdlc.HdlcException as err:
                                    log.warning('{0}: invalid serial frame: {2} {1}'.format(self.name, err, u.formatStringBuf(tempBuf)))
                                else:
                                    if self.sendToParser:
                                        self.sendToParser([ord(c) for c in self.inputBuf])
                            
                            self.lastRxByte = rxByte
                        
                    if self.mode==self.MODE_EMULATED:
                        self.serial.doneReading()
        except Exception as err:
            errMsg=u.formatCrashMessage(self.name,err)
            print errMsg
            log.critical(errMsg)
            sys.exit(-1)
        finally:
            if self.mode==self.MODE_SERIAL and self.serial is not None:
                self.serial.close()
    
    #======================== public ==========================================
    
    def getPortName(self):
        with self.dataLock:
            return self.portname
    
    def getSerialPortBaudrate(self):
        with self.dataLock:
            return self.baudrate
    
    def close(self):
        self.goOn = False
    
    #======================== private =========================================
    
    def _addToInputBuf(self,byte):
        if byte==chr(self.XONXOFF_ESCAPE):
            self.xonxoffEscaping = True
        else:
            if self.xonxoffEscaping==True:
                self.inputBuf += chr(ord(byte)^self.XONXOFF_MASK)
                self.xonxoffEscaping=False
            elif byte!=chr(self.XON) and byte!=chr(self.XOFF):
                self.inputBuf += byte
    
    def _sendData(self,data):
        
        # abort for IoT-LAB
        if self.mode==self.MODE_IOTLAB:
            return
        
        # frame with HDLC
        hdlcData = self.hdlc.hdlcify(data)
        
        if self.mode==self.MODE_TESTBED:
            payload_buffer = {
                'token':       123,
            }
            payload_buffer['serialbytes'] = [ord(i) for i in hdlcData]
            # publish the cmd message
            self.mqttclient.publish(
                topic   = '{0}/deviceType/mote/deviceId/{1}/cmd/tomoteserialbytes'.format(self.testbed, self.testbedmote_eui64),
                payload = json.dumps(payload_buffer),
            )
        else:
            # write to serial
            self.serial.write(hdlcData)

    #==== mqtt callback functions
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        
        client.subscribe('{0}/deviceType/mote/deviceId/{1}/notif/frommoteserialbytes'.format(self.testbed, self.testbedmote_eui64))
        
    def _on_mqtt_message(self, client, userdata, message):
    
        try:
            serialbytes = json.loads(message.payload)['serialbytes']
        except:
            print "Error: failed to parse message payload {0}".format(message.payload)
        else:
            try:
                self.serialbytes_queue.put(json.loads(message.payload)['serialbytes'], block = False)
            except:
                print "queue overflow"
