#!/usr/bin/env python

import wx
import multiprocessing
#import wx.richtext
#from wx.lib import wordwrap
#from wx.prop import basetableworker
# import warnings
# warnings.simplefilter("ignore")
#import matplotlib.pyplot as plt

import pdb
#from reremi import *

from siren.interface.classSiren import Siren
from siren.interface.classGridTable import CustRenderer

import time

## MAIN APP CLASS ###
class SirenApp(wx.App):
    def __init__(self, *args, **kwargs):
        wx.App.__init__(self, *args, **kwargs)
        # Catches events when the app is asked to activate by some other process
        self.Bind(wx.EVT_ACTIVATE_APP, self.OnActivate)

    def OnInit(self):
        # Set the app name here to *hard coded* Siren
        self.SetAppName("Siren")
        self.frame = Siren()

        import sys, os.path, platform
        if len(sys.argv) > 1 and platform.system() != 'Darwin':
            # On OSX, MacOpenFile() gets called with sys.argv's contents, so don't load anything here
            # DEBUG
            #print "Loading file", sys.argv[-1]
            filename = sys.argv[1]
            (p, ext) = os.path.splitext(filename)
            if ext == '.siren':
                self.frame.LoadFile(filename)
            elif ext == ".conf":
                self.frame.dw.importPreferencesFromFile(filename)
            elif ext == '.csv':
                # If the first file is .csv, check if we've got two files and use them as left and right files
                LHfile = filename
                RHfile = filename
                if len(sys.argv) > 2:
                    (f, ext2) = os.path.splitext(sys.argv[2])
                    if ext2 == '.csv':
                        RHfile = sys.argv[2]
                self.frame.dw.importDataFromCSVFiles([LHfile, RHfile, {}, 'NA'])
                self.frame.reloadAll()
            else:
                sys.stderr.write('Unknown data type "'+ext+'" for file '+filename)
                

        # if len(sys.argv) > 2 and sys.argv[-1] == "debug":
            # DEBUG
            # print "Loading file", sys.argv[-1]
            # self.frame.expand()

            # ### SPLITS
            # self.frame.dw.getData().extractFolds(1, 12)
            # splits_info = self.frame.dw.getData().getFoldsInfo()
            # stored_splits_ids = sorted(splits_info["split_ids"].keys(), key=lambda x: splits_info["split_ids"][x])
            # ids = {}
            # checked = [("learn", range(1,len(stored_splits_ids))), ("test", [0])]
            # for lt, bids in checked:
            #     ids[lt] = [stored_splits_ids[bid] for bid in bids]
            # self.frame.dw.getData().assignLT(ids["learn"], ids["test"])
            # self.frame.recomputeAll()

            # tab = "reds"
            # for i in self.frame.tabs[tab]["tab"].getDataHdl().getAllIids():
            #     mapV = self.frame.tabs[tab]["tab"].viewData(i, "MAP")
            #     mapV.mapFrame.SetClientSizeWH(1920, 1190)
            #     # mapV.mapFrame.SetClientSizeWH(1064, 744)
            #     # mapV.mapFrame.SetClientSizeWH(551, 375)
            #     # mapV.savefig("/home/egalbrun/R%d_map_2K-d100.pdf" % i, dpi=100, format="pdf")
            #     # mapV.savefig("/home/egalbrun/R%d_map_2K-d100.eps" % i, dpi=100, format="eps")
            #     mapV.savefig("/home/egalbrun/R%d_map_2K-d100.png" % i, format="png")
            #     mapV.OnKil()

            # self.frame.dw.getData().getMatrix()
            # self.frame.dw.getData().selected_rows = set(range(400))
            # self.frame.tabs[tab]["tab"].viewData(1, "TR")
            # self.frame.tabs[tab]["tab"].viewData(2, "MAP")
            # -- self.frame.tabs[tab]["tab"].viewData(2, "SKpca")
            # self.frame.tabs[tab]["tab"].viewListData(1, "INT")
            # self.frame.tabs[tab]["tab"].viewData(1, "TR")
            # self.frame.tabs[tab]["tab"].viewData(7, "PC")
            # self.frame.tabs[tab]["tab"].viewData(2, "PC")
            # self.frame.tabs[tab]["tab"].viewData(1, "SKrand_entities")
            # mapV = self.frame.getViewX(None, "PC")
            # pos = self.frame.tabs[tab]["tab"].getSelectedPos()
            # self.frame.tabs[tab]["tab"].registerView(mapV.getId(), pos)
            # mapV.setCurrent(self.frame.tabs[tab]["tab"].getSelectedItem(), self.frame.tabs["reds"]["tab"].tabId)
            
        return True

    def BringWindowToFront(self):
        try:
            pass
            #self.frame.toolFrame.Raise()
        except:
            pass

    def OnActivate(self, event):
        pass
        # if event.GetActive():
        #     self.BringWindowToFront()
        # event.Skip()

    def MacOpenFile(self, filename):
        """Called for files dropped on dock icon, or opened via Finder's context menu"""
        import sys, os.path
        sys.stderr.write('In MacOpenFile with filename '+filename)
        # When start from command line, this gets called with the script file's name
        if filename != sys.argv[0]:
            if self.frame.dw.getData() is not None:
                if not self.frame.checkAndProceedWithUnsavedChanges():
                    return
            (p, ext) = os.path.splitext(filename)
            if ext == '.siren':
                self.frame.LoadFile(filename)
            elif ext == '.csv':
                self.frame.dw.importDataFromCSVFiles([filename, filename, {}, 'NA'])
                self.frame.reloadAll()
            else:
                 wx.MessageDialog(self.frame.toolFrame, 'Unknown file type "'+ext+'" in file '+filename, style=wx.OK, caption='Unknown file type').ShowModal()

    def MacReopenApp(self):
        """Called when the doc icon is clicked, and ???"""
        self.BringWindowToFront()

    def MacNewFile(self):
        pass

    def MacPrintFile(self, filepath):
        pass

def siren_run():
    app = SirenApp(False)

    CustRenderer.BACKGROUND_SELECTED = wx.SystemSettings_GetColour( wx.SYS_COLOUR_HIGHLIGHT )
    CustRenderer.TEXT_SELECTED = wx.SystemSettings_GetColour( wx.SYS_COLOUR_HIGHLIGHTTEXT )
    CustRenderer.BACKGROUND = wx.SystemSettings_GetColour( wx.SYS_COLOUR_WINDOW  )
    CustRenderer.TEXT = wx.SystemSettings_GetColour( wx.SYS_COLOUR_WINDOWTEXT  )

    #app.frame = Siren()
    app.MainLoop()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    siren_run()
