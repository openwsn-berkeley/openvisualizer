# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

from abc import ABCMeta


class OpenType(object):
    __metaclass__ = ABCMeta


class TypeRssi(OpenType):
    def __init__(self):
        super(TypeRssi, self).__init__()

    def __str__(self):
        return '{0} dBm'.format(self.rssi)

    # ======================== public ==========================================

    def update(self, rssi):
        self.rssi = rssi


class TypeComponent(OpenType):
    COMPONENT_NULL = 0x00
    COMPONENT_OPENWSN = 0x01

    # cross-layers
    COMPONENT_IDMANAGER = 0x02
    COMPONENT_OPENQUEUE = 0x03
    COMPONENT_OPENSERIAL = 0x04
    COMPONENT_PACKETFUNCTIONS = 0x05
    COMPONENT_RANDOM = 0x06
    # PHY
    COMPONENT_RADIO = 0x07
    # MAClow
    COMPONENT_IEEE802154 = 0x08
    COMPONENT_IEEE802154E = 0x09

    # MAClow<->MAChigh ("virtual components")
    COMPONENT_SIXTOP_TO_IEEE802154E = 0x0a
    COMPONENT_IEEE802154E_TO_SIXTOP = 0x0b
    # MAChigh
    COMPONENT_SIXTOP = 0x0c
    COMPONENT_NEIGHBORS = 0x0d
    COMPONENT_SCHEDULE = 0x0e
    COMPONENT_SIXTOP_RES = 0x0f
    # IPHC
    COMPONENT_OPENBRIDGE = 0x10
    COMPONENT_IPHC = 0x11
    COMPONENT_FRAG = 0x12
    # IPv6
    COMPONENT_FORWARDING = 0x13
    COMPONENT_ICMPv6 = 0x14
    COMPONENT_ICMPv6ECHO = 0x15
    COMPONENT_ICMPv6ROUTER = 0x16
    COMPONENT_ICMPv6RPL = 0x17
    # TRAN
    COMPONENT_OPENUDP = 0x18
    COMPONENT_OPENCOAP = 0x19
    # secure join
    COMPONENT_CJOIN = 0x1a
    COMPONENT_OPENOSCOAP = 0x1b
    # applications
    COMPONENT_C6T = 0x1c
    COMPONENT_CEXAMPLE = 0x1d
    COMPONENT_CINFO = 0x1e
    COMPONENT_CLEDS = 0x1f
    COMPONENT_CSENSORS = 0x20
    COMPONENT_CSTORM = 0x21
    COMPONENT_CWELLKNOWN = 0x22
    COMPONENT_UECHO = 0x23
    COMPONENT_UINJECT = 0x24
    COMPONENT_RRT = 0x25
    COMPONENT_SECURITY = 0x26
    COMPONENT_USERIALBRIDGE = 0x27
    COMPONENT_UEXPIRATION = 0x28
    COMPONENT_UMONITOR = 0x29
    COMPONENT_CINFRARED = 0x2a

    def __init__(self):
        super(TypeComponent, self).__init__()

    def __str__(self):
        return '{0} ({1})'.format(self.type, self.desc)

    # ======================== public ==========================================

    def update(self, type):
        self.type = type

        if type == self.COMPONENT_NULL:
            self.desc = 'NULL'
        elif type == self.COMPONENT_OPENWSN:
            self.desc = 'OPENWSN'

        elif type == self.COMPONENT_IDMANAGER:
            self.desc = 'IDMANAGER'
        elif type == self.COMPONENT_OPENQUEUE:
            self.desc = 'OPENQUEUE'
        elif type == self.COMPONENT_OPENSERIAL:
            self.desc = 'OPENSERIAL'
        elif type == self.COMPONENT_PACKETFUNCTIONS:
            self.desc = 'PACKETFUNCTIONS'
        elif type == self.COMPONENT_RANDOM:
            self.desc = 'RANDOM'

        elif type == self.COMPONENT_RADIO:
            self.desc = 'RADIO'

        elif type == self.COMPONENT_IEEE802154:
            self.desc = 'IEEE802154'
        elif type == self.COMPONENT_IEEE802154E:
            self.desc = 'IEEE802154E'

        elif type == self.COMPONENT_SIXTOP_TO_IEEE802154E:
            self.desc = 'SIXTOP_TO_IEEE802154E'
        elif type == self.COMPONENT_IEEE802154E_TO_SIXTOP:
            self.desc = 'IEEE802154E_TO_SIXTOP'

        elif type == self.COMPONENT_SIXTOP:
            self.desc = 'SIXTOP'
        elif type == self.COMPONENT_SIXTOP_RES:
            self.desc = 'SIXTOP_RES'
        elif type == self.COMPONENT_NEIGHBORS:
            self.desc = 'NEIGHBORS '
        elif type == self.COMPONENT_SCHEDULE:
            self.desc = 'SCHEDULE'

        elif type == self.COMPONENT_OPENBRIDGE:
            self.desc = 'OPENBRIDGE'
        elif type == self.COMPONENT_IPHC:
            self.desc = 'IPHC'
        elif type == self.COMPONENT_FRAG:
            self.desc = '6LoWPAN FRAGMENT'

        elif type == self.COMPONENT_FORWARDING:
            self.desc = 'FORWARDING'
        elif type == self.COMPONENT_ICMPv6:
            self.desc = 'ICMPv6'
        elif type == self.COMPONENT_ICMPv6ECHO:
            self.desc = 'ICMPv6ECHO'
        elif type == self.COMPONENT_ICMPv6ROUTER:
            self.desc = 'ICMPv6ROUTER'
        elif type == self.COMPONENT_ICMPv6RPL:
            self.desc = 'ICMPv6RPL'

        elif type == self.COMPONENT_OPENUDP:
            self.desc = 'OPENUDP'
        elif type == self.COMPONENT_OPENCOAP:
            self.desc = 'OPENCOAP'

        elif type == self.COMPONENT_C6T:
            self.desc = 'C6T'
        elif type == self.COMPONENT_CEXAMPLE:
            self.desc = 'CEXAMPLE'
        elif type == self.COMPONENT_CINFO:
            self.desc = 'CINFO'
        elif type == self.COMPONENT_CLEDS:
            self.desc = 'CLEDS'
        elif type == self.COMPONENT_CSENSORS:
            self.desc = 'CSENSORS'
        elif type == self.COMPONENT_CWELLKNOWN:
            self.desc = 'CWELLKNOWN'
        elif type == self.COMPONENT_CSTORM:
            self.desc = 'COMPONENT_CSTORM'

        elif type == self.COMPONENT_UECHO:
            self.desc = 'UECHO'
        elif type == self.COMPONENT_UINJECT:
            self.desc = 'COMPONENT_UINJECT'

        elif type == self.COMPONENT_RRT:
            self.desc = 'RRT'

        elif type == self.COMPONENT_SECURITY:
            self.desc = 'SECURITY'

        elif type == self.COMPONENT_UEXPIRATION:
            self.desc = 'UEXPIRATION'

        elif type == self.COMPONENT_UMONITOR:
            self.desc = 'UMONITOR'

        elif type == self.COMPONENT_CJOIN:
            self.desc = 'CJOIN'

        elif type == self.COMPONENT_OPENOSCOAP:
            self.desc = 'OPENOSCOAP'

        else:
            self.desc = 'unknown'
            self.addr = None


