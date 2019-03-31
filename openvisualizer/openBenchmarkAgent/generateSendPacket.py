import paho.mqtt.client as mqtt
from argparse       import ArgumentParser
import json
import random

class PacketGenerator():
    OPENBENCHMARK_SENDPACKET_TOPIC = 'openbenchmark/experimentId/000/command/sendPacket'

    def __init__(self):
        self.parser = ArgumentParser()
        self._addParserArgs()

        self.argspace = self.parser.parse_args()

        self.confirmable = True if self.argspace.confirmable == 'True' else False
        self.mqttBroker = self.argspace.mqttBroker
        self.payloadLen = self.argspace.mqttBroker
        self.destEui64 = self.argspace.destEui64
        self.srcEui64 = self.argspace.srcEui64

        # mqtt client
        self.mqttClient = mqtt.Client('generateSendPacket')
        self.mqttClient.connect(self.mqttBroker)

        command = {
            'token' : '123',
            'source' : self.srcEui64,
            'destination' : self.destEui64,
            'packetsInBurst' : 1,
            'packetToken' : [0, random.randint(0,255), random.randint(0,255), random.randint(0,255), random.randint(0,255)],
            'packetPayloadLen' : 10,
            'confirmable' : self.confirmable
        }

        self.mqttClient.publish(
            topic=self.OPENBENCHMARK_SENDPACKET_TOPIC,
            payload=json.dumps(command),
        )

    def _addParserArgs(self):
        self.parser.add_argument('-c', '--confirmable',
                            dest='confirmable',
                            default='False',
                            action='store',
                            choices=['False', 'True'],
                            help='Whether a packet should be ack-ed at the app layer'
                            )
        self.parser.add_argument('-p', '--payloadLen',
                            dest='payloadLen',
                            default=10,
                            action='store',
                            help='Length of the payload in the packet to be sent.'
                            )
        self.parser.add_argument('-d', '--destEui64',
                            dest='destEui64',
                            default='14-15-92-cc-00-00-00-03',
                            action='store',
                            help='Destination EUI-64.'
                            )
        self.parser.add_argument('-s', '--srcEui64',
                            dest='srcEui64',
                            default='14-15-92-cc-00-00-00-01',
                            action='store',
                            help='Source EUI-64.'
                            )
        self.parser.add_argument('-b', '--mqttBroker',
                            dest='mqttBroker',
                            default='argus.paris.inria.fr',
                            action='store_true',
                            help='MQTT broker to use'
                            )

    def _on_mqtt_connect(self):
        pass

    def _on_mqtt_message(self):
        pass

if __name__ == '__main__':
    PacketGenerator()
