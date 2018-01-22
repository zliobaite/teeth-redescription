import wx
import numpy
# The recommended way to use wx with mpl is with the WXAgg backend. 
import matplotlib
matplotlib.use('WXAgg')

import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas, \
    NavigationToolbar2WxAgg as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.patches import Ellipse
 
from ..reremi.classSParts import SSetts
from ..reremi.classRedescription import Redescription
from classInterObjects import MaskCreator

import pdb

def HTMLColorToRGB(colorstring):
    """ convert #RRGGBB to an (R, G, B) tuple """
    colorstring = colorstring.strip()
    if colorstring[0] == '#': colorstring = colorstring[1:]
    if len(colorstring) != 6:
        raise ValueError, "input #%s is not in #RRGGBB format" % colorstring
    r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:]
    r, g, b = [int(n, 16) for n in (r, g, b)]
    return (r, g, b)

############ MODAL WINDOW TRICKS
# class MyModalDialogHook(wx.ModalDialogHook):

#     def __init__(self, parent):

#         wx.ModalDialogHook.__init__(self, parent)


#     def Enter(self, dialog):

#         # Just for demonstration purposes, intercept all uses of
#         # wx.FileDialog. Notice that self doesn't provide any real
#         # sandboxing, of course, the program can still read and write
#         # files by not using wx.FileDialog to ask the user for their
#         # names.
#         if isinstance(dialog, wx.MessageDialog):

#             wx.LogError("Access to file system disallowed.")

#             # Skip showing the file dialog entirely.
#             return wx.ID_CANCEL


#         self.lastEnter = wx.DateTime.Now()

#         # Allow the dialog to be shown as usual.
#         return wx.ID_NONE


#     def Exit(self, dialog):

#         # Again, just for demonstration purposes, show how long did
#         # the user take to dismiss the dialog. Notice that we
#         # shouldn't use wx.LogMessage() here as self would result in
#         # another modal dialog call and hence infinite recursion. In
#         # general, the hooks should be as unintrusive as possible.
#         wx.LogDebug("%s dialog took %s to be dismissed",
#                    dialog.GetClassInfo().GetClassName(),
#                    (wx.DateTime.Now() - self.lastEnter).Format())
####################

class CustToolbar(NavigationToolbar):
    """ 
    Customized Toolbar for action on the plot including saving, attaching to main window, etc.
    Sets the different mouse cursors depending on context. 
    """
    
    def __init__(self, plotCanvas, parent):
        self.toolitems = (('Home', 'Reset original view', 'home', 'home'), ('Back', 'Back to  previous view', 'back', 'back'), ('Forward', 'Forward to next view', 'forward', 'forward'), (None, None, None, None), ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'), ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'))
        # , (None, None, None, None), ('Subplots', 'Configure subplots', 'subplots', 'configure_subplots'), ('Save', 'Save the figure', 'filesave', 'save_figure')
        if not parent.hasParent():
            self.toolitems = tuple(list(self.toolitems) +[('Save', 'Save the figure', 'filesave', 'save_figure')])
        NavigationToolbar.__init__(self, plotCanvas)
        self.parent = parent

        # self.toolitems = (('Home', 'Reset original view', 'home', 'home'), ('Back', 'Back to  previous view', 'back', 'back'), ('Forward', 'Forward to next view', 'forward', 'forward'), (None, None, None, None), ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'), ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'), (None, None, None, None), ('Subplots', 'Configure subplots', 'subplots', 'configure_subplots'), ('Save', 'Save the figure', 'filesave', 'save_figure'))

    def set_history_buttons(self):
        pass

    def mouse_move(self, event=None):
        if event is not None:
            NavigationToolbar.mouse_move(self, event)
        if self.parent.q_active_poly():
            self.set_cursor(2)
        elif self.parent.q_active_info():
            self.set_cursor(0)
        else:
            self.set_cursor(1)


