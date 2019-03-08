import threading
from   coap   import    coap,                    \
                        coapResource,            \
                        coapDefines as d,        \
                        coapOption as o,         \
                        coapUtils as u,          \
                        coapObjectSecurity as oscoap
import logging.handlers
try:
    from openvisualizer.eventBus import eventBusClient
    import openvisualizer.openvisualizer_utils
except ImportError:
    pass

import cojpDefines

log = logging.getLogger('JRC')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

import cbor
import binascii
import os

# ======================== Top Level JRC Class =============================
class JRC(eventBusClient.eventBusClient):
    def __init__(self, coapServer):
        # store params
        self.coapServer = coapServer

        self.coapResource = joinResource()

        self.coapServer.coapServer.addResource(self.coapResource)
        self.coapServer.coapServer.addSecurityContextHandler(contextHandler(self.coapResource).securityContextLookup)

        # initialize parent class
        eventBusClient.eventBusClient.__init__(
            self,
            name='JRC',
            registrations=[
                {
                    'sender': self.WILDCARD,
                    'signal': 'getL2SecurityKey',
                    'callback': self._getL2SecurityKey_notif,
                },

            ]
        )

    # ======================== public ==========================================

    def close(self):
        self.coapServer.close()

    # ==== handle EventBus notifications

    def _getL2SecurityKey_notif(self, sender, signal, data):
        '''
        Return L2 security key for the network.
        '''
        return {'index': [self.coapResource.networkKeyIndex], 'value': self.coapResource.networkKey}

# ======================== Security Context Handler =========================
class contextHandler():
    MASTERSECRET = binascii.unhexlify('DEADBEEFCAFEDEADBEEFCAFEDEADBEEF') # value of the OSCORE Master Secret from 6TiSCH TD

    def __init__(self, joinResource):
        self.joinResource = joinResource

    # ======================== Context Handler needs to be registered =============================
    def securityContextLookup(self, kid):
        kidBuf = u.str2buf(kid)

        eui64 = kidBuf[:-1]
        senderID = eui64 + [0x01]  # sender ID of JRC is reversed
        recipientID = eui64 + [0x00]

        # if eui-64 is found in the list of joined nodes, return the appropriate context
        # this is important for replay protection
        for dict in self.joinResource.joinedNodes:
            if dict['eui64'] == u.buf2str(eui64):
                log.info("Node {0} found in joinedNodes. Returning context {1}.".format(binascii.hexlify(dict['eui64']),
                                                                                        str(dict['context'])))
                return dict['context']

        # if eui-64 is not found, create a new tentative context but only add it to the list of joined nodes in the GET
        # handler of the join resource
        context = oscoap.SecurityContext(masterSecret=self.MASTERSECRET,
                                         senderID=u.buf2str(senderID),
                                         recipientID=u.buf2str(recipientID),
                                         aeadAlgorithm=oscoap.AES_CCM_16_64_128())

        log.info("Node {0} not found in joinedNodes. Instantiating new context based on the master secret.".format(
            binascii.hexlify(u.buf2str(eui64))))

        return context

# ==================== Implementation of CoAP join resource =====================
class joinResource(coapResource.coapResource):
    def __init__(self):
        self.joinedNodes = []

        self.networkKey = u.str2buf(os.urandom(16)) # random key every time OpenVisualizer is initialized
        self.networkKeyIndex = 0x01 # L2 key index

        # initialize parent class
        coapResource.coapResource.__init__(
            self,
            path = 'j',
        )

        self.addSecurityBinding((None, [d.METHOD_POST]))  # security context should be returned by the callback

    def POST(self,options=[], payload=[]):

        link_layer_keyset = [self.networkKeyIndex, u.buf2str(self.networkKey)]

        configuration = {}

        configuration[cojpDefines.COJP_PARAMETERS_LABELS_LLKEYSET]   = link_layer_keyset
        configuration_serialized = cbor.dumps(configuration)

        respPayload     = [ord(b) for b in configuration_serialized]

        objectSecurity = oscoap.objectSecurityOptionLookUp(options)

        if objectSecurity:
            # we need to add the pledge to a list of joined nodes, if not present already
            eui64 = u.buf2str(objectSecurity.kid[:-1])
            found = False
            for node in self.joinedNodes:
                if node['eui64'] == eui64:
                    found = True
                    break

            if not found:
                self.joinedNodes += [
                                        { 'eui64'   : eui64, # remove last prepended byte
                                          'context' : objectSecurity.context
                                        }
                                    ]

            # return the Join Response regardless of whether it is a first or Nth join attempt
            return (d.COAP_RC_2_04_CHANGED, [], respPayload)
        else:
            return (d.COAP_RC_4_01_UNAUTHORIZED, [], [])

if __name__ == "__main__":

    fileLogger = logging.handlers.RotatingFileHandler(
        filename    = 'test.log',
        mode        = 'w',
        backupCount = 5,
    )
    fileLogger.setFormatter(
        logging.Formatter(
            '%(asctime)s [%(name)s:%(levelname)s] %(message)s'
        )
    )

    consoleLogger = logging.StreamHandler()
    consoleLogger.setLevel(logging.DEBUG)

    for loggerName in [
            'coap',
            'coapOption',
            'coapUri',
            'coapTransmitter',
            'coapMessage',
            'socketUdpReal',
        ]:
        temp = logging.getLogger(loggerName)
        temp.setLevel(logging.DEBUG)
        temp.addHandler(fileLogger)
        temp.addHandler(consoleLogger)
    
    log = logging.getLogger('JRC')
    log.setLevel(logging.DEBUG)
    log.addHandler(fileLogger)
    log.addHandler(consoleLogger)
 
    c = coap.coap()

    joinResource = joinResource()

    c.addResource(joinResource)

    c.addSecurityContextHandler(JRCSecurityContextLookup) # register callback


    raw_input('\n\nServer running. Press Enter to close.\n\n')
    
    c.close()

