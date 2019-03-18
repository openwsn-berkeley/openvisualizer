# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
import logging
log = logging.getLogger('ParserData')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

import struct

from pydispatch import dispatcher

from ParserException import ParserException
import Parser

import paho.mqtt.client as mqtt
import threading
import json

OPENTESTBED_BROKER_ADDRESS          = "argus.paris.inria.fr"

class ParserData(Parser.Parser):
    
    HEADER_LENGTH  = 2
    MSPERSLOT      = 0.02 #second per slot.
    
    IPHC_SAM       = 4
    IPHC_DAM       = 0
    
    UINJECT_MASK    = 'uinject'
     
    def __init__(self):
        
        # log
        log.info("create instance")
        
        # initialize parent class
        Parser.Parser.__init__(self,self.HEADER_LENGTH)
        
        self._asn= ['asn_4',                     # B
          'asn_2_3',                   # H
          'asn_0_1',                   # H
         ]

        self.broker                    = OPENTESTBED_BROKER_ADDRESS
        self.mqttconnected             = False

         # connect to MQTT
        self.mqttclient                = mqtt.Client(self.UINJECT_MASK)
        self.mqttclient.on_connect     = self._on_mqtt_connect
        self.mqttclient.connect(self.broker)
    
        # start mqtt client
        self.mqttthread                = threading.Thread(
            name                       = 'mqtt_loop_thread',
            target                     = self.mqttclient.loop_forever
        )
        self.mqttthread.start()

     #======================== private =========================================

    def _on_mqtt_connect(self, client, userdata, flags, rc):

        log.info("Connected to MQTT")

        self.mqttconnected = True


    #======================== public ==========================================
    
    def parseInput(self,input):
        # log
        if log.isEnabledFor(logging.DEBUG):
            log.debug("received data {0}".format(input))
        
        # ensure input not short longer than header
        self._checkLength(input)
   
        headerBytes = input[:2]
        #asn comes in the next 5bytes.  
        
        asnbytes=input[2:7]
        (self._asn) = struct.unpack('<BHH',''.join([chr(c) for c in asnbytes]))
        
        #source and destination of the message
        dest = input[7:15]
        
        #source is elided!!! so it is not there.. check that.
        source = input[15:23]
        
        if log.isEnabledFor(logging.DEBUG):
            a="".join(hex(c) for c in dest)
            log.debug("destination address of the packet is {0} ".format(a))
        
        if log.isEnabledFor(logging.DEBUG):
            a="".join(hex(c) for c in source)
            log.debug("source address (just previous hop) of the packet is {0} ".format(a))
        
        # remove asn src and dest and mote id at the beginning.
        # this is a hack for latency measurements... TODO, move latency to an app listening on the corresponding port.
        # inject end_asn into the packet as well
        input = input[23:]
        
        if log.isEnabledFor(logging.DEBUG):
            log.debug("packet without source,dest and asn {0}".format(input))
        
        # when the packet goes to internet it comes with the asn at the beginning as timestamp.
         
        # cross layer trick here. capture UDP packet from udpLatency and get ASN to compute latency.
        if len(input) >37:
            if self.UINJECT_MASK == ''.join(chr(i) for i in input[-7:]):
                numCellsUsed = input[-15]
                aux          = input[-14:-9]                               # last 5 bytes of the packet are the ASN in the UDP latency packet
                diff         = self._asndiference(aux,asnbytes)            # calculate difference 
                latency      = diff*self.MSPERSLOT                         # compute time in ms
                counter      = input[-9] + 256*input[-8]                   # counter sent by mote
                l3_source    = "{0:x}{1:x}".format(input[-16], input[-17]) # mote id

                payload = {
                    'token':       123,
                }

                payload['l3_source']      = l3_source
                payload['numCellsUsed']   = numCellsUsed
                payload['latency']        = latency
                payload['counter']        = counter

                print payload

                # publish the cmd message
                self.mqttclient.publish(
                    topic   = 'opentestbed/uinject/arrived',
                    payload = json.dumps(payload),
                    qos=2
                )
                # in case we want to send the computed time to internet..
                # computed=struct.pack('<H', timeinus)#to be appended to the pkt
                # for x in computed:
                    #input.append(x)
            else:
                # no udplatency
                # print input
                pass     
        else:
            pass      
       
        eventType='data'
        # notify a tuple including source as one hop away nodes elide SRC address as can be inferred from MAC layer header
        return eventType, (source, input)

 #======================== private =========================================
 
    def _asndiference(self,init,end):
      
       asninit = struct.unpack('<HHB',''.join([chr(c) for c in init]))
       asnend  = struct.unpack('<HHB',''.join([chr(c) for c in end]))
       if asnend[2] != asninit[2]: #'byte4'
          return 0xFFFFFFFF
       else:
           pass
       
       return (0x10000*(asnend[1]-asninit[1])+(asnend[0]-asninit[0]))