class BasisView(object):
    """
    The parent class of all visualizations.
    """

    colors_ord = ["color_l", "color_r", "color_i", "color_o"]
    colors_def = {"color_l": (255,0,0), "color_r": (0,0,255), "color_i": (160,32,240), "color_o": (153, 153, 153),
                  "grey_basic": (127,127,127), "grey_light": (153,153,153), "grey_dark": (85,85,85),
                  "color_h": (255, 255, 0), -1: (127, 127, 127)}
    DOT_ALPHA = 0.6
    ## 153 -> 99, 237 -> ed
    DOT_SHAPE = 's'
    DOT_SIZE = 3

    DELTA_ON = False
    DEF_ZORD = 3
    
    TID = "-"
    SDESC = "-"
    ordN = 0
    title_str = "Basis View"
    geo = False
    typesI = ""

    nb_cols = 4
    spacer_w = 15
    spacer_h = 10
    nbadd_boxes = 0 
    butt_w = 90
    sld_w = 115
    butt_shape = (27, 27)
    fwidth = {"i": 400, "t": 400, "s": 250}
    fheight = {"i": 400, "t": 300, "s": 200}

    ann_xy = (-10, 15)
    
    def getSpacerW(self):
        return self.spacer_w
    def getSpacerWn(self):
        return self.spacer_w/4.
    def getSpacerH(self):
        return self.spacer_h
    def getVizType(self):
        if self.isIntab():
            if self.parent.getVizm().isVizSplit():
                return "s"
            return "t"
        return "i"
    def getFWidth(self):
        return self.fwidth[self.getVizType()]    
    def getFHeight(self):
        return self.fheight[self.getVizType()]
    def getGPos(self):
        return self.pos
    def resetGPos(self, npos):
        self.mapFrame.GetSizer().Detach(self.panel)
        self.pos = npos
        self.mapFrame.GetSizer().Add(self.panel, pos=self.getGPos(), flag=wx.EXPAND|wx.ALIGN_CENTER, border=0)

    ltids_map = {1: "binary", 2: "spectral", 3: "viridis"}
    def getCMap(self, ltid):
        return plt.get_cmap(self.ltids_map.get(ltid, "jet"))
        
    @classmethod
    def getViewsDetails(tcl):
        if tcl.TID is not None:
            return {tcl.TID: {"title": tcl.title_str, "class": tcl, "more": None, "ord": tcl.ordN}}
        return {}
    
    @classmethod
    def suitableView(tcl, geo=False, what=None, tabT=None):
        return (tabT is None or tabT in tcl.typesI) and (not tcl.geo or geo)

    def hasParent(self):
        return self.parent is not None
    def GetRoundBitmap(self, w, h, r=10):
        maskColour = wx.Colour(0,0,0)
        shownColour = wx.Colour(5,5,5)
        b = wx.EmptyBitmap(w,h)
        dc = wx.MemoryDC(b)
        dc.SetBrush(wx.Brush(maskColour))
        dc.DrawRectangle(0,0,w,h)
        dc.SetBrush(wx.Brush(shownColour))
        dc.SetPen(wx.Pen(shownColour))
        dc.DrawCircle(w/2,h/2,w/2)
        dc.SelectObject(wx.NullBitmap)
        b.SetMaskColour(maskColour)
        return b
    def getIcon(self, key):
        if self.hasParent() and key in self.parent.icons:
            return self.parent.icons[key]
        return wx.NullBitmap
    
    def __init__(self, parent, vid, more=None):
        self.initVars(parent, vid, more)
        self.initView()

    def initVars(self, parent, vid, more=None):
        self.active_info = False
        self.parent = parent
        self.mc = None
        self.pos = None
        self.sld_sel = None
        self.savef = None
        self.boxL = None
        self.boxT = None
        self.rsets = None
        self.rwhich = None
        self.vid = vid
        self.buttons = []
        self.act_butt = [1]

        self.initHighlighted()
        self.intab = (self.hasParent() and self.parent.getVizm().showVizIntab())
        self.store_size = None

    def initView(self):
        if self.hasParent() and self.isIntab():
            self.mapFrame = self.parent.tabs["viz"]["tab"]
            # self.panel = self.parent.tabs["viz"]["tab"]
        else:
            self.mapFrame = self.initExtFrame()
        self.panel = wx.Panel(self.mapFrame, -1, style=wx.RAISED_BORDER)
        self.drawFrame()
        self.doBinds()
        self.prepareActions()
        self.setKeys()
        self.prepareProcesses()
        self.makeMenu()
        self.initSizeRelative()
        if not self.isIntab():
            self.mapFrame.Show()
        
    ############ MODAL WINDOW TRICKS         
    #     self.mapFrame.MakeModal()
    #     # self.myHook = MyModalDialogHook(None)
    #     # self.myHook.Register()
            
    #     TIMER_ID = wx.NewId()
    #     self.timer = wx.Timer(self.panel, TIMER_ID)
    #     wx.EVT_TIMER(self.panel, TIMER_ID, self.onTimer)
    #     self.timer.Start(5000)
 
    #     # self.dlg = wx.MessageDialog(self.mapFrame, 'Picture will be shown', 'Info', wx.OK | wx.ICON_INFORMATION)
    #     # # ## self.dlg.SetReturnCode(1)
    #     # # print "-- (0) --"
    #     # self.dlg.MakeModal(True)
    #     # self.dlg.ShowModal()
    #     # # print "-- (1) --"
    #     # self.dlg.Destroy()


    # def onTimer(self, event):
    #     self.timer.Stop()
    #     print "in onTimer"
    #     self.mapFrame.MakeModal(False)
    #     # print self.dlg, self.dlg.IsModal()
    #     # # if self.dlg.IsModal():
    #     #self.dlg.MakeModal(False)
    #     # self.dlg.EndModal(0)
    #     # self.dlg.Destroy()
    ################

    def getCanvasConnections(self):
        return []
            
    def lastStepInit(self):
        pass

    def isIntab(self):
        return self.intab

    def hideShowOptRec(self, box, where):
        if isinstance(box, wx.SizerItem) and box.IsSizer():
            box = box.GetSizer()
        if isinstance(box, wx.Sizer) or box.IsSizer():
            for child in box.GetChildren():
                self.hideShowOptRec(child, where)
        else:
            ww = (box.GetUserData() or {"where": "i"}).get("where")
            if where in ww or ww == "*":
                box.Show(True)
            else:
                box.Show(False)

    def hideShowOpt(self):
        self.hideShowOptRec(self.innerBox1, self.getVizType())
        self.autoShowSplitsBoxes()

    def getActionsDetails(self):
        details = []
        for action, dtl in self.actions_map.items():
            details.append({"label": "%s[%s]" % (dtl["label"].ljust(30), dtl["key"]),
                            "legend": dtl["legend"], "active": dtl["active_q"](),
                            "key": dtl["key"], "order": dtl["order"], "type": dtl["type"]})
        if self.mc is not None:
            details.extend(self.mc.getActionsDetails(6))
        return details

    def q_expand(self, more):
        if more is None:
            return True
        res = True
        if "side" in more:
            res &= len(self.queries[1-more["side"]]) > 0
        if "in_weight" in more or "out_weight" in more:
            res &= self.q_has_selected()
        return res
            
    def q_has_poly(self):
        return self.mc is not None and self.mc.q_has_poly()

    def q_active_poly(self):
        return self.mc is not None and self.mc.isActive()

    def q_active_info(self):
        return self.active_info

    def q_not_svar(self):
        return not self.isSingleVar()
    def q_has_selected(self):
        return len(self.getHighlightedIds()) > 0

    def q_true(self):
        return True

    def getWeightCover(self, params):
        params["area"] = self.getHighlightedIds()
        return params

    def prepareProcesses(self):
        self.processes_map = {}
    def prepareActions(self):
        self.actions_map = {}

    def setKeys(self, keys=None):
        self.keys_map = {}
        if keys is None:
            for action, details in self.actions_map.items():
                details["key"] = action[0]
                self.keys_map[details["key"]] = action
        else:
            for action, details in self.actions_map.items():
                details["key"] = None
            for key, action in keys.items():
                if action in self.actions_map:
                    self.actions_map[action]["key"] = key
                    self.keys_map[key] = action
                    
    def getItemId(self):
        if self.hasParent():
            return self.parent.viewsm.getItemId(self.getId())
        return self.vid
    
    def getShortDesc(self):
        return "%s %s" % (self.getItemId(), self.SDESC)

    def getTitleDesc(self):
        return "%s %s" % (self.getItemId(), self.title_str)

    def updateTitle(self):
        if self.hasParent() and not self.isIntab():
            self.mapFrame.SetTitle("%s%s" % (self.parent.titlePref, self.getTitleDesc()))
        self.info_title.SetLabel(self.getTitleDesc())

    def getId(self):
        return (self.TID, self.vid)

    def getVId(self):
        return self.vid

    def toTop(self):
        self.mapFrame.Raise()
        try:
            self.MapfigMap.canvas.SetFocus()
        except AttributeError:
            self.mapFrame.SetFocus()

    def getDetailsSplit(self):
        return self.rsets

    def getVizRows(self):
        if self.getParentData() is not None:
            return self.getParentData().getVizRows(self.getDetailsSplit()) 
        return set()
    def getUnvizRows(self):
        if self.getParentData() is not None:
            return self.getParentData().getUnvizRows(self.getDetailsSplit())
        return set()
    def makeMenu(self, frame=None):
        """
        Prepare the menu for this view.

        @type  frame: wx.Frame
        @param frame: The frame in which the menu resides
        """
        
        if self.isIntab():
            return
        
        if frame is None:
            frame = self.mapFrame
        self.menu_map_act = {}
        self.ids_viewT = {}
        self.menu_map_pro = {}
        menuBar = wx.MenuBar()
        if self.hasParent():
            menuBar.Append(self.parent.makeFileMenu(frame), "&File")
        menuBar.Append(self.makeActionsMenu(frame), "&Edit")
        menuBar.Append(self.makeVizMenu(frame), "&View")
        menuBar.Append(self.makeProcessMenu(frame), "&Process")
        if self.hasParent():
            menuBar.Append(self.parent.makeViewsMenu(frame), "&Windows")
            menuBar.Append(self.parent.makeHelpMenu(frame), "&Help")
        frame.SetMenuBar(menuBar)
        frame.Layout()

    def enumerateVizItems(self):
        if self.hasParent():
            return self.parent.viewsm.getViewsItems(vkey=self.getId())
        return []
    def makeVizMenu(self, frame, menuViz=None):
        """
        Prepare the visualization sub-menu for this view.

        @type  frame: wx.Frame
        @param frame: The frame in which the menu resides
        @type  menuViz: wx.Menu
        @param menuViz: Existing menu, if any, where entries will be appended
        @rtype:   wx.Menu
        @return:  the sub-menu, menuViz extended
        """

        if menuViz is None:
            menuViz = wx.Menu()
        for item in self.enumerateVizItems():
            ID_NEWV = wx.NewId()
            m_newv = menuViz.Append(ID_NEWV, "%s" % item["title"],
                                    "Plot %s." % item["title"])
            if not item["suitable"]:
                m_newv.Enable(False)

            frame.Bind(wx.EVT_MENU, self.OnOtherV, m_newv)
            self.ids_viewT[ID_NEWV] = item["viewT"]
        return menuViz

    def makeActionsMenu(self, frame, menuAct=None):
        if menuAct is None:
            menuAct = wx.Menu()
        for action in sorted(self.getActionsDetails(), key=lambda x:(x["order"],x["key"])):
            ID_ACT = wx.NewId()
            if action["type"] == "check":
                m_act = menuAct.AppendCheckItem(ID_ACT, action["label"], action["legend"])
                frame.Bind(wx.EVT_MENU, self.OnMenuAction, m_act)
                self.menu_map_act[ID_ACT] = action["key"]
                if action["active"]:
                    m_act.Check()
            else:
                m_act = menuAct.Append(ID_ACT, action["label"], action["legend"])
                if action["active"]:
                    if action["type"] == "mc":
                        frame.Bind(wx.EVT_MENU, self.OnMenuMCAction, m_act)
                    else:
                        frame.Bind(wx.EVT_MENU, self.OnMenuAction, m_act)
                    self.menu_map_act[ID_ACT] = action["key"]
                else:
                    menuAct.Enable(ID_ACT, False)
        return menuAct

    def makeProcessMenu(self, frame, menuPro=None):
        if menuPro is None:
            menuPro = wx.Menu()

        for process, details in sorted(self.processes_map.items(), key=lambda x: (x[1]["order"], x[1]["label"])):
            ID_PRO = wx.NewId()
            m_pro = menuPro.Append(ID_PRO, details["label"], details["legend"])
            if self.q_expand(details["more"]):
                frame.Bind(wx.EVT_MENU, self.OnExpandAdv, m_pro)
                self.menu_map_pro[ID_PRO] = process
            else:
                menuPro.Enable(ID_PRO, False)
        ct = menuPro.GetMenuItemCount()
        if self.hasParent():
            menuPro = self.parent.makeStoppersMenu(frame, menuPro)
        if ct < menuPro.GetMenuItemCount():
            menuPro.InsertSeparator(ct)
        return menuPro

    def do_toggle_info(self, event):
        self.active_info = not self.active_info

    def do_toggle_poly(self, event):
        self.togglePoly()

    def togglePoly(self):
        if self.mc is not None:
             if self.mc.isActive():
                 self.mc.setButtons([])
                 self.act_butt = [1]
             else:
                 self.mc.setButtons([1])
                 self.act_butt = []
             self.makeMenu()
             self.MaptoolbarMap.mouse_move()
        
    def OnMenuAction(self, event):
        if event.GetId() in self.menu_map_act:
            self.doActionForKey(self.menu_map_act[event.GetId()])

    def OnMenuMCAction(self, event):
        if self.mc is not None and event.GetId() in self.menu_map_act:
            self.mc.doActionForKey(self.menu_map_act[event.GetId()])

    def OnOtherV(self, event):
        if self.hasParent():
            self.parent.viewsm.viewOther(viewT=self.ids_viewT[event.GetId()], vkey=self.getId())

    def showSplitsBoxes(self, show=True):
        self.boxL.Show(show)
        self.boxT.Show(show)

    def autoShowSplitsBoxes(self):
        if self.getParentData() is not None and self.getParentData().hasLT():
            self.showSplitsBoxes(True)
        else:
            self.showSplitsBoxes(False)
        
    def OnSplitsChange(self, event):
        new_rsets = None
        parts = [{"butt": self.boxL, "id": "learn",
                  "act_icon": self.getIcon("learn_act"), "dis_icon": self.getIcon("learn_dis")},
                 {"butt": self.boxT, "id": "test",
                  "act_icon": self.getIcon("test_act"), "dis_icon": self.getIcon("test_dis")}]
        if event.GetId() == parts[0]["butt"].GetId():
            which = 0
        else:
            which = 1
        if self.rwhich is None: ### None active
            self.rwhich = which
            new_rsets = {"rset_id": parts[which]["id"]}
            parts[which]["butt"].SetBitmap(parts[which]["act_icon"])
            
        elif self.rwhich == which:  ### Current active
            self.rwhich = None
            new_rsets =None
            parts[which]["butt"].SetBitmap(parts[which]["dis_icon"])
            
        else:  ### Other active
            self.rwhich = which
            new_rsets = {"rset_id": parts[which]["id"]}
            parts[which]["butt"].SetBitmap(parts[which]["act_icon"])
            parts[1-which]["butt"].SetBitmap(parts[1-which]["dis_icon"])

        if self.rsets != new_rsets:
            self.rsets = new_rsets
            self.refresh()

        
    def additionalElements(self):
        return []

    def additionalBinds(self):
        for button in self.buttons:
            button["element"].Bind(wx.EVT_BUTTON, button["function"])

    def bindsToFrame(self):
        if not self.isIntab():
            self.mapFrame.Bind(wx.EVT_CLOSE, self.OnQuit)
            self.mapFrame.Bind(wx.EVT_SIZE, self._onSize)

    def bindsOther(self):
        self.savef.Bind(wx.EVT_LEFT_UP, self.OnSaveFig)
        self.boxL.Bind(wx.EVT_LEFT_UP, self.OnSplitsChange)
        self.boxT.Bind(wx.EVT_LEFT_UP, self.OnSplitsChange)
        self.boxPop.Bind(wx.EVT_LEFT_UP, self.OnPop)
        self.boxKil.Bind(wx.EVT_LEFT_UP, self.OnKil)

        # self.boxL.Bind(wx.EVT_TOGGLEBUTTON, self.OnSplitsChange)
        # self.boxT.Bind(wx.EVT_TOGGLEBUTTON, self.OnSplitsChange)
        # self.boxPop.Bind(wx.EVT_TOGGLEBUTTON, self.OnPop)
        # self.boxKil.Bind(wx.EVT_TOGGLEBUTTON, self.OnKil)

        # self.panel.Bind(wx.EVT_ENTER_WINDOW, self.onMouseOver)
        # self.panel.Bind(wx.EVT_LEAVE_WINDOW, self.onMouseLeave)


    def doBinds(self):
        self.bindsToFrame()
        self.bindsOther()

        self.additionalBinds()
        self.autoShowSplitsBoxes()


    # def onMouseOver(self, event):
    #     print "Entering", self.vid, self.panel.GetBackgroundColour()
    #     for elem in [self.panel, self.MapcanvasMap, self.MaptoolbarMap]:
    #         elem.SetBackgroundColour((230, 230, 230))
    #         elem.Refresh()

    # def onMouseLeave(self, event):
    #     print "Exiting", self.vid, self.panel.GetBackgroundColour()
    #     for elem in [self.panel, self.MapcanvasMap, self.MaptoolbarMap]:
    #         elem.SetBackgroundColour((249, 249, 248))
    #         elem.Refresh()

    def getParentCoords(self):
        if not self.hasParent():
            return [[[0]],[[0]]]
        return self.parent.dw.getCoords()
    def getParentCoordsExtrema(self):
        if not self.hasParent():
            return (-1., 1., -1., 1.)
        return self.parent.dw.getCoordsExtrema()
    def getParentData(self):
        if not self.hasParent():
            return None
        return self.parent.dw.getData()
        
    def getQueries(self):
        ### the actual queries, not copies, to test, etc. not for modifications
        return self.queries

    def getCopyRed(self):
        return Redescription.fromQueriesPair([self.queries[0].copy(), self.queries[1].copy()], self.getParentData())
        
    def OnExpandAdv(self, event):
        params = {"red": self.getCopyRed()}
        if event.GetId() in self.menu_map_pro:
            more = self.processes_map[self.menu_map_pro[event.GetId()]]["more"]
            if more is not None:
                params.update(more)
            for k in self.processes_map[self.menu_map_pro[event.GetId()]]["more_dyn"]:
                params = k(params)
        self.parent.expandFV(params)

    def OnExpandSimp(self, event):
        params = {"red": self.getCopyRed()}
        self.parent.expandFV(params)

    def initSizeRelative(self):
        ds = wx.DisplaySize()
        self.mapFrame.SetClientSizeWH(ds[0]/2.5, ds[1]/1.5)
        # self.mapFrame.SetClientSizeWH(2*ds[0], 2*ds[1])
        # print "Init size", (ds[0]/2.5, ds[1]/1.5)
        # self._SetSize((ds[0]/2.5, ds[1]/1.5))

    def _onSize(self, event=None):
        self._SetSize()


    def setSizeSpec(self, figsize):
        pass

    def _SetSize(self, initSize=None): 
        if initSize is None:
            pixels = tuple(self.mapFrame.GetClientSize() )
        else:
            pixels = initSize
        ## print "Set Size", self.store_size, pixels
        if self.store_size == pixels:
            return
        self.store_size = pixels
        boxsize = self.innerBox1.GetMinSize()
        ## min_size = (self.getFWidth(), self.getFHeight())
        if self.isIntab():
            # sz = (laybox.GetCols(), laybox.GetRows())
            sz = self.parent.getVizm().getVizGridSize()
            ## min_size = (self.getFWidth(), self.getFHeight())
            ## max_size = ((pixels[0]-2*self.parent.getVizm().getVizBb())/float(sz[1]),
            ##             (pixels[1]-2*self.parent.getVizm().getVizBb())/float(sz[0]))
            pixels = (max(self.getFWidth(), (pixels[0]-2*self.parent.getVizm().getVizBb())/float(sz[1])),
                      max(self.getFHeight(), (pixels[1]-2*self.parent.getVizm().getVizBb())/float(sz[0])))
            ## print "Redraw", pixels, tuple(self.mapFrame.GetClientSize())
        else:
            pixels = (max(self.getFWidth(), pixels[0]),
                      max(self.getFHeight(), pixels[1]))  
            ## max_size = (-1, -1)
        self.panel.SetSize( pixels )
        figsize = (pixels[0], max(pixels[1]-boxsize[1], 10))
        # self.MapfigMap.set_size_inches( float( figsize[0] )/(self.MapfigMap.get_dpi()),
        #                                 float( figsize[1] )/(self.MapfigMap.get_dpi() ))
        self.MapcanvasMap.SetMinSize(figsize)
        # #self.fillBox.SetMinSize((figsize[0], figsize[1]))
        self.innerBox1.SetMinSize((1*figsize[0], -1)) #boxsize[1]))
        ## print "\tMapcanvasMap:", figsize, "\tinnerBox1:", (1*figsize[0], curr[1])
        self.setSizeSpec(figsize)
        self.mapFrame.GetSizer().Layout()
        self.MapfigMap.set_size_inches( float( figsize[0] )/(self.MapfigMap.get_dpi()),
                                        float( figsize[1] )/(self.MapfigMap.get_dpi() ))
        ### The line below is primarily for Windows, works fine without in Linux...
        self.panel.SetClientSizeWH(pixels[0], pixels[1])
        # print "Height\tmin=%.2f\tmax=%.2f\tactual=%.2f\tfig=%.2f\tbox=%.2f" % ( min_size[1], max_size[1], pixels[1], figsize[1], boxsize[1])
        # self.MapfigMap.set_size_inches(1, 1)

    def OnSaveFig(self, event=None):
        self.MaptoolbarMap.save_figure(event)

    def initExtFrame(self):
        pref = "Standalone "
        if self.hasParent():
            pref = self.parent.titlePref
        mapFrame = wx.Frame(None, -1, "%s%s" % (pref, self.getTitleDesc()))
        mapFrame.SetMinSize((self.getFWidth(), self.getFHeight()))
        mapFrame.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        return mapFrame
        
    def OnPop(self, event=None):
        pos = self.getGPos()
        self.popSizer()
        if self.isIntab():
            self.intab = False
            self.mapFrame = self.initExtFrame()

            self.boxPop.SetBitmap(self.getIcon("outin"))
            # self.boxPop.SetLabel(self.label_outin)
            # self.boxPop.SetValue(False)
            self.parent.getVizm().setVizcellFreeded(pos)
            self.panel.Reparent(self.mapFrame)
            self.mapFrame.GetSizer().Add(self.panel)

        else:
            self.intab = True
            self.mapFrame.Destroy()
            self.mapFrame = self.parent.tabs["viz"]["tab"]
            
            self.boxPop.SetBitmap(self.getIcon("inout"))
            # self.boxPop.SetLabel(self.label_inout)
            # self.boxPop.SetValue(False)
            self.panel.Reparent(self.mapFrame)
            self.pos = self.parent.getVizm().getVizPlotPos(self.getId())
            self.mapFrame.GetSizer().Add(self.panel, pos=self.getGPos(), flag=wx.ALL, border=0)
            
        self.bindsToFrame()
        self.makeMenu()
        if not self.isIntab():
            self.mapFrame.Show()
        self.hideShowOpt()
        self._SetSize()
            
    def OnKil(self, event=None):
        self.OnQuit()

    def OnQuit(self, event=None, upMenu=True, freeing=True):
        if self.hasParent():
            self.parent.viewsm.deleteView(self.getId(), freeing)
            self.parent.viewsm.unregisterView(vkey=self.getId(), upMenu=upMenu)
        else:
            self.mapFrame.Destroy()
            
    def wasKilled(self):
        return self.MapcanvasMap is None
        
    def refresh(self):
        pass

    def setCurrent(self, data):
        pass
    def isSingleVar(self):
        return False
    def clearPlot(self):
        if not hasattr( self, 'MapfigMap' ): return
        axxs = self.MapfigMap.get_axes()
        for ax in axxs:
            ax.cla()
            if ax != self.axe:
                self.MapfigMap.delaxes(ax)
        self.clearHighlighted()

    def savefig(self, fname, **kwargs):
        self.MapfigMap.savefig(fname, **kwargs)

        
    def drawMap(self):
        """ Draws the map
        """

        if not hasattr( self, 'axe' ):
            self.axe = self.MapfigMap.add_subplot( 111 )

        self.prepareInteractive()

        ##self.plot_void()
        self.MapcanvasMap.draw()

    def prepareInteractive(self):
        self.el = Ellipse((2, -1), 0.5, 0.5)
            
        for act, meth in self.getCanvasConnections():
            if act == "MASK":
                self.mc = MaskCreator(self.axe, None, buttons_t=[], callback_change=self.makeMenu)
            else:
                self.MapfigMap.canvas.mpl_connect(act, meth)

        
    ##### FILL and WAIT PLOTTING
    def plot_void(self):
        if self.wasKilled():
            return
        self.clearPlot()
        self.axe.plot([r/10.0+0.3 for r in [0,2,4]], [0.5 for r in [0,2,4]], 's', markersize=10, mfc="#DDDDDD", mec="#DDDDDD")
        self.axe.axis([0,1,0,1])
        self.MapcanvasMap.draw()

    def init_wait(self):
        self.call_wait = wx.CallLater(1, self.plot_wait)
        self.cp = 0

    def kill_wait(self):
        self.call_wait.Stop()
        if self.wasKilled():
            return
        self.clearPlot()
        self.axe.plot([r/10.0+0.3 for r in [1,3]], [0.5, 0.5], 's', markersize=10, mfc="#DDDDDD", mec="#DDDDDD")
        self.axe.plot([r/10.0+0.3 for r in [0,2,4]], [0.5, 0.5, 0.5], 'ks', markersize=10)
        self.axe.axis([0,1,0,1])
        self.MapcanvasMap.draw()

    def plot_wait(self):
        if self.wasKilled():
            return
        self.clearPlot()
        self.axe.plot([r/10.0+0.3 for r in range(5)], [0.5 for r in range(5)], 'ks', markersize=10, mfc="#DDDDDD", mec="#DDDDDD")
        self.axe.plot(((self.cp)%5)/10.0+0.3, 0.5, 'ks', markersize=10)
        self.axe.axis([0,1,0,1])
        self.MapcanvasMap.draw()
        self.cp += 1
        self.call_wait.Restart(self.wait_delay)

        
        
    def drawFrameSpecific(self):
        pass

    def addFrameSpecific(self):
        pass

    def drawFrame(self):
        # initialize matplotlib stuff
        self.opt_hide = []
        self.MapfigMap = Figure(None) #, facecolor='white')
        self.MapcanvasMap = FigCanvas(self.panel, -1, self.MapfigMap)
        self.MaptoolbarMap = CustToolbar(self.MapcanvasMap, self)

        # styL = wx.ALIGN_RIGHT | wx.EXPAND
        # styV = wx.ALIGN_LEFT | wx.EXPAND
        # sizz = (70,-1)

        self.info_title = wx.StaticText(self.panel, label="? ?")
        self.drawFrameSpecific()

        adds = self.additionalElements()

        ### UTILITIES BUTTONS
        self.savef = wx.StaticBitmap(self.panel, wx.NewId(), self.getIcon("save"))
        self.boxL = wx.StaticBitmap(self.panel, wx.NewId(), self.getIcon("learn_dis"))
        self.boxT = wx.StaticBitmap(self.panel, wx.NewId(), self.getIcon("test_dis"))
        # self.boxL = wx.ToggleButton(self.panel, wx.NewId(), self.label_learn, style=wx.ALIGN_CENTER, size=self.butt_shape)
        # self.boxT = wx.ToggleButton(self.panel, wx.NewId(), self.label_test, style=wx.ALIGN_CENTER, size=self.butt_shape)

        if self.isIntab():
            # self.boxPop = wx.ToggleButton(self.panel, wx.NewId(), self.label_inout, style=wx.ALIGN_CENTER, size=self.butt_shape)
            self.boxPop = wx.StaticBitmap(self.panel, wx.NewId(), self.getIcon("inout"))
        else:
            # self.boxPop = wx.ToggleButton(self.panel, wx.NewId(), self.label_outin, style=wx.ALIGN_CENTER, size=self.butt_shape)
            self.boxPop = wx.StaticBitmap(self.panel, wx.NewId(), self.getIcon("outin"))
        # self.boxKil = wx.ToggleButton(self.panel, wx.NewId(), self.label_cross, style=wx.ALIGN_CENTER, size=self.butt_shape)
        self.boxKil = wx.StaticBitmap(self.panel, wx.NewId(), self.getIcon("kil"))
        if not self.hasParent() or not self.parent.getVizm().hasVizIntab():
            self.boxPop.Hide()
            self.boxKil.Hide()

        self.drawMap()

        ### PUTTING EVERYTHING IN SIZERS
        flags = wx.ALIGN_CENTER | wx.ALL # | wx.EXPAND
        add_boxB = wx.BoxSizer(wx.HORIZONTAL)
        add_boxB.AddSpacer((self.getSpacerWn()/2.,-1), userData={"where": "*"})
        
        add_boxB.Add(self.info_title, 0, border=1, flag=flags, userData={"where": "ts"})
        add_boxB.AddSpacer((2*self.getSpacerWn(),-1), userData={"where": "ts"})

        add_boxB.Add(self.MaptoolbarMap, 0, border=0, userData={"where": "*"})
        add_boxB.Add(self.boxL, 0, border=0, flag=flags, userData={"where": "*"})
        add_boxB.Add(self.boxT, 0, border=0, flag=flags, userData={"where": "*"})
        add_boxB.AddSpacer((2*self.getSpacerWn(),-1), userData={"where": "*"})

        add_boxB.Add(self.boxPop, 0, border=0, flag=flags, userData={"where": "*"})
        add_boxB.Add(self.boxKil, 0, border=0, flag=flags, userData={"where": "*"})
        add_boxB.AddSpacer((2*self.getSpacerWn(),-1))

        add_boxB.Add(self.savef, 0, border=0, flag=flags, userData={"where": "*"})
        add_boxB.AddSpacer((2*self.getSpacerWn(),-1))

        self.masterBox =  wx.FlexGridSizer(rows=2, cols=1, vgap=0, hgap=0)
        #self.masterBox = wx.BoxSizer(wx.VERTICAL)

        #self.fillBox = wx.BoxSizer(wx.HORIZONTAL)
        self.innerBox = wx.BoxSizer(wx.HORIZONTAL)
        self.innerBox1 = wx.BoxSizer(wx.VERTICAL)
        self.masterBox.Add(self.MapcanvasMap, 0, border=1,  flag= wx.EXPAND)
        #self.masterBox.Add(self.fillBox, 0, border=1,  flag= wx.EXPAND)

        self.addFrameSpecific()
        
        self.innerBox1.AddSpacer((-1,self.getSpacerH()), userData={"where": "it"})
        for add in adds:
            self.innerBox1.Add(add, 0, border=1,  flag= wx.ALIGN_CENTER)
        self.innerBox1.AddSpacer((-1,self.getSpacerH()/2), userData={"where": "it"})
        self.innerBox1.Add(add_boxB, 0, border=1,  flag= wx.ALIGN_CENTER)
        self.innerBox1.AddSpacer((-1,self.getSpacerH()/2), userData={"where": "*"})
            
        self.innerBox.Add(self.innerBox1, 0, border=1,  flag= wx.ALIGN_CENTER)
        self.masterBox.Add(self.innerBox, 0, border=1, flag= wx.EXPAND| wx.ALIGN_CENTER| wx.ALIGN_BOTTOM)
        self.panel.SetSizer(self.masterBox)
        if self.isIntab():
            self.pos = self.parent.getVizm().getVizPlotPos(self.getId())
            self.mapFrame.GetSizer().Add(self.panel, pos=self.pos, flag=wx.ALL, border=0)
        else:
            self.mapFrame.GetSizer().Add(self.panel)
            # self.panel.GetSizer().Fit(self.panel)
            # self.mapFrame.GetSizer().Add(self.masterBox, pos=pos, flag=wx.ALL, border=2)

        self.hideShowOpt()
        self._SetSize()


    def popSizer(self):
        if self.isIntab():
            self.pos = None
            self.mapFrame.GetSizer().Detach(self.panel)
            self.mapFrame.GetSizer().Layout()
        return self.panel

            
    def updateMap(self):
        """ Redraws the map
        """
        pass

    def sendEditBack(self, red = None):
        if red is not None:
            self.parent.viewsm.dispatchEdit(red, vkey=self.getId())

    def updateText(self, red = None):
        pass

    ################ HANDLING ACTIONS
    def doActionForKey(self, key):
        if self.keys_map.get(key, None in self.actions_map):
            act = self.actions_map[self.keys_map[key]]
            if act["type"] == "check" or act["active_q"]():
                self.actions_map[self.keys_map[key]]["method"](self.actions_map[self.keys_map[key]]["more"])
                return True
        return False

    def key_press_callback(self, event):
        self.doActionForKey(event.key)

    def mkey_press_callback(self, event):
        self.doActionForKey(chr(event.GetKeyCode()).lower())

    ################ HANDLING HIGHLIGHTS
    def updateEmphasize(self, review=True):
        if self.hasParent():
            lids = self.parent.viewsm.getEmphasizedR(vkey=self.getId())
            self.emphasizeOnOff(turn_on=lids, turn_off=None, review=review)

    def emphasizeOnOff(self, turn_on=set(), turn_off=set(), hover=False, review=True):
        self.emphasizeOff(turn_off, hover)
        self.emphasizeOn(turn_on, hover)
        if hover:
            self.MapcanvasMap.draw()
        else:
            self.makeMenu()
         
    def emphasizeOn(self, lids, hover=False):
        pass
    
    def emphasizeOff(self, lids=None, hover=False):
        self.removeHighlighted(lids, hover)

    def sendEmphasize(self, lids):
        return self.parent.viewsm.setEmphasizedR(vkey=self.getId(), lids=lids, show_info=self.q_active_info())

    def sendFlipEmphasizedR(self):
        return self.parent.viewsm.doFlipEmphasizedR(vkey=self.getId())
        
    ################ HANDLING HIGHLIGHTS
    def initHighlighted(self):
        self.highl = {}
        self.high_lbl = set()
        self.current_hover = {}
    def clearHighlighted(self):
        self.initHighlighted()
    def isHovered(self, iid):
        return iid in self.current_hover
    def isHighlighted(self, iid):
        return iid in self.highl
    def isHighLbl(self, iid):
        return iid in self.high_lbl
    def needingHighLbl(self, iids):
        if len(iids) <= self.max_emphlbl:
            return [iid for iid in iids if not self.isHighLbl(iid)]
        return []
    def needingHighlight(self, iids):
        return [iid for iid in iids if not self.isHighlighted(iid)]
    def getHighlightedIds(self):
        return self.highl.keys()
    def addHighlighted(self, hgs, hover=False):
        where = self.highl
        if hover:
            where = self.current_hover

        for iid, high in hgs.items():
            if iid not in where:
                where[iid] = []
            if type(high) is list:
                has_lbl = any([isinstance(t, Text) for t in high])
                where[iid].extend(high)
            else:
                has_lbl = isinstance(high, Text)
                where[iid].append(high)
            if has_lbl and not hover:
                self.high_lbl.add(iid)
                
    def removeHighlighted1(self, iid):
        if iid in self.highl:
            while len(self.highl[iid]) > 0:
                t = self.highl[iid].pop()
                t.remove()
            del self.highl[iid]
            self.high_lbl.discard(iid)
    def removeHover1(self, iid):
        if iid in self.current_hover:
            while len(self.current_hover[iid]) > 0:
                t = self.current_hover[iid].pop()
                t.remove()
            del self.current_hover[iid]
    def removeHighlighted(self, iid=None, hover=False):
        if iid is None:
            if hover:
                iids = self.current_hover.keys()
            else:
                iids = self.highl.keys()
        elif type(iid) is list or type(iid) is set:
            iids = iid
        else:
            iids = [iid]
        for iid in iids:
            if hover:
                self.removeHover1(iid)
            else:
                self.removeHighlighted1(iid)
                
    ################ HANDLING SETTINGS
    def getParentPreferences(self):
        if not self.hasParent():
            return {}
        return self.parent.dw.getPreferences()

    def getSettBoolV(self, key, default=False):
        t = self.getParentPreferences()
        try:
            v = t[key]["data"] == "yes"
        except:            
            v = default
        return v
    
    def hoverActive(self):
        return self.getSettBoolV('hover_entities')
    def clickActive(self):
        return self.getSettBoolV('click_entities')
    def inCapture(self, event):
        return False
    
    def getMissDetails(self):
        return self.getSettBoolV('miss_details')

    def getLitContribOn(self):
        return self.getSettBoolV('literals_contrib')
    
    def getDeltaOn(self):
        return self.getSettBoolV('draw_delta', self.DELTA_ON)

    
    def getColorKey1(self, key, dsetts=None):
        if dsetts is None:
            dsetts = self.getParentPreferences()
        if key in dsetts:
            tc = dsetts[key]["data"]
        elif key in self.colors_def:
            tc = self.colors_def[key]
        else:
            tc = self.colors_def[-1]
        return [i/255.0 for i in tc]+[1.]
    def getColorKey255(self, key, dsetts=None):
        if dsetts is None:
            dsetts = self.getParentPreferences()
        if key in dsetts:
            tc = dsetts[key]["data"]
        elif key in self.colors_def:
            tc = self.colors_def[key]
        else:
            tc = self.colors_def[-1]
        return tc
    
    def getColorA(self, color, alpha=None):
        if alpha is None:
            alpha = self.DOT_ALPHA
        elif alpha < -1 or alpha > 1:
            alpha = numpy.sign(alpha)*(numpy.abs(alpha)%1)*self.DOT_ALPHA
        if alpha < 0:
            return tuple([color[0],color[1], color[2], -color[3]*alpha])
        return tuple([color[0],color[1], color[2], alpha])
    
    def getColorHigh(self):
        return self.getColorA(self.getColorKey1("color_h"))

    def getColors255(self):
        return  [ self.getColorKey255(color_k) for color_k in self.colors_ord ]

    def getColors1(self):
        return  [ self.getColorKey1(color_k) for color_k in self.colors_ord ]
    
    def getDrawSettDef(self):
        t = self.getParentPreferences()
        try:
            dot_shape = t["dot_shape"]["data"]
            dot_size = t["dot_size"]["data"]
        except:
            dot_shape = self.DOT_SHAPE
            dot_size = self.DOT_SIZE

        return {"color_f": self.getColorA(self.getColorKey1("grey_basic")),
                "color_e": self.getColorA(self.getColorKey1("grey_basic"), 1.),
                "color_l": self.getColorA(self.getColorKey1("grey_light")),
                "shape": dot_shape, "size": dot_size, "zord": self.DEF_ZORD}

    def getDrawSettings(self):
        colors = self.getColors1()
        colhigh = self.getColorHigh()
        defaults = self.getDrawSettDef()
        draw_pord = dict([(v,p) for (p,v) in enumerate([SSetts.mud, SSetts.mua, SSetts.mub,
                                                        SSetts.muaB, SSetts.mubB,
                                                        SSetts.delta, SSetts.beta,
                                                        SSetts.alpha, SSetts.gamma])])
            
        dd = numpy.nan*numpy.ones(numpy.max(draw_pord.keys())+1)
        for (p,v) in enumerate([SSetts.delta, SSetts.beta, SSetts.alpha, SSetts.gamma]):
            dd[v] = p

        css = {"draw_pord": draw_pord, "draw_ppos": dd, "shape": defaults["shape"], "colhigh": colhigh}
        for (p, iid) in enumerate([SSetts.alpha, SSetts.beta, SSetts.gamma, SSetts.delta]):
            css[iid] = {"color_f": self.getColorA(colors[p]),
                        "color_e": self.getColorA(colors[p], 1.),
                        "color_l": self.getColorA(colors[p]), 
                        "shape": defaults["shape"], "size": defaults["size"],
                        "zord": self.DEF_ZORD}
        for (p, iid) in enumerate([SSetts.mua, SSetts.mub]):
            css[iid] = {"color_f": self.getColorA(defaults["color_f"], -.9),
                        "color_e": self.getColorA(colors[p], .9),
                        "color_l": self.getColorA(defaults["color_l"], -.9),
                        "shape": defaults["shape"], "size": defaults["size"]-1,
                        "zord": self.DEF_ZORD}
        for (p, iid) in enumerate([SSetts.mubB, SSetts.muaB]):
            css[iid] = {"color_f": self.getColorA(colors[p], -.9),
                        "color_e": self.getColorA(defaults["color_e"], .9),
                        "color_l": self.getColorA(defaults["color_l"], -.9),
                        "shape": defaults["shape"], "size": defaults["size"]-1,
                        "zord": self.DEF_ZORD}
        css[SSetts.mud] = {"color_f": self.getColorA(defaults["color_f"], -.9),
                           "color_e": self.getColorA(defaults["color_e"], .9),
                           "color_l": self.getColorA(defaults["color_l"], -.9),
                           "shape": defaults["shape"], "size": defaults["size"]-1,
                           "zord": self.DEF_ZORD}
        # css[SSetts.delta] = {"color_f": self.getColorA(defaults["color_f"]),
        #                      "color_e": self.getColorA(defaults["color_e"], 1.),
        #                      "color_l": self.getColorA(defaults["color_l"]),
        #                      "shape": defaults["shape"], "size": defaults["size"]-1,
        #                      "zord": self.DEF_ZORD}
        css[-1] = {"color_f": self.getColorA(defaults["color_f"], .5),
                   "color_e": self.getColorA(defaults["color_e"], .5),
                   "color_l": self.getColorA(defaults["color_l"], .5),
                   "shape": defaults["shape"], "size": defaults["size"]-1,
                   "zord": self.DEF_ZORD}
        css["default"] = defaults
        css[SSetts.alpha]["zord"] += 1
        css[SSetts.beta]["zord"] += 1
        css[SSetts.gamma]["zord"] += 2
        css[SSetts.delta]["zord"] -= 1
        return css
