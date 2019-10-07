# DO NOT EDIT DIRECTLY!
# This file was generated automatically by GenStackDefines.py
# on Mon, 03 Jun 2019 19:43:06
#

components = {
   0: "NULL",
   1: "OPENWSN",
   2: "IDMANAGER",
   3: "OPENQUEUE",
   4: "OPENSERIAL",
   5: "PACKETFUNCTIONS",
   6: "RANDOM",
   7: "RADIO",
   8: "IEEE802154",
   9: "IEEE802154E",
  10: "SIXTOP_TO_IEEE802154E",
  11: "IEEE802154E_TO_SIXTOP",
  12: "SIXTOP",
  13: "NEIGHBORS",
  14: "SCHEDULE",
  15: "SIXTOP_RES",
  16: "OPENBRIDGE",
  17: "IPHC",
  18: "FORWARDING",
  19: "ICMPv6",
  20: "ICMPv6ECHO",
  21: "ICMPv6ROUTER",
  22: "ICMPv6RPL",
  23: "OPENUDP",
  24: "OPENCOAP",
  25: "CJOIN",
  26: "OPENOSCOAP",
  27: "C6T",
  28: "CEXAMPLE",
  29: "CINFO",
  30: "CLEDS",
  31: "CSENSORS",
  32: "CSTORM",
  33: "CWELLKNOWN",
  34: "UECHO",
  35: "UINJECT",
  36: "RRT",
  37: "SECURITY",
  38: "USERIALBRIDGE",
  39: "UEXPIRATION",
  40: "UMONITOR",
  41: "CINFRARED",
  42: "CBENCHMARK",
}

errorDescriptions = {
   1: "node joined",
   2: "OSCOAP sequence number reached maximum value",
   3: "OSCOAP buffer overflow detected (code location {0})",
   4: "OSCOAP replay protection failed",
   5: "OSCOAP decryption and tag verification failed",
   6: "Aborted join process (code location {0})",
   7: "unknown transport protocol {0} (code location {1})",
   8: "unsupported port number {0} (code location {1})",
   9: "received an echo request",
  10: "received an echo reply",
  11: "the received packet has expired",
  12: "packet expiry time reached, dropped",
  13: "unexpected DAO (code location {0}). A change maybe happened on dagroot node.",
  14: "unsupported ICMPv6 type {0} (code location {1})",
  15: "unsupported 6LoWPAN parameter {1} at location {0}",
  16: "no next hop for layer 3 destination {0:x}{1:x}",
  17: "invalid parameter",
  18: "invalid forward mode",
  19: "large DAGrank {0}, set to {1}",
  20: "packet discarded hop limit reached",
  21: "loop detected due to previous rank {0} lower than current node rank {1}",
  22: "upstream packet set to be downstream, possible loop.",
  23: "packet to forward is dropped (code location {0})",
  24: "neighbors table is full (max number of neighbor is {0})",
  25: "there is no sent packet in queue",
  26: "there is no received packet in queue",
  27: "schedule overflown",
  28: "sixtop return code {0} at sixtop state {1}",
  29: "there are {0} cells to request mote",
  30: "the cells reserved to request mote contains slot {0} and slot {1}",
  31: "wrong celltype {0} at slotOffset {1}",
  32: "unsupported IEEE802.15.4 parameter {1} at location {0}",
  33: "got desynchronized at slotOffset {0}",
  34: "synchronized at slotOffset {0}",
  35: "large timeCorr.: {0} ticks (code loc. {1})",
  36: "wrong state {0} in end of frame+sync",
  37: "wrong state {0} in startSlot, at slotOffset {1}",
  38: "wrong state {0} in timer fires, at slotOffset {1}",
  39: "wrong state {0} in start of frame, at slotOffset {1}",
  40: "wrong state {0} in end of frame, at slotOffset {1}",
  41: "maxTxDataPrepare overflows while at state {0} in slotOffset {1}",
  42: "maxRxAckPrepapare overflows while at state {0} in slotOffset {1}",
  43: "maxRxDataPrepapre overflows while at state {0} in slotOffset {1}",
  44: "maxTxAckPrepapre overflows while at state {0} in slotOffset {1}",
  45: "wdDataDuration overflows while at state {0} in slotOffset {1}",
  46: "wdRadio overflows while at state {0} in slotOffset {1}",
  47: "wdRadioTx overflows while at state {0} in slotOffset {1}",
  48: "wdAckDuration overflows while at state {0} in slotOffset {1}",
  49: "security error on frameType {0}, code location {1}",
  50: "getData asks for too few bytes, maxNumBytes={0}, fill level={1}",
  51: "the input buffer has overflown",
  52: "busy sending",
  53: "sendDone for packet I didn't send",
  54: "no free packet buffer (code location {0})",
  55: "freeing unused memory",
  56: "freeing memory unsupported memory",
  57: "unsupported command {0}",
  58: "unknown message type {0}",
  59: "wrong address type {0} (code location {1})",
  60: "bridge mismatch (code location {0})",
  61: "header too long, length {1} (code location {0})",
  62: "input length problem, length={0}",
  63: "booted",
  64: "invalid serial frame",
  65: "invalid packet frome radio, length {1} (code location {0})",
  66: "busy receiving when stop of serial activity, buffer input length {1} (code location {0})",
  67: "wrong CRC in input Buffer",
  68: "synchronized when received a packet",
  69: "the slot {0} to be added is already in schedule",
  70: "the received packet format is not supported (code location {0})",
  71: "the metadata type is not suppored",
  72: "maxretries reached (counter: {0})",
}

sixtop_returncode = {
   0: "RC_SUCCESS",
   1: "RC_EOL",
   2: "RC_ERROR",
   3: "RC_RESET",
   4: "RC_VER_ERR",
   5: "RC_SFID_ERR",
   6: "RC_SEQNUM_ERR",
   7: "RC_CELLLIST_ERR",
   8: "RC_BUSY",
   9: "RC_LOCKED",
}

sixtop_statemachine = {
   0: "IDLE",
   1: "WAIT_ADDREQUEST_SENDDONE",
   2: "WAIT_DELETEREQUEST_SENDDONE",
   3: "WAIT_RELOCATEREQUEST_SENDDONE",
   4: "WAIT_COUNTREQUEST_SENDDONE",
   5: "WAIT_LISTREQUEST_SENDDONE",
   6: "WAIT_CLEARREQUEST_SENDDONE",
   7: "WAIT_ADDRESPONSE",
   8: "WAIT_DELETERESPONSE",
   9: "WAIT_RELOCATERESPONSE",
  10: "WAIT_COUNTRESPONSE",
  11: "WAIT_LISTRESPONSE",
  12: "WAIT_CLEARRESPONSE",
}