class TypeCellType(OpenType):
    CELLTYPE_OFF = 0
    CELLTYPE_TX = 1
    CELLTYPE_RX = 2
    CELLTYPE_TXRX = 3
    CELLTYPE_SERIALRX = 4
    CELLTYPE_MORESERIALRX = 5

    def __init__(self):
        super(TypeCellType, self).__init__()

    def __str__(self):
        return '{0} ({1})'.format(self.type, self.desc)

    # ======================== public ==========================================

    def update(self, type):
        self.type = type
        if type == self.CELLTYPE_OFF:
            self.desc = 'OFF'
        elif type == self.CELLTYPE_TX:
            self.desc = 'TX'
        elif type == self.CELLTYPE_RX:
            self.desc = 'RX'
        elif type == self.CELLTYPE_TXRX:
            self.desc = 'TXRX'
        elif type == self.CELLTYPE_SERIALRX:
            self.desc = 'SERIALRX'
        elif type == self.CELLTYPE_MORESERIALRX:
            self.desc = 'MORESERIALRX'
        else:
            self.desc = 'unknown'
            self.addr = None


class TypeAsn(OpenType):
    def __init__(self):
        super(TypeAsn, self).__init__()

    def __str__(self):
        return '0x{0}'.format(''.join(["%.2x" % b for b in self.asn]))

    # ======================== public ==========================================

    def update(self, byte0_1, byte2_3, byte4):
        self.asn = [
            byte4,
            byte2_3 >> 8,
            byte2_3 % 256,
            byte0_1 >> 8,
            byte0_1 % 256,
        ]


class TypeAddr(OpenType):
    ADDR_NONE = 0
    ADDR_16B = 1
    ADDR_64B = 2
    ADDR_128B = 3
    ADDR_PANID = 4
    ADDR_PREFIX = 5
    ADDR_ANYCAST = 6

    def __init__(self):
        super(TypeAddr, self).__init__()

    def __str__(self):
        output = []
        if self.addr:
            output += ['-'.join(["%.2x" % b for b in self.addr])]

        output += [' ({0})'.format(self.desc)]
        return ''.join(output)

    # ======================== public ==========================================

    def update(self, type, body_h, body_l):
        full_addr = [
            body_h >> (8 * 0) & 0xff,
            body_h >> (8 * 1) & 0xff,
            body_h >> (8 * 2) & 0xff,
            body_h >> (8 * 3) & 0xff,
            body_h >> (8 * 4) & 0xff,
            body_h >> (8 * 5) & 0xff,
            body_h >> (8 * 6) & 0xff,
            body_h >> (8 * 7) & 0xff,
            body_l >> (8 * 0) & 0xff,
            body_l >> (8 * 1) & 0xff,
            body_l >> (8 * 2) & 0xff,
            body_l >> (8 * 3) & 0xff,
            body_l >> (8 * 4) & 0xff,
            body_l >> (8 * 5) & 0xff,
            body_l >> (8 * 6) & 0xff,
            body_l >> (8 * 7) & 0xff,
        ]

        self.type = type
        if type == self.ADDR_NONE:
            self.desc = 'None'
            self.addr = None
        elif type == self.ADDR_16B:
            self.desc = '16b'
            self.addr = full_addr[:2]
        elif type == self.ADDR_64B:
            self.desc = '64b'
            self.addr = full_addr[:8]
        elif type == self.ADDR_128B:
            self.desc = '128b'
            self.addr = full_addr
        elif type == self.ADDR_PANID:
            self.desc = 'panId'
            self.addr = full_addr[:2]
        elif type == self.ADDR_PREFIX:
            self.desc = 'prefix'
            self.addr = full_addr[:8]
        elif type == self.ADDR_ANYCAST:
            self.desc = 'anycast'
            self.addr = None
        else:
            self.desc = 'unknown'
            self.addr = None
