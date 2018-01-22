import re
import wx
import numpy

from scipy.sparse import lil_matrix
# The recommended way to use wx with mpl is with the WXAgg backend. 
# import matplotlib
# matplotlib.use('WXAgg')

from matplotlib.path import Path

from lines_cust import CustLine2D

from classLView import LView

from ..reremi.classRedescription import Redescription

import pdb


class OverView(LView):

    cversion = 0
    TID = "OVE"
    SDESC = "OverLViz"
    ordN = 0
    title_str = "Overlap View"
    typesI = "r"

    color_palet = {'before': (0.2,0.2,0.2),
                   'before_light': (0.2,0.2,0.2),
                   'add': (1,1,0.25),
                   'add_light': (1,1,0.25)}
    pick_sz = 5
    

    def __init__(self, parent, vid, more=None):
        self.initVars(parent, vid, more)
        self.reds = {}
        self.srids = []
        self.rids_mapk = {}
        self.annotations = {}
        self.initView()

    def pickColor(self, ckey):
        return self.color_palet.get(ckey, (0,0,0))

    def drawFrameSpecific(self):

        # self.info_red = [wx.StaticText(self.panel, label="qL"), wx.StaticText(self.panel, label="qR")]
        # colors = self.getColors255()
        # self.info_red[0].SetForegroundColour(colors[0])
        # self.info_red[1].SetForegroundColour(colors[1])
        # font = wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        # self.info_red[0].SetFont(font)
        # self.info_red[1].SetFont(font)

        self.info_rids = []

    def addFrameSpecific(self):
        # self.innerBox1.Add(self.info_red[0], 0, border=1,  flag= wx.ALIGN_CENTER, userData={"where": "it"})
        # self.innerBox1.Add(self.info_red[1], 0, border=1,  flag= wx.ALIGN_CENTER, userData={"where": "it"})

        # self.innerBox1.AddSpacer((-1,self.getSpacerH()), userData={"where": "*"})
        
        self.lineB = wx.BoxSizer(wx.HORIZONTAL)
        self.innerBox1.Add(self.lineB, 0, border=1,  flag= wx.ALIGN_CENTER)

    def getNbReds(self):
        return len(self.srids)
    def getBeforeReds(self):
        try:
            return [self.reds[self.srids[pp]] for pp in range(self.current_pos)]
        except IndexError, KeyError:
            return None
    def getBeforeRids(self):
        try:
            return [self.srids[pp] for pp in range(self.current_pos)]
        except IndexError, KeyError:
            return None
    def getCurrentRed(self):
        try:
            return self.reds[self.srids[self.current_pos]]
        except IndexError, KeyError:
            return None
    def getCurrentRid(self):
        try:
            return self.srids[self.current_pos]
        except IndexError:
            return None
    def getCurrentPos(self):
        try:
            return self.current_pos
        except IndexError, KeyError:
            return None


    def updateText(self, pos = None):
        """ Reset red fields and info
        """
        if pos is None:
            red = self.getCurrentRed()
            cpos = self.getCurrentPos()
        # if red is not None:
        #     for side in [0, 1]:
        #         self.info_red[side].SetLabel(red.queries[side].disp(style="U", names=self.getParentData().getNames(side)))
            
        self.lineB.Clear()
        for e in self.info_rids:
            e.Destroy()
        self.info_rids = []
        self.rids_mapk = {}

        font_other = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        font_curr = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        for pos, rid in enumerate(self.srids):
            nid = wx.NewId()
            self.rids_mapk[nid] = pos
            self.info_rids.append(wx.StaticText(self.panel, nid, label="R%d" % rid))
            self.info_rids[-1].Bind(wx.EVT_LEFT_UP, self.OnClickRid)
            if pos == cpos:
                self.info_rids[-1].SetFont(font_curr)
            else:
                self.info_rids[-1].SetFont(font_other)
                self.info_rids[-1].SetBackgroundColour(self.pickColor('add'))
            if pos > 0:
                self.lineB.AddSpacer((self.getSpacerW(),-1), userData={"where": "it"})
            self.lineB.Add(self.info_rids[-1], 0, border=1,  flag= wx.ALIGN_CENTER|wx.EXPAND)

    def OnClickRid(self, event):
        if event.GetId() in self.rids_mapk:
            self.changePos(self.rids_mapk[event.GetId()])

    def additionalBinds(self):
        self.mapFrame.Bind(wx.EVT_KEY_DOWN, self.onKeyPress)
        self.MapfigMap.canvas.Bind(wx.EVT_KEY_DOWN, self.onKeyPress)
        for button in self.buttons:
            button["element"].Bind(wx.EVT_BUTTON, button["function"])

    def onKeyPress(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_RIGHT:
            self.changePos(self.getCurrentPos()+1)
        elif keycode == wx.WXK_LEFT:
            self.changePos(self.getCurrentPos()-1)
        event.Skip()

    def getCanvasConnections(self):
        return [('motion_notify_event', self.on_motion)]
    
    def changePos(self, pos=None):
        if pos >= self.getNbReds():
            pos = 0
        if pos < 0:
            pos = self.getNbReds()-1
        self.current_pos = pos
        self.updateMap()
        self.updateText()
        self._SetSize()

    def setCurrent(self, reds_map): ### collection of tuples
        self.reds = dict(reds_map)
        self.srids = [rid for (rid, red) in reds_map]
        self.parts, self.reds_mats, self.lits_acc = self.accumulateOccs()
        self.changePos(max(len(self.srids)-2, 0))

    def accumulateOccs(self):

        reds_mats = {}
        parts = {"supp": [], "vars": []}
        lits_acc = {}
        marg_acc = {"supp": numpy.zeros(self.getParentData().nbRows(), dtype=numpy.int),
                    "vars": numpy.zeros(self.getParentData().nbCols(0)+self.getParentData().nbCols(1), dtype=numpy.int)}

        for nn, rid in enumerate(self.srids):
            cur_mat = lil_matrix((self.getParentData().nbCols(0)+self.getParentData().nbCols(1),
                                  self.getParentData().nbRows()), dtype=numpy.bool)
            vsupp = list(self.reds[rid].getSuppI())
            vvars = set()
            off = 0
            for (side, lits) in enumerate(self.reds[rid].invLiterals()):
                for lit in lits:
                    c = lit.colId()
                    cur_mat[c+off, vsupp] = True
                    vvars.add(c+off)
                    marg_acc["vars"][c+off]+=1
                    if c+off in lits_acc: 
                        lits_acc[c+off].append((nn, rid, lit))
                    else:
                        lits_acc[c+off]= [(nn, rid, lit)]
                off += self.getParentData().nbCols(side)
            marg_acc["supp"][vsupp]+=1
            reds_mats[rid] = cur_mat

            cur_sets = {"supp": set(vsupp), "vars": vvars}
            for what in ["vars", "supp"]:
                if nn == 0:
                    parts[what].append({"inter": [],
                                        "before": [],
                                        "add": sorted(cur_sets[what], key=lambda x: marg_acc[what][x])
                                        })
                    parts[what][-1].update({"nb_inter": 0, "nb_before": 0,
                                            "nb_add": len(parts[what][-1]["add"]),
                                            "vids": numpy.array(parts[what][-1]["add"])})
                else:
                    lall = parts[what][-1]["before"]+parts[what][-1]["inter"]+parts[what][-1]["add"]
                    parts[what].append({"inter": [x for x in lall if x in cur_sets[what]],
                                        "before": [x for x in lall if x not in cur_sets[what]]
                                        })
                    parts[what][-1]["add"] = sorted(cur_sets[what].difference(parts[what][-1]["inter"]),
                                                       key=lambda x: marg_acc[what][x])
                    parts[what][-1].update({"nb_inter": len(parts[what][-1]["inter"]),
                                            "nb_before": len(parts[what][-1]["before"]),
                                            "nb_add": len(parts[what][-1]["add"]),
                                            "vids": numpy.array(parts[what][-1]["before"]+parts[what][-1]["inter"]+parts[what][-1]["add"])})

                parts[what][-1]["marg_acc"] = marg_acc[what].copy()

        return parts, reds_mats, lits_acc


    def updateMap(self):
        """ Redraws the map
        """

        if not hasattr( self, 'parts' ):
            return

        self.clearPlot()
        self.blocks = {}
        
        what_map = ["vars", "supp"]
        sizes = {"vars": self.getParentData().nbCols(0)+self.getParentData().nbCols(1),
                 "supp": self.getParentData().nbRows()}
                 
        ### TODO figure out data size that produces 1 point or x% on display
        sfactor = 50.
        self.block_size = {"vars": sizes["supp"]/sfactor, "supp": sizes["vars"]/sfactor}
        # self.block_size = {"vars": 1., "supp": 1.}
        nbreds = self.getNbReds()
        colors = self.getColors1()
        bsz = 0.4
        # unitmarker_points = numpy.array([[-bsz, -bsz], [bsz, -bsz], [bsz, bsz], [-bsz, bsz]]) ### centered
        unitmarker_points = numpy.array([[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]])



        data_pos = {"vars": self.parts["vars"][self.current_pos],
                    "supp": self.parts["supp"][self.current_pos]}
            
        mask = self.reds_mats[self.srids[0]].copy()
        for i in range(self.current_pos):
            mask += self.reds_mats[self.srids[i]]

        mask = mask[data_pos["vars"]["before"]+data_pos["vars"]["inter"],:][:,data_pos["supp"]["before"]+data_pos["supp"]["inter"]]

        x,y = mask.nonzero()
        marker = Path(unitmarker_points)
        blocks_mat = CustLine2D(x, y, linestyle='None', marker=marker,
                                mfc=self.pickColor('before'), mec=self.pickColor('before'))
        self.axe.add_line(blocks_mat)
        # self.blocks["cells"] = blocks_mat
        
        points = [(0, data_pos[what]["nb_before"],
                   data_pos[what]["nb_before"]+data_pos[what]["nb_inter"],
                   data_pos[what]["nb_before"]+data_pos[what]["nb_inter"]+data_pos[what]["nb_add"]) for what in ["vars", "supp"]]

        for (tc, bc, color, alph) in [(0,2, self.pickColor('before'), 0.6), (1,3, self.pickColor('add'), 0.6)]: # , (1,2,(0.65,0.65,0.65), 0.86)
            self.axe.fill([points[0][tc], points[0][bc], points[0][bc], points[0][tc]],
                          [points[1][tc], points[1][tc], points[1][bc], points[1][bc]],
                          color=color, alpha=alph, ec=color, zorder=15)


        # # pdb.set_trace()
        ccs = [numpy.where(data_pos["vars"]["vids"] < self.getParentData().nbCols(0))[0],
               numpy.where(data_pos["vars"]["vids"] >= self.getParentData().nbCols(0))[0]]
        bh = sizes["supp"]/sfactor

        mks_tmp = unitmarker_points.copy()
        mks_tmp[:,1] *= self.block_size["vars"]

        for side in [0,1]:
            histt = CustLine2D(ccs[side], -3*self.block_size["vars"]*numpy.ones(ccs[side].shape),
                               linestyle='None', marker=Path(mks_tmp),
                               mfc=colors[side], mec=colors[side], picker=self.pick_sz)
            self.axe.add_line(histt)
            self.blocks["lbl_%s" % side] = histt
            # self.labelCol(ccs[side][0], 0, side, 0)
        
        for whatn, what in enumerate(what_map):
            bb = data_pos[what]["marg_acc"][data_pos[what]["before"]+data_pos[what]["inter"]]
            nbc = data_pos[what]["nb_inter"]+data_pos[what]["nb_add"]
            pos = data_pos[what]["nb_before"]

            for i in range(self.current_pos):
                mks_tmp = unitmarker_points.copy()
                mks_tmp[:,1] *= self.block_size[what]
                mks_tmp[(2,3),1] += (i*self.block_size[what])

                coords = [numpy.where(bb==i+1)[0]]
                coords.append(numpy.ones(coords[0].shape)*(sizes[what_map[1-whatn]]+3*self.block_size[what]))
                histt = CustLine2D(coords[whatn], coords[1-whatn],
                                   linestyle='None', marker=Path(mks_tmp[:,(whatn, 1-whatn)]),
                                   mfc=self.pickColor('before_light'), mec=self.pickColor('before_light'), picker=self.pick_sz)
                self.axe.add_line(histt)
                self.blocks["hist_%s_b%s" % (what, i)] = histt

            mks_tmp = unitmarker_points.copy()
            mks_tmp[:,1] *= self.block_size[what]

            coords = [numpy.arange(nbc)+pos]
            coords.append(numpy.ones(nbc)*(sizes[what_map[1-whatn]]+3*self.block_size[what]))
            histt = CustLine2D(coords[whatn], coords[1-whatn],
                               linestyle='None', marker=Path(mks_tmp[:,(whatn, 1-whatn)]),
                               mfc=self.pickColor('add_light'), mec=self.pickColor('add_light'), picker=self.pick_sz)
            self.axe.add_line(histt)
            self.blocks["hist_%s_a" % what] = histt


        self.axe.plot([0, sizes["vars"], sizes["vars"], 0, 0],
                      [0, 0, sizes["supp"], sizes["supp"], 0],
                      color=(0,0,0))

        self.axe.set_xlim([-4*self.block_size["supp"], sizes["vars"]+(nbreds+7)*self.block_size["supp"]])
        self.axe.set_ylim([-4*self.block_size["vars"], sizes["supp"]+(nbreds+7)*self.block_size["vars"]])
        self.axe.invert_yaxis()
        self.axe.get_xaxis().tick_top()

        # lbl = self.axe.get_xticklabels()
        # self.axe.set_xticks([])
        # self.axe.set_yticks([])

        self.MapcanvasMap.draw()
        self.MapfigMap.canvas.SetFocus()

    def hoverActive(self):
        return True
        
    def on_motion(self, event):
        changed = []
        if event.inaxes == self.axe and hasattr( self, 'blocks'):
            active_anns = self.annotations.keys()
            for kk, v in self.blocks.items():
                if v.contains(event)[0]:
                    indices = v.contains(event)[1]["ind"]
                    anns = []
                    if kk in ["lbl_0", "lbl_1"] or re.match("hist_vars", kk):
                        ind = int(v.get_data()[0][indices[0]])
                        col = self.parts["vars"][self.getCurrentPos()]["vids"][ind]
                        if (kk, col) in active_anns:
                            active_anns.remove((kk, col))
                        else:
                            vid = self.getVarIdForCol(col)
                            if kk in ["lbl_0", "lbl_1"]:
                                anns = self.labelCol(ind+0.5, -4.*self.block_size["vars"], vid[0], vid[1])
                            else:
                                if col in self.lits_acc:
                                    llts = "\n".join(["R%s: %s" % (lit[1], lit[2]) for lit in self.lits_acc[col] if lit[0] <= self.getCurrentPos()])
                                    anns = self.labelLits(ind+0.5, self.axe.get_ylim()[0]-self.block_size["vars"], vid[0], llts)

                    elif re.match("hist_supp", kk):
                        ind = int(v.get_data()[1][indices[0]])
                        col = self.parts["supp"][self.getCurrentPos()]["vids"][ind]
                        if (kk, col) in active_anns:
                            active_anns.remove((kk, col))
                        else:
                            self.reds_mats[0][:,col].sum() > 0
                            ### TODO improve
                            sss = ", ".join(["R%s" % rri for rri in self.getBeforeRids()+[self.getCurrentRid()] if self.reds_mats[rri][:,col].sum() > 0])
                            anns = self.labelLits(self.axe.get_xlim()[1]-self.block_size["supp"], ind+0.5, 0, sss)
                    else:
                        print "HIT", kk, v.contains(event)


                    if len(anns) > 0:
                        self.annotations[(kk, col)] = anns
                        changed.append((kk, col))

            for aa in active_anns:
                for cs in self.annotations[aa]:
                    cs.remove()
                del self.annotations[aa]
                changed.append(aa)
        if len(changed) > 0:
            self.MapcanvasMap.draw()


    def getVarIdForCol(self, col):
        if col < self.getParentData().nbCols(0):
            return (0, col)
        else:
            return (1, col-self.getParentData().nbCols(0))

    def labelCol(self, x,y, side, col):
        print "Label col", x, y, side, col
        ds = self.getDrawSettings()
        tb = self.axe.annotate(self.getParentData().col(side, col).getName(),
                               xy =(x, y), xytext =(x, y+0.02),
                               horizontalalignment='center', verticalalignment='bottom', color=ds[side]["color_l"],
                               bbox=dict(boxstyle="round", fc="w", ec="none", alpha=0.7),
                               )        
        tf = self.axe.annotate(self.getParentData().col(side, col).getName(),
                               xy =(x, y), xytext =(x, y+0.02),
                               horizontalalignment='center', verticalalignment='bottom', color=ds[side]["color_l"],
                               bbox=dict(boxstyle="round", fc=ds[side]["color_l"], ec="none", alpha=0.3),
                               )
        return [tb, tf]

    def labelLits(self, x, y, side, lits_str):
        ds = self.getDrawSettings()
        tb = self.axe.annotate(lits_str,
                               xy =(x, y), xytext =(x, y+0.02),
                               horizontalalignment='left', verticalalignment='bottom', color=ds[side]["color_l"],
                               bbox=dict(boxstyle="round", fc="w", ec="none", alpha=0.7),
                               )        
        tf = self.axe.annotate(lits_str,
                               xy =(x, y), xytext =(x, y+0.02),
                               horizontalalignment='left', verticalalignment='bottom', color=ds[side]["color_l"],
                               bbox=dict(boxstyle="round", fc=ds[side]["color_l"], ec="none", alpha=0.3),
                               )
        return [tb, tf]

