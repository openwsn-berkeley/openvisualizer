#!/usr/bin/python
# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import sys
import os

if __name__=="__main__":
    # Update pythonpath if running in in-tree development mode
    basedir  = os.path.dirname(__file__)
    confFile = os.path.join(basedir, "openvisualizer.conf")
    if os.path.exists(confFile):
        import pathHelper
        pathHelper.updatePath()

import logging
log = logging.getLogger('openVisualizerGui')

try:
    from openvisualizer.motehandler.motestate import motestate
except ImportError:
    # Debug failed lookup on first library import
    print 'ImportError: cannot find openvisualizer.motestate module'
    print 'sys.path:\n\t{0}'.format('\n\t'.join(str(p) for p in sys.path))

import openvisualizer_app
from openvisualizer.openUI import OpenWindow
from openvisualizer.openUI import OpenFrameState
from openvisualizer.openUI import OpenFrameButton
from openvisualizer.openUI import OpenFrameEventBus

import Tkinter

class MenuUpdateFrame(Tkinter.Frame):
    """Updates the motes menu items with mote 16-bit IDs"""
    
    def setMoteStateHandler(self,ms):
        self.ms              = ms
    
    def setMenuList(self,menuList):
        self.menuList        = menuList
    
    def updateMenuLabel(self,indexToUpdate):
        rawLabel  = self.ms.get_state_elem(motestate.MoteState.ST_IDMANAGER).get_16b_addr()
        if rawLabel:
            menuLabel = ''.join(['%02x'%b for b in rawLabel])
            self.menuList.entryconfig(
                indexToUpdate,
                label=menuLabel,
            )

class OpenVisualizerGui(object):
    
    GUI_UPDATE_PERIOD      = 500
    MENUENTRY_STATE        = 'motes'
    MENUENTRY_LBR          = 'lbr'
    MENUENTRY_EVENTBUS     = 'eventBus'
    
    def __init__(self,app):
        """Sets menu names initially to serial port ID"""
        log.info('Creating OpenVisualizerGui')
        
        # store params
        self.app                    = app
        
        # local variables
        self.window                 = OpenWindow.OpenWindow("OpenVisualizer", self)
        
        #===== mote states frame
        menuNames                   = []
        self.menuFrames             = []
        for ms in self.app.moteStates:
            thisFrame               = MenuUpdateFrame(self.window)
            thisFrame.setMoteStateHandler(ms)
            frameOrganization = [
                [
                    motestate.MoteState.ST_ISSYNC,
                    motestate.MoteState.ST_ASN,
                    motestate.MoteState.ST_MYDAGRANK,
                    motestate.MoteState.ST_KAPERIOD,
                    motestate.MoteState.ST_OUPUTBUFFER,
                    motestate.MoteState.ST_BACKOFF,
                ],
                [
                    motestate.MoteState.TRIGGER_DAGROOT,
                    motestate.MoteState.ST_IDMANAGER,
                ],
                [
                    motestate.MoteState.ST_MACSTATS,
                ],
                [
                    motestate.MoteState.ST_SCHEDULE,
                    motestate.MoteState.ST_QUEUE,
                ],
                [
                    motestate.MoteState.ST_NEIGHBORS,
                ],
            ]
            for row in range(len(frameOrganization)):
                tempRowFrame = Tkinter.Frame(thisFrame)
                tempRowFrame.grid(row=row)
                for column in range(len(frameOrganization[row])):
                    stateOrTrigger = frameOrganization[row][column]
                    if   stateOrTrigger in motestate.MoteState.ST_ALL:
                        tempFrameState = OpenFrameState.OpenFrameState(
                            guiParent       = tempRowFrame,
                            frameName       = stateOrTrigger,
                            row             = 0,
                            column          = column,
                        )
                        tempFrameState.startAutoUpdate(
                            updatePeriod    = self.GUI_UPDATE_PERIOD,
                            updateFunc      = ms.get_state_elem,
                            updateParams    = (stateOrTrigger,),
                        )
                        tempFrameState.show()
                    elif stateOrTrigger in motestate.MoteState.TRIGGER_ALL:
                        tempFrameButton = OpenFrameButton.OpenFrameButton(
                            callfunction    = ms.trigger_action,
                            callparams      = (stateOrTrigger,),
                            guiParent       = tempRowFrame,
                            frameName       = stateOrTrigger,
                            buttonText      = 'Toggle DAG root state',
                            row             = 0,
                            column          = column,
                        )
                        tempFrameButton.show()
                    else:
                        raise SystemError('unexpected stateOrTrigger={0}'.format(stateOrTrigger))
            
            menuNames       += ['{0}'.format(ms.moteConnector.serialport)]
            self.menuFrames += [thisFrame]
        
        # Add to menu; returns Tkinter.Menu
        menuList = self.window.addMenuList(
            listname =  self.MENUENTRY_STATE,
            names =     menuNames,
            frames =    self.menuFrames,
        )
        
        for menuFrame in self.menuFrames:
            menuFrame.setMenuList(menuList)
        
        menuList.config(
            # Executes when menu displayed.
            postcommand=self._updateMenuFrameNames
        )
        
        #===== openLbr Frame
        # TODO
        
        #===== eventBusMonitor Frame
        
        thisFrame            = Tkinter.Frame(self.window)
        
        tempFrameEventBus    = OpenFrameEventBus.OpenFrameEventBus(
            thisFrame,
            self.app.eventBusMonitor,
            row=1
        )
        tempFrameEventBus.show()
        
        # add to menu
        self.window.addMenuItem(
            name =      self.MENUENTRY_EVENTBUS,
            frame =     thisFrame,
        )
        
    #======================== public ==========================================
    
    def start(self):
        self.window.startGui()
        
    def close(self):
        self.app.close()
    
    #======================== private =========================================
    
    def _updateMenuFrameNames(self):
        for i in range(len(self.menuFrames)):
            self.menuFrames[i].updateMenuLabel(i)


#============================ main ============================================

if __name__=="__main__":
    app = openvisualizer_app.main()
    gui = OpenVisualizerGui(app)
    gui.start()