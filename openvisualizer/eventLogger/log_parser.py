# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import traceback
import time
import json
import os
import matplotlib.pyplot as plt
import numpy as np

# pre-define

root_node_id = 'b6-0b'

# input file data
log_file_path = ".\\..\\..\\"
input_files = [file for file in os.listdir(log_file_path) if file.startswith("eventLog_")]

# output

result = {
    'num_nodes_synchronized':{
        'num_nodes':        [0],
        'time':             [0],
    },
    'num_nodes_joined':{
        'num_nodes':        [0],
        'time':             [0],
    },
    'num_nodes_hasNegotiatedTxcell':{
        'num_nodes':        [0],
        'time':             [0],
    },
}

# helper

def time_translate(asn_string):
    # change to minutes
    return int(asn_string,16)*0.02/60
    

# get result

for file in input_files:
    print "processing with file {0}...".format(file)
    with open(log_file_path+file, 'r') as f:
        
        node_id                     = file.split('.')[-2][-5:]
        sync_flag                   = 0
        
        synchronized                    = False
        joined                          = False
        negotiated_tx_cell_installed    = False
        
        synchronized_asn                    = 0
        joined_asn                          = 0
        negotiated_tx_cell_installed_asn    = 0
        
        lineCounter = 0
        for line in f:
            # get line in dictionary format
            
            lineCounter += 1
            try:
                eval_line = eval(line)
            except SyntaxError as s_error:
                print "error happened when parsing {0} file at line {1}, errorMessage: {2}".format(file,lineCounter,s_error)
                
            # get the lastest asn
            
            if len(eval_line) == 1 and 'asn' in eval_line:
                latestAsn = time_translate(eval_line['asn'])
                
            # get num_nodes_synchronized result
            
            if 'isSync' in eval_line.keys() and eval_line['isSync'] != sync_flag:
                sync_flag = eval_line['isSync']
                if sync_flag == 1:
                    synchronized        = True
                    synchronized_asn    = latestAsn
                else:
                    synchronized = False
                
            # get num_nodes_joined result
            
            if 'joinedAsn' in eval_line.keys():
                joined      = True
                joined_asn  = time_translate(eval_line['joinedAsn'])
                
            # get num_nodes_hasNegotiatedTxcell result
                
            if 'slotOffset' in eval_line.keys() and 'type' in eval_line.keys() and eval_line['type'] == '1 (TX)' and eval_line['shared'] == 0:
                negotiated_tx_cell_installed        = True
                negotiated_tx_cell_installed_asn    = time_translate(eval_line['lastUsedAsn'])
                
                
            if synchronized and joined and negotiated_tx_cell_installed:
                break
        
        # collect data
        
        if synchronized:
            pre_num_nodes = result['num_nodes_synchronized']['num_nodes'][-1]+1
            result['num_nodes_synchronized']['num_nodes'].append(pre_num_nodes)
            result['num_nodes_synchronized']['time'].append(synchronized_asn)
        
        if joined:
            pre_num_nodes = result['num_nodes_joined']['num_nodes'][-1]+1
            result['num_nodes_joined']['num_nodes'].append(pre_num_nodes)
            result['num_nodes_joined']['time'].append(joined_asn)
            
        if negotiated_tx_cell_installed:
            pre_num_nodes = result['num_nodes_hasNegotiatedTxcell']['num_nodes'][-1]+1
            result['num_nodes_hasNegotiatedTxcell']['num_nodes'].append(pre_num_nodes)
            result['num_nodes_hasNegotiatedTxcell']['time'].append(negotiated_tx_cell_installed_asn)

# plot

for key, item in result.items():
    item['time'] = sorted(item['time'])
    plt.plot(item['time'], item['num_nodes'],label=key)
plt.xlabel('time (minutes)')
plt.ylabel('num_nodes')
plt.legend(loc=4)
plt.grid(True)
plt.savefig('network_form_info.png')
plt.clf()