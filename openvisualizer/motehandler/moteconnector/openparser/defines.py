# DO NOT EDIT DIRECTLY!
# This file was generated automatically by generate_defines.py
# on Tue, 31 Mar 2020 14:26:34
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
  18: "FRAG",
  19: "FORWARDING",
  20: "ICMPv6",
  21: "ICMPv6ECHO",
  22: "ICMPv6ROUTER",
  23: "ICMPv6RPL",
  24: "OPENUDP",
  25: "OPENCOAP",
  26: "CJOIN",
  27: "OSCORE",
  28: "C6T",
  29: "CEXAMPLE",
  30: "CINFO",
  31: "CLEDS",
  32: "CSENSORS",
  33: "CSTORM",
  34: "CWELLKNOWN",
  35: "UECHO",
  36: "UINJECT",
  37: "RRT",
  38: "SECURITY",
  39: "USERIALBRIDGE",
  40: "UEXPIRATION",
  41: "UMONITOR",
  42: "CINFRARED",
}

errorDescriptions = {
   1: "node joined",
   2: "sending CJOIN request",
   3: "OSCORE sequence number reached maximum value",
   4: "OSCORE buffer overflow detected (code location {0})",
   5: "OSCORE replay protection failed",
   6: "OSCORE decryption and tag verification failed",
   7: "Aborted join process (code location {0})",
   8: "unknown transport protocol {0} (code location {1})",
   9: "unsupported port number {0} (code location {1})",
  10: "invalid checksum, expected 0x{:04x}, found 0x{:04x}",
  11: "received an echo request",
  12: "received an echo reply",
  13: "the received packet has expired",
  14: "packet expiry time reached, dropped",
  15: "unexpected DAO (code location {0}). A change maybe happened on dagroot node.",
  16: "unsupported ICMPv6 type {0} (code location {1})",
  17: "unsupported 6LoWPAN parameter {1} at location {0}",
  18: "no next hop for layer 3 destination {0:x}{1:x}",
  19: "invalid parameter",
  20: "invalid forward mode",
  21: "large DAGrank {0}, set to {1}",
  22: "packet discarded hop limit reached",
  23: "loop detected due to previous rank {0} lower than current node rank {1}",
  24: "upstream packet set to be downstream, possible loop.",
  25: "packet to forward is dropped (code location {0})",
  26: "fragmentation buffer overflowed ({0} fragments queued)",
  27: "invalid original packet size ({0} > {1})",
  28: "reassembled fragments into big packet (size: {0}, tag: {1})",
  29: "fast-forwarded all fragments with tag {0} (total size: {1})",
  30: "stored a fragment with offset {0} (currently in buffer: {1})",
  31: "failed to send fragment with tag {0} (offset: {1})",
  32: "reassembly or vrb timer expired for fragments with tag {0}",
  33: "fragmenting a big packet, original size {0}, number of fragments {1}",
  34: "neighbors table is full (max number of neighbor is {0})",
  35: "there is no sent packet in queue",
  36: "there is no received packet in queue",
  37: "schedule overflown",
  38: "sixtop return code {0} at sixtop state {1}",
  39: "there are {0} cells to request mote",
  40: "the cells reserved to request mote contains slot {0} and slot {1}",
  41: "wrong celltype {0} at slotOffset {1}",
  42: "unsupported IEEE802.15.4 parameter {1} at location {0}",
  43: "got desynchronized at slotOffset {0}",
  44: "synchronized at slotOffset {0}",
  45: "large timeCorr.: {0} ticks (code loc. {1})",
  46: "wrong state {0} in end of frame+sync",
  47: "wrong state {0} in startSlot, at slotOffset {1}",
  48: "wrong state {0} in timer fires, at slotOffset {1}",
  49: "wrong state {0} in start of frame, at slotOffset {1}",
  50: "wrong state {0} in end of frame, at slotOffset {1}",
  51: "maxTxDataPrepare overflows while at state {0} in slotOffset {1}",
  52: "maxRxAckPrepapare overflows while at state {0} in slotOffset {1}",
  53: "maxRxDataPrepapre overflows while at state {0} in slotOffset {1}",
  54: "maxTxAckPrepapre overflows while at state {0} in slotOffset {1}",
  55: "wdDataDuration overflows while at state {0} in slotOffset {1}",
  56: "wdRadio overflows while at state {0} in slotOffset {1}",
  57: "wdRadioTx overflows while at state {0} in slotOffset {1}",
  58: "wdAckDuration overflows while at state {0} in slotOffset {1}",
  59: "security error on frameType {0}, code location {1}",
  60: "getData asks for too few bytes, maxNumBytes={0}, fill level={1}",
  61: "the input buffer has overflown",
  62: "busy sending",
  63: "sendDone for packet I didn't send",
  64: "no free packet buffer (code location {0})",
  65: "no free timer or queue entry (code location {0})",
  66: "freeing unused memory",
  67: "freeing memory unsupported memory",
  68: "unsupported command {0}",
  69: "unknown message type {0}",
  70: "wrong address type {0} (code location {1})",
  71: "bridge mismatch (code location {0})",
  72: "header too long, length {1} (code location {0})",
  73: "input length problem, length={0}",
  74: "booted",
  75: "invalid serial frame",
  76: "invalid packet from radio, length {1} (code location {0})",
  77: "busy receiving when stop of serial activity, buffer input length {1} (code location {0})",
  78: "wrong CRC in input Buffer",
  79: "synchronized when received a packet",
  80: "the slot {0} to be added is already in schedule",
  81: "the received packet format is not supported (code location {0})",
  82: "the metadata type is not suppored",
  83: "maxretries reached (counter: {0})",
  84: "empty queue or trying to remove unknown timer id (code location {0})",
  85: "debug {0} {1}",
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
