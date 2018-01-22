import wx
### from wx import ALIGN_BOTTOM, ALIGN_CENTER, ALIGN_LEFT, ALIGN_RIGHT, ALL, EXPAND, HORIZONTAL, RAISED_BORDER, TE_PROCESS_ENTER, VERTICAL
### from wx import BoxSizer, DisplaySize, FlexGridSizer, Frame, Menu, MenuBar, NewId, Panel, Sizer, SizerItem, StaticBitmap, StaticText, TextCtrl, ToggleButton
### from wx import EVT_BUTTON, EVT_CLOSE, EVT_ENTER_WINDOW, EVT_LEAVE_WINDOW, EVT_LEFT_UP, EVT_MENU, EVT_SIZE, EVT_TEXT_ENTER, EVT_TOGGLEBUTTON, EVT_TOOL

import numpy
# The recommended way to use wx with mpl is with the WXAgg
# backend. 
# import matplotlib
# matplotlib.use('WXAgg')

from classBasisView import BasisView

from ..reremi.classQuery import SYM, Query
from ..reremi.classSParts import SSetts
from ..reremi.classRedescription import Redescription

import pdb


class GView(BasisView):

    label_jacc="J ="
    label_pval="p-value ="
    label_cardAlpha="|E"+SYM.SYM_ALPHA+"| ="
    label_cardBeta="|E"+SYM.SYM_BETA+"| ="
    label_cardU="|E"+SYM.SYM_SETMIN+"E"+SYM.SYM_DELTA+"| ="
    label_cardI="|E"+SYM.SYM_GAMMA+"| ="
    label_cardO="|E"+SYM.SYM_DELTA+"| ="
    label_cardT="|E| ="

    label_learn = SYM.SYM_LEARN #+":"
    label_test = SYM.SYM_TEST #+":"
    label_ratio = SYM.SYM_RATIO #+":"

    label_inout = SYM.SYM_INOUT
    label_outin = SYM.SYM_OUTIN 
    label_cross = SYM.SYM_CROSS

    map_select_supp = [("l", "|E"+SYM.SYM_ALPHA+"|", [SSetts.alpha]), ("r", "|E"+SYM.SYM_BETA+"|", [SSetts.beta]),
                       ("i", "|E"+SYM.SYM_GAMMA+"|", [SSetts.gamma]), ("o", "|E"+SYM.SYM_DELTA+"|", [SSetts.delta])]

    infos_details = [{"id": "jacc", "label": label_jacc, "meth": "getRoundAcc", "format": "%1.3f"},
                     {"id": "lenI", "label": label_cardI, "meth": "getLenI", "format": "%i", "color":2},
                     {"id": "lenA", "label": label_cardAlpha, "meth": "getLenA", "format": "%i", "color":0},
                     {"id": "lenT", "label": label_cardT, "meth": "getLenT", "format": "%i"},
                     {"id": "pval", "label": label_pval, "meth": "getRoundPVal", "format": "%1.3f"},
                     {"id": "lenO", "label": label_cardO, "meth": "getLenO", "format": "%i"},
                     {"id": "lenB", "label": label_cardBeta, "meth": "getLenB", "format": "%i", "color":1},
                     {"id": "lenU", "label": label_cardU, "meth": "getLenU", "format": "%i"},]
    max_emphlbl = 5
    
    TID = "G"
    SDESC = "Viz"
    ordN = 0
    title_str = "View"
    geo = False
    typesI = "evr"

    
    def __init__(self, parent, vid, more=None):
        self.initVars(parent, vid, more)
        self.queries = [Query(), Query()]
        self.initView()
        self.dots_draws = None
        self.suppABCD = None

    def prepareEntitiesDots(self):
        draw_settings = self.getDrawSettings()

        vec = numpy.empty((0))
        if self.suppABCD is not None:
            vec = numpy.array(self.suppABCD)
        u, indices = numpy.unique(vec, return_inverse=True)

        styles = []
        for i in u:
            if draw_settings[i]["shape"] in [".",",","*","+","x"]:
                #### point-wise shape -> same color face and edge
                styles.append(draw_settings[i]["color_e"])
            else:
                #### otherwise -> possibly different colors face and edge
                styles.append(draw_settings[i]["color_f"])
        fc_clusts = numpy.array(styles)
        # fc_clusts = numpy.array([draw_settings[i]["color_f"] for i in u])
        fc_dots = fc_clusts[indices]
        ec_clusts = numpy.array([draw_settings[i]["color_e"] for i in u])
        ec_dots = ec_clusts[indices]
        lc_clusts = numpy.array([draw_settings[i]["color_l"] for i in u])
        lc_dots = lc_clusts[indices]
        zord_clusts = numpy.array([draw_settings[i]["zord"] for i in u])
        zord_dots = zord_clusts[indices]
            
        delta_dots = vec==SSetts.delta
        
        sz_dots = numpy.ones(vec.shape)*draw_settings["default"]["size"]
        sz_dots[~ delta_dots] *= 0.5

        if self.getDeltaOn():
            draw_dots = numpy.ones(vec.shape, dtype=bool)
        else:
            draw_dots = ~ delta_dots

        return {"fc_dots": fc_dots, "ec_dots": ec_dots, "lc_dots": lc_dots, "sz_dots": sz_dots, "zord_dots": zord_dots, "draw_dots": draw_dots}

    def prepareProcesses(self):
        self.processes_map = {"E*": {"label": "Expand", "legend": "Expand the current redescription.",
                                     "more": None, "more_dyn":[], "order": 0},
                              "EL": {"label": "Expand LHS", "legend": "Expand the LHS query of the current redescription.",
                                     "more": {"side":0}, "more_dyn":[], "order":1},
                              "ER": {"label": "Expand RHS", "legend": "Expand the RHS query of the current redescription.",
                                     "more": {"side":1}, "more_dyn":[], "order":2},
                              "OL": {"label": "Overfit LHS", "legend": "Overfit LHS wrt the selected area.",
                                     "more": {"side":0, "in_weight":10}, "more_dyn":[self.getWeightCover], "order":3},
                              "OR": {"label": "Overfit RHS", "legend": "Overfit RHS wrt the selected area.",
                                     "more": {"side":1, "in_weight":10}, "more_dyn":[self.getWeightCover], "order":4} }
        
    def prepareActions(self):
        self.actions_map = {"deselect_all": {"method": self.do_deselect_all, "label": "&Deselect all",
                                             "legend": "Deselect all dots", "more": None, "type": "main",
                                             "order":1, "active_q":self.q_has_selected},
                            "flip_able": {"method": self.do_flip_emphasized, "label": "(Dis)able selected",
                                             "legend": "(Dis)able selected dots", "more": None, "type": "main",
                                             "order":0, "active_q":self.q_has_selected},
                            "noggle_info": {"method": self.do_toggle_info, "label": "Toggle i&nfo",
                                               "legend": "Toggle info", "more": None,  "type": "check",
                                               "order":101, "active_q":self.q_active_info}
                            }

        for setk, setl, setp in self.map_select_supp:
            self.actions_map[setk+"_set"] = {"method": self.do_set_select, "label": "(De)select "+setl,
                                                 "legend": "(De)select dots in "+setl, "more": setp, "type": "main",
                                                 "order":2, "active_q":self.q_not_svar}

        if self.mc is not None:
            self.actions_map["poly_set"] = {"method": self.do_select_poly, "label": "(De)select &polygon",
                                               "legend": "Select dots inside the polygon", "more": None,  "type": "main",
                                               "order":3, "active_q":self.q_has_poly}
            self.actions_map["toggle_draw"] = {"method": self.do_toggle_poly, "label": "&Toggle polygon",
                                               "legend": "Toggle polygon drawing", "more": None,  "type": "check",
                                               "order":100, "active_q":self.q_active_poly}

        
    def enumerateVizItems(self):
        if self.hasParent():
            return self.parent.viewsm.getViewsItems(what=self.getQueries(), vkey=self.getId())
        return []

    def additionalBinds(self):
        self.MapredMapQ[0].Bind(wx.EVT_TEXT_ENTER, self.OnEditQuery)
        self.MapredMapQ[1].Bind(wx.EVT_TEXT_ENTER, self.OnEditQuery)
        for button in self.buttons:
            button["element"].Bind(wx.EVT_BUTTON, button["function"])
        
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
        self.parent.expandFromView(params)

    def OnExpandSimp(self, event):
        params = {"red": self.getCopyRed()}
        self.parent.expandFromView(params)

    def setSizeSpec(self, figsize):
        self.MapredMapQ[0].SetMinSize((1*figsize[0], -1))
        self.MapredMapQ[1].SetMinSize((1*figsize[0], -1))

    def OnEditQuery(self, event):
        if event.GetId() in self.QIds:
            side = self.QIds.index(event.GetId())
            self.updateQuery(side)

    def refresh(self):
        self.autoShowSplitsBoxes()
        red = Redescription.fromQueriesPair(self.queries, self.getParentData())
        red.setRestrictedSupp(self.getParentData())
        self.suppABCD = red.supports().getVectorABCD()
        self.updateText(red)
        self.updateMap()
        if self.isIntab():
            self._SetSize()

    def updateQuery(self, sd=None, query=None):
        if sd is None:
            queries = [self.parseQuery(0), self.parseQuery(1)]
        else:
            queries = [None, None]
            if query is None:
                queries[sd] = self.parseQuery(sd)
            else:
                queries[sd] = query

        changed = False
        for side in [0,1]:
            if queries[side] != None and queries[side] != self.queries[side]:
                self.queries[side] = queries[side]
                changed = True

        if changed:
            red = Redescription.fromQueriesPair(self.queries, self.getParentData())
            red.setRestrictedSupp(self.getParentData())
            self.suppABCD = red.supports().getVectorABCD()
            self.updateText(red)
            self.makeMenu()
            self.sendEditBack(red)
            self.updateMap()
        else: ### wrongly formatted query or not edits, revert
            for side in [0,1]:
                self.updateQueryText(self.queries[side], side)
            red = Redescription.fromQueriesPair(self.queries, self.getParentData())
        return red

    def setCurrent(self, qr=None):
        if qr is not None:
            if type(qr) in [list, tuple]:
                queries = qr
                red = Redescription.fromQueriesPair(qr, self.getParentData())
            else:
                red = qr
                queries = [red.query(0), red.query(1)]
            self.queries = queries
            red.setRestrictedSupp(self.getParentData())
            self.suppABCD = red.supports().getVectorABCD()
            self.updateText(red)
            self.updateMap()
            self.makeMenu()
            return red
        
    def isSingleVar(self):
        return (len(self.queries[0]) == 0 and self.queries[1].isBasis(1, self.getParentData())) or \
          (len(self.queries[1]) == 0 and self.queries[0].isBasis(0, self.getParentData()))

    def getQCols(self):
        return [(0,c) for c in self.queries[0].invCols()]+[(1,c) for c in self.queries[1].invCols()]
    
    def getCol(self, side, c):
        return self.getParentData().col(side, c)
        
    def parseQuery(self, side):
        stringQ = self.MapredMapQ[side].GetValue().strip()
        try:
            query = Query.parse(stringQ, self.getParentData().getNames(side))
        except:
            query = None
        if query is not None and (len(stringQ) > 0 and len(query) == 0):
            query = None
        return query                    
       

    def drawFrameSpecific(self):
        self.QIds = [wx.NewId(), wx.NewId()]
        self.MapredMapQ = [wx.TextCtrl(self.panel, self.QIds[0], style=wx.TE_PROCESS_ENTER),
                           wx.TextCtrl(self.panel, self.QIds[1], style=wx.TE_PROCESS_ENTER)]
        # self.MapredMapQ = [wx.TextCtrl(self.mapFrame, self.QIds[0]),
        #                    wx.TextCtrl(self.mapFrame, self.QIds[1])]
        colors = self.getColors255()
        self.MapredMapQ[0].SetForegroundColour(colors[0])
        self.MapredMapQ[1].SetForegroundColour(colors[1])

        self.info_items = {}
        for info_item in self.infos_details:
            # self.info_items[info_item["id"]] = (wx.StaticText(self.panel, label=info_item["label"], style=styL, size=sizz),
            #                                     wx.StaticText(self.panel, label="--", style=styV, size=sizz))
            self.info_items[info_item["id"]] = (wx.StaticText(self.panel, label=info_item["label"]),
                                                wx.StaticText(self.panel, label="XXX"))


            if info_item.get("color") is not None:
                self.info_items[info_item["id"]][1].SetForegroundColour(colors[info_item.get("color")])

    def addFrameSpecific(self):
        self.innerBox1.Add(self.MapredMapQ[0], 0, border=1,  flag= wx.ALIGN_CENTER, userData={"where": "it"})
        self.innerBox1.Add(self.MapredMapQ[1], 0, border=1,  flag= wx.ALIGN_CENTER, userData={"where": "it"})

        self.innerBox1.AddSpacer((-1,self.getSpacerH()), userData={"where": "*"})
        
        cols = [wx.BoxSizer(wx.VERTICAL) for i in range(2*self.nb_cols)]
        for pi, elem in enumerate(self.infos_details):
            ci = 2*(pi % self.nb_cols)
            cols[ci].Add(self.info_items[elem["id"]][0], 1, border=1,  flag= wx.ALL|wx.ALIGN_RIGHT, userData={"where": "it"})
            cols[ci+1].Add(self.info_items[elem["id"]][1], 1, border=1,  flag= wx.ALL|wx.ALIGN_RIGHT, userData={"where": "it"})
        # self.opt_hide.extend(cols)

        lineB = wx.BoxSizer(wx.HORIZONTAL)
        for ci, col in enumerate(cols):
            lineB.Add(col, 0, border=1,  flag= wx.ALIGN_CENTER|wx.EXPAND)
            if ci % 2 == 1 and ci < len(cols)-1:
                lineB.AddSpacer((self.getSpacerW(),-1), userData={"where": "it"})
        self.innerBox1.Add(lineB, 0, border=1,  flag= wx.ALIGN_CENTER)

 

    def updateQueryText(self, query, side):
        self.MapredMapQ[side].ChangeValue(query.disp(style="U", names=self.getParentData().getNames(side)))
        #self.MapredMapQ[side].ChangeValue(query.disp()) #, unicd=True), unicd=True))

    def updateText(self, red = None):
        """ Reset red fields and info
        """
        if red is not None:
            for side in [0, 1]:
                self.updateQueryText(red.queries[side], side)
            self.setMapredInfo(red)

    def setMapredInfo(self, red = None, details=None):
        for det in self.infos_details:
            if red is not None:
                meth = getattr(red,det["meth"], None)
            else:
                meth = None
                
            if meth is not None:
                self.info_items[det["id"]][1].SetLabel(det["format"] % meth(self.getDetailsSplit()))
            else:
                self.info_items[det["id"]][1].SetLabel("XX")

    def apply_mask(self, path, radius=0.0):
        if path is not None and self.getCoords() is not None:
            points = numpy.transpose((self.getCoords(0), self.getCoords(1)))
            return [i for i,point in enumerate(points) if path.contains_point(point, radius=radius)]
        return []
                
    def do_deselect_all(self, more=None):
        self.sendEmphasize(None)

    def do_set_select(self, setp):
        points = [i for (i,p) in enumerate(self.suppABCD) if p in setp]
        self.sendEmphasize(points)
                
    def do_select_poly(self, more=None):
        points = self.apply_mask(self.mc.get_path())
        self.mc.clear()
        if points != set():
            self.sendEmphasize(points)

    def do_flip_emphasized(self, more=None):
        self.sendFlipEmphasizedR()

    
    def getPlotColor(self, idp, prop):
        return tuple(self.dots_draws[prop+"_dots"][idp])
    def getPlotProp(self, idp, prop):
        return self.dots_draws[prop+"_dots"][idp]
    
    def hasDotsReady(self):
        return self.dots_draws is not None
    
    def getCoords(axi=None, ids=None):
        return None
    def getCoordsXY(self, id):
        return (0,0)
    def getCoordsXYA(self, id):
        return self.getCoordsXY(id)

    def getAnnXY(self):
        return self.ann_xy

    def drawEntity(self, idp, fc, ec, sz, zo=4, dsetts={}):        
        x, y = self.getCoordsXY(idp)
        return self.axe.plot(x, y, mfc=fc, mec=ec, marker=dsetts.get("shape"), markersize=sz, linestyle=dsetts.get("linestyle", 'None'), zorder=zo)
    
    def drawAnnotation(self, xy, ec, tag, xytext=(-10, 15)):
        return [self.axe.annotate(tag, xy=xy,
                                xycoords='data', xytext=xytext, textcoords='offset points',
                                color=ec, size=10, va="center", backgroundcolor="#FFFFFF",
                                bbox=dict(boxstyle="round", facecolor="#FFFFFF", ec=ec),
                                arrowprops=dict(arrowstyle="wedge,tail_width=1.", fc="#FFFFFF", ec=ec,
                                                    patchA=None, patchB=self.el, relpos=(0.2, 0.5)))]
    
    def emphasizeOn(self, lids, hover=False):
        dsetts = self.getDrawSettDef()
        if not self.hasDotsReady():
            return

        hgs = {}
        for lid in self.needingHighlight(lids):
            hg = self.drawEntity(lid, self.getColorHigh(), self.getPlotColor(lid, "ec"), self.getPlotProp(lid, "sz"), self.getPlotProp(lid, "zord"), dsetts)
            if lid not in hgs:
                hgs[lid] = []
            hgs[lid].extend(hg)
            
        for lid in self.needingHighLbl(lids):
            tag = self.getParentData().getRName(lid)
            hg = self.drawAnnotation(self.getCoordsXYA(lid), self.getPlotColor(lid, "ec"), tag, self.getAnnXY())
            if lid not in hgs:
                hgs[lid] = []
            hgs[lid].extend(hg)

        self.addHighlighted(hgs, hover)

            
    def inCapture(self, event):
        return event.inaxes == self.axe and numpy.abs(numpy.around(event.xdata) - event.xdata) < self.flat_space \
          and event.ydata >= self.missing_yy-.1 and event.ydata <= 1

    def on_motion(self, event):
        if self.hoverActive() and self.inCapture(event):
            lid = self.getLidAt(event.xdata, event.ydata)
            if lid is None:
                self.emphasizeOnOff(turn_off=None, hover=True, review=True)
            elif not self.isHovered(lid):
                self.emphasizeOnOff(turn_on=[lid], turn_off=None, hover=True, review=True)
                
    def on_click(self, event):
        if self.clickActive() and self.inCapture(event):
            lid = self.getLidAt(event.xdata, event.ydata)
            if lid is not None:
                self.sendEmphasize([lid])        
