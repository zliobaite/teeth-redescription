import wx
from classFiller import Filler

import pdb

######################################################################
###########     INTAB VIZ MANAGER
######################################################################

class VizManager:
    """ 
    Manages the visualizations tab, selecting the next visualization slot, etc.
    """

    viz_grid = [2,0]
    intab = False #True
    color_add = (16, 82, 0)
    color_drop = (190, 10, 10)
    color_vizb = (20, 20, 20)

    def __init__(self, parent, tabId, frame, short=None):
        self.parent = parent
        self.tabId = tabId
        self.short = short
        self.viz_postab = self.parent.tabs_keys.index(self.tabId)

        self.vfiller_ids = {}
        self.vused_ids = {}
        self.buttons = {}
        self.selected_cell = None
        
        self.drawSW(frame)
        self.initialize()
        
    def initialize(self):
        if self.parent.dw is not None:
            self.viz_grid = [self.parent.dw.getPreference('intab_nbr'),
                             self.parent.dw.getPreference('intab_nbc')]

        if self.hasVizIntab():
            self.fillInViz()
            self.addVizExts()
            self.setVizButtAble()
            self.updateVizcellSelected()
            # if not self.parent.tabs["viz"]["hide"] and self.parent.sysTLin():
            if self.parent.sysTLin():
                self.getSW().Show()
            if self.viz_postab >= len(self.parent.tabs_keys) or self.parent.tabs_keys[self.viz_postab] != "viz":
                # print "In Viz"
                self.parent.tabs_keys.insert(self.viz_postab, "viz")

        else:
            self.getSW().Hide()
            if self.viz_postab < len(self.parent.tabs_keys) and self.parent.tabs_keys[self.viz_postab] == "viz":
                # print "Pop Viz"
                self.parent.tabs_keys.pop(self.viz_postab)

    def getTitle(self):
        return self.short

    def setVizCheck(self, check=True):
        self.intab = check

    #### HERE INTAB SWITCH
    def showVizIntab(self):
        return self.hasVizIntab() and self.intab

    def hasVizIntab(self):
        return (self.viz_grid[0]*self.viz_grid[1]) > 0

    def isReadyVizIntab(self):
        return self.hasVizIntab() and hasattr(self, 'vfiller_ids') and len(self.vfiller_ids) + len(self.vused_ids) + len(self.buttons) > 0

    def getIcon(self, key):
        if self.hasParent() and key in self.parent.icons:
            return self.parent.icons[key]
        return wx.NullBitmap
    def getVizBbsiz(self):
        return 9
    def getVizBb(self):
        return self.getVizBbsiz()+3

    def drawSW(self, frame):
        self.sw = wx.ScrolledWindow(frame, -1, style=wx.HSCROLL|wx.VSCROLL)
        self.sw.SetScrollRate(5, 5)
        # sw.SetSizer(wx.GridSizer(rows=2, cols=3, vgap=0, hgap=0))
        self.sw.SetSizer(wx.GridBagSizer(vgap=0, hgap=0))

    def getSW(self):
        return self.sw

    def OnQuit(self):
        self.clearVizTab()

    def clearVizTab(self):
        for sel in self.vfiller_ids:
            panel = self.vfiller_ids[sel].popSizer()
            panel.Destroy()
        for sel in self.vused_ids:
            ### Free another view            
            self.parent.viewsm.accessViewX(self.vused_ids[sel][0]).OnQuit(upMenu=False, freeing=False)
            
        for bi, bb in self.buttons.items():
            self.getSW().GetSizer().Detach(bb["button"])
            bb["button"].Destroy()

        self.vfiller_ids = {}
        self.vused_ids = {}
        self.buttons = {}
        self.selected_cell = None

    def reloadVizTab(self):
        if self.isReadyVizIntab():
            self.clearVizTab()
        self.initialize()
        self.parent.doUpdates({"menu":True})
            
    def getVizcellSelected(self):
        return self.selected_cell
    def setVizcellSelected(self, pos):
        self.selected_cell = pos
    def updateVizcellSelected(self):
        if len(self.vfiller_ids) > 0:
            self.selected_cell = sorted(self.vfiller_ids.keys(), key=lambda x: x[0]+x[1])[0]
            uid = self.selected_cell
        else:
            self.selected_cell = sorted(self.vused_ids.keys(), key=lambda x: self.vused_ids[x][1])[0]
            uid = None
        self.setActiveViz(uid)

    def getVizPlotPos(self, vid):
        sel = self.getVizcellSelected()
        if sel in self.vfiller_ids:
            pv = self.vfiller_ids.pop(sel)
            panel = pv.popSizer()
            panel.Destroy()
        else:
            ### Free another view            
            self.parent.viewsm.accessViewX(self.vused_ids[sel][0]).OnQuit(upMenu=False, freeing=False)

        #### mark cell used    
        self.vused_ids[sel] = (vid, len(self.vused_ids))            
        self.updateVizcellSelected()
        return sel

    def getVizGridSize(self):
        return self.viz_grid
    def getVizGridNbDim(self, dim=None):
        if dim is None:
            return self.viz_grid
        else:
            return self.viz_grid[dim]
    
    def decrementVizGridDim(self, dim, id):
        self.viz_grid[dim] -= 1
        self.dropGridDimViz(dim, id)
        self.resizeViz()
        self.setVizButtAble()
        self.updateVizcellSelected()

    def incrementVizGridDim(self, dim):
        self.viz_grid[dim] += 1
        self.addGridDimViz(dim)
        self.resizeViz()
        self.setVizButtAble()
        self.updateVizcellSelected()
        
    def fillInViz(self):
        for i in range(1, self.getVizGridNbDim(0)+1):
            for j in range(1, self.getVizGridNbDim(1)+1):
                self.vfiller_ids[(i,j)] = Filler(self.parent, (i,j))

    def addGridDimViz(self, dim):
        for bi, but in self.buttons.items():
            if but["action"][1] == -1:
                self.getSW().GetSizer().Detach(but["button"])
                ddim = but["action"][0]
                ppos, pspan = ([1, 1], [1, 1])
                ppos[ddim] += self.getVizGridNbDim(ddim)
                pspan[1-ddim] = self.getVizGridNbDim(1-ddim)
                self.getSW().GetSizer().Add(but["button"], pos=ppos, span=pspan, flag=wx.EXPAND|wx.ALIGN_CENTER, border=0)

        sizeb = (self.getVizBbsiz(), 1)
        bid = wx.NewId()
        but = wx.Button(self.getSW(), bid, "", style=wx.NO_BORDER, size=(sizeb[dim], sizeb[1-dim]))
        but.SetBackgroundColour(self.color_drop)
        posb = [0,0]
        posb[dim] = self.getVizGridNbDim(dim)
        self.getSW().GetSizer().Add(but, pos=tuple(posb), flag=wx.EXPAND|wx.ALIGN_CENTER, border=0)
        self.buttons[bid] = {"action": (dim, self.getVizGridNbDim(dim)), "button": but}
        but.Bind(wx.EVT_BUTTON, self.OnChangeGridViz)
        ## but.Bind(wx.EVT_ENTER_WINDOW, self.OnPrintName)

        ppos = [self.getVizGridNbDim(dim), self.getVizGridNbDim(dim)]
        for i in range(1, self.getVizGridNbDim(1-dim)+1):
            ppos[1-dim] = i
            self.vfiller_ids[tuple(ppos)] = Filler(self.parent, tuple(ppos))

    def dropGridDimViz(self, dim, cid):
        ssel = [0,0]
        ssel[dim] = cid
        for i in range(1, self.getVizGridNbDim(1-dim)+1):
            ssel[1-dim] = i
            sel = tuple(ssel)
            if sel in self.vfiller_ids:
                pv = self.vfiller_ids.pop(sel)
                panel = pv.popSizer()
                panel.Destroy()
            else:
                # ## Free another view
                self.parent.viewsm.accessViewX(self.vused_ids[sel][0]).OnQuit(upMenu=False, freeing=False)

        for ccid in range(cid+1, self.getVizGridNbDim(dim)+2):
            ssel = [0,0]
            ssel[dim] = ccid
            nnel = [0,0]
            nnel[dim] = ccid-1

            for i in range(1, self.getVizGridNbDim(1-dim)+1):
                ssel[1-dim] = i
                nnel[1-dim] = i
                sel = tuple(ssel)
                nel = tuple(nnel)
                if sel in self.vfiller_ids:
                    self.vfiller_ids[sel].resetGPos(nel)
                    self.vfiller_ids[nel] = self.vfiller_ids.pop(sel)
                else:
                    self.parent.accessViewX(self.vused_ids[sel][0]).resetGPos(nel)
                    self.vused_ids[nel] = self.vused_ids.pop(sel)
                    
        ### adjust buttons
        bis = self.buttons.keys()
        for bi in bis:
            but = self.buttons[bi]
            if but["action"][1] == -1:
                self.getSW().GetSizer().Detach(but["button"])
                ddim = but["action"][0]
                ppos, pspan = ([1, 1], [1, 1])
                ppos[ddim] += self.getVizGridNbDim(ddim)
                pspan[1-ddim] = self.getVizGridNbDim(1-ddim)
                self.getSW().GetSizer().Add(but["button"], pos=ppos, span=pspan, flag=wx.EXPAND|wx.ALIGN_CENTER, border=0)
            elif but["action"][0] == dim and but["action"][1] == self.getVizGridNbDim(dim)+1:
                bb = self.buttons.pop(bi)
                self.getSW().GetSizer().Detach(bb["button"])
                bb["button"].Destroy()

    def addVizExts(self):
        sizeb = (self.getVizBbsiz(), 1)
        for which in [0, 1]:
            posb = [0,0]
            for i in range(1, self.getVizGridNbDim(which)+1):
                bid = wx.NewId()
                but = wx.Button(self.getSW(), bid, "", style=wx.NO_BORDER, size=(sizeb[which], sizeb[1-which]))
                but.SetBackgroundColour(self.color_drop)
                posb[which] = i
                self.getSW().GetSizer().Add(but, pos=tuple(posb), flag=wx.EXPAND|wx.ALIGN_CENTER, border=0)
                self.buttons[bid] = {"action": (which, i), "button": but}
                but.Bind(wx.EVT_BUTTON, self.OnChangeGridViz)
                ## but.Bind(wx.EVT_ENTER_WINDOW, self.OnPrintName)

            bid = wx.NewId()
            but = wx.Button(self.getSW(), bid, "", style=wx.NO_BORDER, size=(sizeb[1-which], sizeb[which]))
            but.SetBackgroundColour(self.color_add)
            ppos, pspan = ([1, 1], [1, 1])
            ppos[which] += self.getVizGridNbDim(which)
            pspan[1-which] = self.getVizGridNbDim(1-which)
            self.getSW().GetSizer().Add(but, pos=ppos, span=pspan, flag=wx.EXPAND|wx.ALIGN_CENTER, border=0)
            self.buttons[bid] = {"action": (which, -1), "button": but}
            but.Bind(wx.EVT_BUTTON, self.OnChangeGridViz)
            ## but.Bind(wx.EVT_ENTER_WINDOW, self.OnPrintName)

    def setVizButtAble(self):
        for bi, bb in self.buttons.items():
            if bb["action"][1] == 1 and self.getVizGridNbDim(bb["action"][0]) == 1:
                bb["button"].Disable()
            else:
                bb["button"].Enable()

    # def OnPrintName(self, event=None):
    #     if event.GetId() in self.buttons:
    #         print "button", self.buttons[event.GetId()]["action"]
    #     else:
    #         print "button", event.GetId(), "not there"
    #     event.Skip()

    def OnChangeGridViz(self, event=None):
        if self.buttons[event.GetId()]["action"][1] == -1:
            self.incrementVizGridDim(self.buttons[event.GetId()]["action"][0])
        else:
            self.decrementVizGridDim(self.buttons[event.GetId()]["action"][0],
                                     self.buttons[event.GetId()]["action"][1])
    def setActiveViz(self, fid=None):
        for k,v in self.vfiller_ids.items():
            if k == fid:
                self.setVizcellSelected(fid)
                v.setActive()
            else:
                v.setUnactive()

    def resizeViz(self):
        if self.isReadyVizIntab():
            for (vid, view) in self.parent.viewsm.iterateViews():
                if view.isIntab():
                    view._SetSize()
            for (vid, view) in self.vfiller_ids.items():
                view._SetSize()

    def hideShowBxViz(self):
        if self.isReadyVizIntab():
            for (vid, view) in self.parent.viewsm.iterateViews():
                if view.isIntab():
                    view.hideShowOpt()
                    # view._SetSize()
            # for (vid, view) in self.vfiller_ids.items():
            #     view._SetSize()


    def setVizcellFreeded(self, pos):
        self.vused_ids.pop(pos)
        self.vfiller_ids[pos] = Filler(self.parent, pos)
        self.updateVizcellSelected()

    def isVizSplit(self):
        return self.parent.hasSplit() and self.parent.splitter.IsSplit()
    
    def vizTabToSplit(self):
        if not self.parent.hasSplit():
            return
        self.parent.tabbed.RemovePage(self.viz_postab)
        # print "Pop viz tab key"
        self.parent.tabs_keys.pop(self.viz_postab)
        self.getSW().Reparent(self.parent.splitter)
        self.parent.splitter.SplitHorizontally(self.parent.tabbed, self.getSW())

    def vizSplitToTab(self):
        if not self.parent.hasSplit():
            return
        if self.isVizSplit():
            self.parent.splitter.Unsplit(self.getSW())
        self.getSW().Reparent(self.parent.tabbed)
        self.parent.tabbed.InsertPage(self.viz_postab, self.getSW(), self.getTitle())
        if self.parent.sysTLin():
            self.getSW().Show()
        # print "Insert viz tab key"
        self.parent.tabs_keys.insert(self.viz_postab, "viz")
        

    def OnSplitchange(self):
        if not self.parent.hasSplit():
            return

        if self.hasVizIntab():
            if self.viz_postab < len(self.parent.tabs_keys) and self.parent.tabs_keys[self.viz_postab] == "viz":
                self.vizTabToSplit()
                self.parent.buttViz.SetBitmap(self.getIcon("unsplit_frame"))
                # self.parent.buttViz.SetValue(False)
                # self.parent.buttViz.SetLabel("u")
                # self.parent.buttViz.SetForegroundColour((255, 255, 255))
                # self.parent.buttViz.SetBackgroundColour((0, 0, 0))
            else:
                self.vizSplitToTab()
                self.parent.buttViz.SetBitmap(self.getIcon("split_frame"))
                # self.parent.buttViz.SetValue(False)
                # self.parent.buttViz.SetLabel("s")
                # self.parent.buttViz.SetForegroundColour((0,0,0))
                # self.parent.buttViz.SetBackgroundColour((255, 255, 255))

            self.hideShowBxViz()
            self.parent.doUpdates({"menu":True})
