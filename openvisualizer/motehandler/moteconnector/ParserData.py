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


def init_pkt_info():
    return {
                        'asn'            : 0,
                        'src_id'      : None,
                        'counter'        : 0,
                        'latency'        : 0,
                        'numCellsUsedTx' : 0,
                        'numCellsUsedRx' : 0,
                        'dutyCycle'      : 0
    }

class ParserData(Parser.Parser):
    
    HEADER_LENGTH  = 2
    MSPERSLOT      = 0.02 #second per slot.
    
    IPHC_SAM       = 4
    IPHC_DAM       = 0
    
    UINJECT_MASK    = 'uinject'
     
    def __init__(self, mqtt_broker_address):
        
        # log
        log.info("create instance")
        
        # initialize parent class
        Parser.Parser.__init__(self,self.HEADER_LENGTH)
        
        self._asn= ['asn_4',                     # B
          'asn_2_3',                   # H
          'asn_0_1',                   # H
         ]

        self.avg_kpi = {}

        self.broker                    = mqtt_broker_address
        self.mqttconnected             = False

        if not (self.broker == 'null'):

             # connect to MQTT
            self.mqttclient                = mqtt.Client()
            self.mqttclient.on_connect     = self._on_mqtt_connect

            try:
                self.mqttclient.connect(self.broker)
            except Exception as e:
                log.error("Failed to connect to {} with error msg: {}".format(self.broker, e))
            else: 
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
        offset  = 0
        if len(input) >37:
            offset -= 7
            if self.UINJECT_MASK == ''.join(chr(i) for i in input[offset:]):
                                
                pkt_info = init_pkt_info()

                pkt_info['counter']      = input[offset-2] + 256*input[offset-1]                   # counter sent by mote
                offset -= 2

                pkt_info['asn']          = struct.unpack('<I',''.join([chr(c) for c in input[offset-5:offset-1]]))[0]
                aux                      = input[offset-5:offset]                               # last 5 bytes of the packet are the ASN in the UDP latency packet
                diff                     = self._asndiference(aux,asnbytes)            # calculate difference 
                pkt_info['latency']      = diff                                        # compute time in slots
                offset -= 5
                
                pkt_info['numCellsUsedTx'] = input[offset-1]
                offset -=1

                pkt_info['numCellsUsedRx'] = input[offset-1]
                offset -=1

                pkt_info['src_id']       = ''.join(['%02x' % x for x in [input[offset-1],input[offset-2]]]) # mote id
                src_id                   = pkt_info['src_id']
                offset -=2

                numTicksOn               = struct.unpack('<I',''.join([chr(c) for c in input[offset-4:offset]]))[0]
                offset -= 4

                numTicksInTotal          = struct.unpack('<I',''.join([chr(c) for c in input[offset-4:offset]]))[0]
                offset -= 4

                pkt_info['dutyCycle']    = float(numTicksOn)/float(numTicksInTotal)    # duty cycle
                
                print pkt_info
                with open('pkt_info.log'.format(),'a') as f:
                    f.write(str(pkt_info)+'\n')
                
                # self.avg_kpi:
                if src_id in self.avg_kpi:
                    self.avg_kpi[src_id]['counter'].append(pkt_info['counter'])
                    self.avg_kpi[src_id]['latency'].append(pkt_info['latency'])
                    self.avg_kpi[src_id]['numCellsUsedTx'].append(pkt_info['numCellsUsedTx'])
                    self.avg_kpi[src_id]['numCellsUsedRx'].append(pkt_info['numCellsUsedRx'])
                    self.avg_kpi[src_id]['dutyCycle'].append(pkt_info['dutyCycle'])
                else:
                    self.avg_kpi[src_id] = {
                        'counter'        : [pkt_info['counter']],
                        'latency'        : [pkt_info['latency']],
                        'numCellsUsedTx' : [pkt_info['numCellsUsedTx']],
                        'numCellsUsedRx' : [pkt_info['numCellsUsedRx']],
                        'dutyCycle'      : [pkt_info['dutyCycle'] ],
                        'avg_cellsUsage' : 0.0,
                        'avg_latency'    : 0.0,
                        'avg_pdr'        : 0.0
                    }

                if self.mqttconnected:
                    self.publish_kpi(src_id)

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

#========================== mqtt publish ====================================

    def publish_kpi(self, src_id):

        payload = {
            'token':       123,
        }
        

        mote_data = self.avg_kpi[src_id]

        self.avg_kpi[src_id]['avg_cellsUsage'] = float(sum(mote_data['numCellsUsedTx'])/len(mote_data['numCellsUsedTx']))/float(64)
        self.avg_kpi[src_id]['avg_latency']    = sum(self.avg_kpi[src_id]['latency'])/len(self.avg_kpi[src_id]['latency'])
        mote_data['counter'].sort() # sort the counter before calculating
        self.avg_kpi[src_id]['avg_pdr']        = float(len(set(mote_data['counter'])))/float(1+mote_data['counter'][-1]-mote_data['counter'][0])

        avg_pdr_all           = 0.0
        avg_latency_all       = 0.0
        avg_numCellsUsage_all = 0.0

        for mote, data in self.avg_kpi.items():
            avg_pdr_all           += data['avg_pdr']
            avg_latency_all       += data['avg_latency']
            avg_numCellsUsage_all += data['avg_cellsUsage']

        numMotes = len(self.avg_kpi)
        avg_pdr_all                = avg_pdr_all/float(numMotes)
        avg_latency_all            = avg_latency_all/float(numMotes)
        avg_numCellsUsage_all      = avg_numCellsUsage_all/float(numMotes)

        payload['avg_cellsUsage']  = avg_numCellsUsage_all
        payload['avg_latency']     = avg_latency_all
        payload['avg_pdr']         = avg_pdr_all
        payload['src_id']          = src_id


        print payload

        if self.mqttconnected:
            # publish the cmd message
            self.mqttclient.publish(
                topic   = 'opentestbed/uinject/arrived',
                payload = json.dumps(payload),
                qos=2
            )

