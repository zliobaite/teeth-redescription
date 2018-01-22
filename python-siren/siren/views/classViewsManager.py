import wx
import numpy
from factView import ViewFactory

import pdb

######################################################################
###########     VIEWS MANAGER
######################################################################

class ViewsManager:

    def __init__(self, parent):
        self.parent = parent
        self.view_map = {}
        self.vtoi = {}
        self.itov = {}
        ### Record highlight rows for reds views
        self.emphasized = {}
        ### MENU ids to opened views
        self.menu_opened_views = {}
        
        self.selectedViewX = -1

    def isGeospatial(self):
        if self.parent.dw is not None:
            return self.parent.dw.isGeospatial()
        return False

    def getViewsItems(self, typv="R", tab_type=None, what=None, vkey=None):
        excludeT = None
        if vkey in self.vtoi:
            typv = self.vtoi[vkey][1]
            excludeT = [vkey[0]]
        return ViewFactory.getViewsInfo(typv, tab_type, self.isGeospatial(), what, excludeT)

    def getDefaultViewT(self, typv="R", type_tab=None):
        return ViewFactory.getDefaultViewT(typv, self.isGeospatial(), type_tab)

    def getNbViews(self):
        return len(self.view_map)

    def getNbActiveViewsForMenu(self):
        return len([vkey for (vkey, view) in self.view_map.items() if not view.isIntab()])
    def getActiveViewsForMenu(self):
        return sorted([(vkey, view.getShortDesc()) for (vkey, view) in self.view_map.items() if not view.isIntab()], key=lambda x: x[1])

    def accessViewX(self, vkey):
        if vkey in self.view_map:
            return self.view_map[vkey]
    def iterateViews(self):
        return self.view_map.items()

    def getViewX(self, viewT, vid=None):
        if (viewT, vid) not in self.view_map:
            view = ViewFactory.getView(viewT, self.parent, wx.NewId())
            if view is None:
                return
            self.selectedViewX = view.getId()
            self.view_map[self.selectedViewX] = view
        else:
            self.selectedViewX = (viewT, vid)
        self.view_map[self.selectedViewX].toTop()
        return self.view_map[self.selectedViewX]

    def deleteView(self, vkey, freeing=True):
        if vkey in self.view_map:
            self.parent.plant.getWP().layOff(self.parent.plant.getWP().findWid([("wtyp", "project"), ("vid", vkey)]))
            if not self.view_map[vkey].isIntab():
                self.view_map[vkey].mapFrame.Destroy()
            else:
                pos = self.view_map[vkey].getGPos()
                panel = self.view_map[vkey].popSizer()
                panel.Destroy()
                if freeing:
                    self.parent.vizm.setVizcellFreeded(pos)
            del self.view_map[vkey]

    def deleteAllViews(self):
        self.selectedViewX = -1
        vkeys = self.view_map.keys()
        for vkey in vkeys:
            self.view_map[vkey].OnQuit(None, upMenu=False)
        self.view_map = {}
        self.parent.updateMenus()

    def viewOther(self, viewT, vkey):
        if vkey in self.vtoi:
            (tabId, typ, iid) = self.vtoi[vkey]
            if tabId in self.parent.tabs and self.parent.matchTabType("r", self.parent.tabs[tabId]):
                if typ == "R":
                    what = self.parent.tabs[tabId]["tab"].getItemForIid(iid)
                elif typ == "L":
                    what = None
                self.viewData(viewT, what, iid, tabId)

    def viewData(self, viewT, what, iid=None, tabId=None):
        if tabId is None:
            tabId = self.parent.getDefaultTabId("r")
        # if what is None:
        #     if tabId in self.parent.tabs and self.parent.matchTabType("r", self.parent.tabs[tabId]):
        #         what = self.parent.tabs[tabId]["tab"].getItemForIid(rid)
        # if what is None and lid is not None:
        #     if tabId in self.parent.tabs and self.parent.matchTabType("r", self.parent.tabs[tabId]):
        #         what = self.parent.tabs[tabId]["tab"].getItemsMapForLid(iid)
            
        vid = None
        ## if iid == -1 and
        if type(what) == list:
            iid = -numpy.sum([2**k for (k,v) in what])
        ikey = (tabId, ViewFactory.getTypV(viewT), iid)
        if ikey in self.itov and viewT in self.itov[ikey]:
            vid = self.itov[ikey][viewT]
            
        mapV = self.getViewX(viewT, vid)
        if vid is None and mapV is not None:
            self.registerView(mapV.getId(), ikey, upMenu=False)
            mapV.setCurrent(what)
            mapV.updateTitle()
            mapV.lastStepInit()
            self.parent.updateMenus()
        return mapV
            
    def registerView(self, vkey, ikey, upMenu=True):
        ## print "Register", vkey, ikey
        self.vtoi[vkey] = ikey
        if ikey not in self.itov:
            self.itov[ikey] = {}
        self.itov[ikey][vkey[0]] = vkey[1]
        if upMenu:
            self.parent.updateMenus()

    def unregisterView(self, vkey, upMenu=True):
        if vkey in self.vtoi:
            ikey = self.vtoi[vkey]
            del self.vtoi[vkey]
            del self.itov[ikey][vkey[0]]

            ### if there are no other view referring to same red, clear emphasize lines
            if len(self.itov[ikey]) == 0:
                del self.itov[ikey]
                if ikey in self.emphasized:
                    del self.emphasized[ikey]

            if upMenu:
                self.parent.updateMenus()

    def OnViewTop(self, event):
        self.viewToTop(event.GetId())

    def viewToTop(self, vid):
        if vid in self.menu_opened_views and \
               self.menu_opened_views[vid] in self.view_map:
            self.view_map[self.menu_opened_views[vid]].toTop()

    def OnCloseViews(self, event):
        self.closeViews()
        self.parent.toTop()

    def closeViews(self):
        vkeys = self.view_map.keys()
        for vkey in vkeys:
            if self.view_map[vkey].isIntab():
                self.view_map[vkey].OnQuit()

    def makeViewsMenu(self, frame, menuViews):
        self.menu_opened_views = {}

        for vid, desc in self.getActiveViewsForMenu():
            ID_VIEW = wx.NewId()
            self.menu_opened_views[ID_VIEW] = vid 
            m_view = menuViews.Append(ID_VIEW, "%s" % desc, "Bring view %s on top." % desc)
            frame.Bind(wx.EVT_MENU, self.OnViewTop, m_view)

        if self.getNbActiveViewsForMenu() == 0:
            ID_NOP = wx.NewId()
            menuViews.Append(ID_NOP, "No view opened", "There is no view currently opened.")
            menuViews.Enable(ID_NOP, False)
        else:
            menuViews.AppendSeparator()
            ID_VIEW = wx.NewId()
            m_view = menuViews.Append(ID_VIEW, "Close all views", "Close all views.")
            frame.Bind(wx.EVT_MENU, self.OnCloseViews, m_view)
        return menuViews

    def makeMenusForViews(self):
        for vid, view in self.view_map.items():
            view.makeMenu()
                        
    def newRedVHist(self, queries, viewT, listsHdl=None):
        mapV = self.getViewX(viewT, None)
        red = mapV.setCurrent(queries)
        if listsHdl is None:
            listsHdl = self.parent.getDefaultTab("r")
        iid = -1
        if listsHdl is not None:
            iid = listsHdl.insertItem('hist', red)

            ikey = (listsHdl.tabId, ViewFactory.getTypV(viewT), iid)
            self.registerView(mapV.getId(), ikey, upMenu=False)
            self.parent.updateMenus()
            mapV.updateTitle()
            mapV.lastStepInit()

    def recomputeAll(self):
        for vkey, view in self.view_map.items():
            view.refresh()

    def getItemId(self, vkey):
        if vkey in self.vtoi:
            return "%s%d" % (self.vtoi[vkey][1], self.vtoi[vkey][2])
        return "?"
    def getItemViewCount(self, vkey):
        if vkey in self.vtoi:
            return len(self.itov[self.vtoi[vkey]])
        return 0
    def dispatchEdit(self, red, vkey=None, ikey=None):
        if ikey is None and vkey in self.vtoi:
            ikey = self.vtoi[vkey]
            
        if vkey != -1 and ikey[0] in self.parent.tabs:
            self.parent.tabs[ikey[0]]["tab"].applyEditToData(ikey[-1], red)

        for (vt, vid) in self.itov.get(ikey, {}).items():
            if (vt, vid) != vkey:
                mm = self.accessViewX((vt, vid))
                mm.setCurrent(red)

    def doFlipEmphasizedR(self, vkey):
        if vkey in self.vtoi and self.vtoi[vkey] in self.emphasized:
            self.parent.flipRowsEnabled(self.emphasized[self.vtoi[vkey]])
            self.setEmphasizedR(vkey, self.emphasized[self.vtoi[vkey]])

    def getEmphasizedR(self, vkey):
        if vkey in self.vtoi and self.vtoi[vkey] in self.emphasized:
            return self.emphasized[self.vtoi[vkey]]
        return set()

    def setAllEmphasizedR(self, lids=None, show_info=False, no_off=False):
        for vkey in self.vtoi:
            self.setEmphasizedR(vkey, lids, show_info, no_off)

    def setEmphasizedR(self, vkey, lids=None, show_info=False, no_off=False):
        if vkey in self.vtoi:
            toed = self.vtoi[vkey]
            if toed not in self.emphasized:
                self.emphasized[toed] = set()
            if lids is None:
                turn_off = self.emphasized[toed]
                turn_on =  set()
                self.emphasized[toed] = set()
            else:
                turn_on =  set(lids) - self.emphasized[toed]
                if no_off:
                    turn_off = set()
                    self.emphasized[toed].update(turn_on)
                else:
                    turn_off = set(lids) & self.emphasized[toed]
                    self.emphasized[toed].symmetric_difference_update(lids)

            for (vt, vid) in self.itov[toed].items():
                mm = self.accessViewX((vt, vid))
                mm.emphasizeOnOff(turn_on=turn_on, turn_off=turn_off)
            
            if len(turn_on) == 1 and show_info:
                if toed[0] in self.parent.tabs:
                    red = self.parent.tabs[toed[0]]["tab"].getItemForIid(toed[1])
                    for lid in turn_on:
                        self.parent.showDetailsBox(lid, red)

