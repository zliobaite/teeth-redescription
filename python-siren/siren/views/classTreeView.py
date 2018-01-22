from __future__ import unicode_literals
import wx
### from wx import ALIGN_CENTER, ALL, EXPAND, HORIZONTAL
### from wx import FONTFAMILY_DEFAULT, FONTSTYLE_NORMAL, FONTWEIGHT_NORMAL
### from wx import BoxSizer, Button, Font, NewId
### from wx import EVT_BUTTON, EVT_LEFT_DCLICK

import numpy
# The recommended way to use wx with mpl is with the WXAgg
# backend. 
# import matplotlib
# matplotlib.use('WXAgg')

from ..reremi.classQuery import QTree
from ..reremi.classRedescription import Redescription
from classGView import GView

import pdb
            
class TreeView(GView):

    TID = "TR"
    SDESC = "Tree"
    ordN = 5
    title_str = "Decision Tree"
    typesI = "vr"
    
    all_width = 1.
    height_inter = [2., 3.] ### starting at zero creates troubles with supp drawing, since it's masking non zero values..
    maj_space = 0.05
    min_space = 0.01
    flat_space = 0.03
    margins_sides = 0.5
    margins_tb = 0.1
    margin_hov = min_space/2.
    missing_yy = -1./6

    ann_xy = (10,0)
    
    @classmethod
    def suitableView(tcl, geo=False, what=None, tabT=None):
        return (tabT is None or tabT in tcl.typesI) and (not tcl.geo or geo) and \
               ( what is None or (what[0].isTreeCompatible() and what[1].isTreeCompatible()))

    def __init__(self, parent, vid, more=None):
        self.current_r = None
        self.trees = None
        self.store_supp = None
        GView.__init__(self, parent, vid)
    
    def getId(self):
        return (self.TID, self.vid)

    def setCurrent(self, qr=None):
        if qr is not None:
            if type(qr) in [list, tuple]:
                queries = qr
                red = Redescription.fromQueriesPair(qr, self.getParentData())
            else:
                red = qr
                queries = [red.query(0), red.query(1)]
            self.queries = queries
            ## red.setRestrictedSupp(self.getParentData())
            ## self.suppABCD = red.supports().getVectorABCD()
            self.suppABCD = red.getRSetParts(self.getDetailsSplit()).getVectorABCD(force_list=True)
            self.current_r = red
            self.updateText(red)
            self.updateMap()
            return red

    def updateQuery(self, sd=None, query=None, force=False, upAll=True, update_trees=True):
        if sd is None:
            queries = [self.parseQuery(0),self.parseQuery(1)]
        else:
            queries = [None, None]
            if query is None:
                queries[sd] = self.parseQuery(sd)
            else:
                queries[sd] = query

        changed = False
        old = [None, None]
        for side in [0,1]:
            old[side] = self.queries[side]
            if queries[side] != None and queries[side] != self.queries[side]:
                self.queries[side] = queries[side]
                changed = True

        red = None
        if changed or force:
            try:
                red = Redescription.fromQueriesPair(self.queries, self.getParentData())
            except Exception:
                ### Query could be parse but not recomputed
                red = None
                self.queries = old
        if red is not None:
            # red.setRestrictedSupp(self.getParentData())
            # self.suppABCD = red.supports().getVectorABCD()
            self.suppABCD = red.getRSetParts(self.getDetailsSplit()).getVectorABCD(force_list=True)
            self.current_r = red
            if upAll:
                self.updateText(red)
                self.makeMenu()
                self.sendEditBack(red)
            self.updateMap(update_trees)
            return red
        else: ### wrongly formatted query, revert
            for side in [0,1]:
                self.updateQueryText(self.queries[side], side)
        return None
        
    def getCanvasConnections(self):
        return [('pick_event', self.OnPick),
                ('button_release_event', self.on_click),
                ('motion_notify_event', self.on_motion)]

        
    def plotTrees(self, trees):
        draw_settings = self.getDrawSettings()
        self.plotTreesT(trees, draw_settings)
        # self.plotTreesBasic(trees, draw_settings)
        for side in [0,1]:
            self.plotTree(side, trees[side], None, draw_settings)
            if self.hasMissingPoint(side):
                b = trees[side].getBottomX()
                self.axe.plot(b, self.height_inter[0]+self.missing_yy, 'o', mec='k', mfc=draw_settings[-1]["color_l"], zorder=10)

    def plotTreesBasic(self, trees, draw_settings):
        ##### DRAW each line
        keys = []
        for side in [0,1]:
            for k in trees[side].getLeaves():
                keys.append((side, k, trees[side].getNodeXY(k)[1]))
                    
        mat = numpy.zeros((self.parent.dw.data.nbRows(), len(keys)+1))
        for ki, (side, k, pos) in enumerate(keys):
            for si, supp_part in enumerate(trees[side].getNodeSuppSets(k)):
                mat[list(supp_part), ki] = pos
                mat[list(supp_part), -1] = si

        mask = mat > 0
        parts = list(mat[:,-1])
        oids = numpy.argsort((mat[:,:-1].sum(axis=1)+(mat[:,-1]+1)*mat.max()*mat.shape[1])/(mask.sum(axis=1)))
        mat[oids,-1] = numpy.linspace(self.height_inter[0], self.height_inter[1], mat.shape[0])
        for li, k in zip(*numpy.where(mat[:, :-1]> 0)):
            x,y = trees[keys[k][0]].getNodeXY(keys[k][1])
            b = trees[keys[k][0]].getBottomX()
            self.axe.plot((b, 0), (y, mat[li,-1]), color=draw_settings[parts[li]]["color_l"])

    def plotTreesT(self, trees, draw_settings):
        ##### DRAW polygons
        keys = []
        lparts = trees[0].getNodeSupps(None)
        order_parts = [r for r in range(len(lparts)) if r != 2][::-1]+[2]
        pmap = dict([(v,i) for (i,v) in enumerate(order_parts)])
        ## nbrows = numpy.sum(lparts)
        nbrows = self.getParentData().nbRows()
        nbparts = len(lparts)
        for side in [0,1]:
            for k in trees[side].getLeaves():
                keys.append((side, k, trees[side].getNodeXY(k)[1]))

        ## pdb.set_trace()
        mat = numpy.zeros(nbrows, dtype=int)
        parts = numpy.zeros((nbrows, nbparts), dtype=bool)
        for ki, (side, k, pos) in enumerate(keys):
            for si, supp_part in enumerate(trees[side].getNodeSuppSets(k)):
                mat[list(supp_part)] += 2**(ki+1)
                parts[list(supp_part), si] = True
        connects = []
        map_p = {}
        store_lids = {}
        for v in numpy.unique(mat):
            idxs = tuple([i for (i,vb) in enumerate(bin(v)[::-1]) if vb == '1'])
            for i in range(parts.shape[1]):
                c = numpy.sum((mat == v)*parts[:,i])
                if c > 0:
                    map_p[(i, idxs, c)] = (v, i)
                    connects.append((i, idxs, c))
                    store_lids[(v,i)] = numpy.where((mat == v)*parts[:,i])[0]

        tot_height = self.height_inter[1]-self.height_inter[0]
        scores = {}
        for x in connects:
            sctmp = [pmap[x[0]], -1, -1]
            for side in [0,1]:
                nps = [keys[xx-1][-1] for xx in x[1] if keys[xx-1][0]==side]
                if len(nps) > 0:
                    sctmp[1+side] = numpy.mean(nps)
            scores[x] = tuple(sctmp)

        connects.sort(key=lambda x: scores[x])
        counts = [[] for i in lparts]
        for (i, idx, c) in connects:
            counts[pmap[i]].append(c)
        bb = (1-(len(lparts)-1)*self.maj_space)*numpy.cumsum([0]+[lparts[p] for p in order_parts])/(1.*numpy.sum(lparts))
        
        pos = []
        for i in range(len(counts)):
            if len(counts[i]) > 0 and numpy.sum(counts[i]) > 0:
                bot, top = bb[i] + i*self.maj_space, bb[i+1] + i*self.maj_space
                span = top-bot - (len(counts[i])-1)*self.min_space
                sbb = span*numpy.cumsum([0]+counts[i])/(1.0*numpy.sum(counts[i]))
                for j in range(len(sbb)-1): 
                    pos.append((self.height_inter[0]+tot_height*(bot+j*self.min_space+sbb[j]),
                                self.height_inter[0]+tot_height*(bot+j*self.min_space+sbb[j+1])))

        store_pos = {}
        has_miss_points = [False, False]
        # pos = numpy.linspace(1., 2., len(connects))
        for pi, (part, points, nb) in enumerate(connects):
            tmp_store_pos = [(pos[pi][0], pos[pi][1])]
            hasBSides = [False, False]
            for point in points:
                #self.axe.plot((0, Xss[keys[point-1][0]][-1], 0, 0),
                hasBSides[keys[point-1][0]] = True
                b = trees[keys[point-1][0]].getBottomX()
                ff = numpy.sign(b)*self.flat_space
                self.axe.fill((0, ff, b, ff, 0, 0),
                              (pos[pi][0], pos[pi][0], keys[point-1][-1],
                               pos[pi][1], pos[pi][1], pos[pi][0]),
                               color=draw_settings[part]["color_e"]) #, linewidth=nb/nbtot)
                tmp_store_pos.append((b, keys[point-1][-1]))
            for side, hS in enumerate(hasBSides):
                if not hS:
                    b = trees[side].getBottomX()
                    ff = -numpy.sign(0.5-side)*self.flat_space
                    self.axe.fill((0, ff, b, ff, 0, 0),
                                  (pos[pi][0], pos[pi][0], self.height_inter[0]+self.missing_yy,
                                   pos[pi][1], pos[pi][1], pos[pi][0]),
                                  color=draw_settings[part]["color_l"]) #, linewidth=nb/nbtot)
                    tmp_store_pos.append((b, self.height_inter[0]+self.missing_yy))
                    has_miss_points[side] = True
            # if (part, points, nb) == (0, (4,16), 1173):
            #     print "THIS:", map_p[(part, points, nb)], tmp_store_pos
            # store_pos[map_p[(part, points, nb)]] = (part, points, nb, tmp_store_pos)
            store_pos[map_p[(part, points, nb)]] = (part, points, nb, tmp_store_pos)
        self.store_supp = {"pos": store_pos, "mat": mat, "parts": parts, "lids": store_lids, "has_miss_points": has_miss_points}
        self.makePMapping()

    def makePMapping(self):
        tmp = []
        for bnds, p in sorted([(v[-1][0], k) for (k,v) in self.store_supp["pos"].items()]):
            tmp.extend([(bnds[0], p, -1), (bnds[1], p, 1)])
        self.store_supp["pmap"] = tmp
        
    def plotTree(self, side, tree, node, ds=None):
        
        color_dot = {0: ds[0]["color_l"], 1: ds[1]["color_l"]}
        line_style = {QTree.branchY: "-", QTree.branchN: "--"}
        # rsym = {0: ">", 1: "<"}
        x, y = tree.getNodeXY(node)

        # if node is not None:
        #     self.axe.annotate("#%d" % node,
        #                       xy =(x, y), xytext =(x, y-0.05))

        if tree.isLeafNode(node):
            b = tree.getBottomX()
            self.axe.plot((x, b), (y, y), 'k:')
            self.axe.plot(x, y, 'k.')
            if tree.isLeafInNode(node):
                self.axe.plot(b, y, 'ko', picker=5, gid="%d:%d:-1.T" % (side, node), zorder=10)
            else:
                self.axe.plot(b, y, 'wo', picker=5, gid="%d:%d:+1.T" % (side, node), zorder=10)
                
        else:
            # if tree.isRootNode(node):
            #     self.axe.plot(x, y, 'k'+rsym[side], picker=5, gid="%d.S" % side)
            if tree.isParentNode(node):
                for ynb in [0,1]:                        
                    for ci, child in enumerate(tree.getNodeChildren(node, ynb)):
                        xc, yc = tree.getNodeXY(child)
                        self.axe.plot((x, xc), (y, yc), 'k'+line_style[ynb], linewidth=1.5)
                        self.plotTree(side, tree, child, ds=ds)

            if tree.isSplitNode(node):
                self.axe.plot(x, y, color=color_dot[side], marker='s')
                # self.axe.annotate(tree.getNodeSplit(node).disp(), # NO NAMES names=self.getParentData().getNames(side)),
                self.axe.annotate(tree.getNodeSplit(node).disp(names=self.getParentData().getNames(side)),
                                  xy =(x, y), xytext =(x, y+0.02),
                                  horizontalalignment='center', color=color_dot[side],
                                  bbox=dict(boxstyle="round", fc="w", ec="none", alpha=0.7),
                                  )
                # self.axe.annotate(tree.getNodeSplit(node).disp(), # NO NAMES names=self.getParentData().getNames(side)),
                self.axe.annotate(tree.getNodeSplit(node).disp(names=self.getParentData().getNames(side)),
                                  xy =(x, y), xytext =(x, y+0.02),
                                  horizontalalignment='center', color=color_dot[side],
                                  bbox=dict(boxstyle="round", fc=color_dot[side], ec="none", alpha=0.3),
                                  )
                # self.axe.text(Xs[tree[node]["depth"]], Ys[node]-0.05, "%s" % (supps[node]), horizontalalignment='center')
                
    def okTrees(self):
        return self.trees is not None \
          and self.trees[0] is not None and self.trees[1] is not None \
          and not self.trees[0].isBroken() and not self.trees[1].isBroken()
                

    def updateMap(self, update_trees=True):
        """ Redraws the map
        """

        if self.current_r is not None:
            
            red = self.current_r
            if update_trees:
                self.trees = [red.queries[0].toTree(), red.queries[1].toTree()]

            for butt in self.buttons:
                if not self.okTrees():
                    butt["element"].Disable()
                else:
                    butt["element"].Enable()
                    
            if self.okTrees():
                ## rsupp = red.supports().parts4M()
                rsupp = red.getRSetParts(self.getDetailsSplit()).parts4M()
                for side in [0,1]:
                    self.trees[side].computeSupps(side, self.getParentData(), rsupp)
                    if update_trees:
                        self.trees[side].positionTree(side, all_width=self.all_width, height_inter=self.height_inter)

                self.clearPlot()

                self.dots_draws = self.prepareEntitiesDots()     
                # print "========= LEFT =======\n%s\n%s\n" % (red.queries[0], self.trees[0])
                # print "========= RIGHT =======\n%s\n%s\n" % ( red.queries[1], self.trees[1])

                self.plotTrees(self.trees)

                self.axe.set_xlim([-self.all_width-self.margins_sides, self.all_width+self.margins_sides])
                if self.hasMissingPoints():
                    self.axe.set_ylim([self.height_inter[0]+self.missing_yy-self.margins_tb,
                                       self.height_inter[1]+self.margins_tb])
                else:
                    self.axe.set_ylim([self.height_inter[0]-self.margins_tb, self.height_inter[1]+self.margins_tb])

                self.axe.set_xticks([])
                self.axe.set_yticks([])

                self.MapcanvasMap.draw()
                self.MapfigMap.canvas.SetFocus()
            else:
                self.plot_void()
                
    def hasMissingPoints(self):
        return self.hasMissingPoint(0) or self.hasMissingPoint(1)

    def hasMissingPoint(self, side):
        if self.store_supp is None:
            return False
        return self.store_supp["has_miss_points"][side]

    def additionalElements(self):
        
        flags = wx.ALIGN_CENTER | wx.ALL # | wx.EXPAND

        self.buttons = []
        self.buttons.extend([{"element": wx.Button(self.panel, wx.NewId(), size=(self.butt_w,-1), label="Expand"),
                             "function": self.OnExpandSimp},
                            {"element": wx.Button(self.panel, wx.NewId(), size=(self.butt_w,-1), label="Simplify LHS"),
                             "function": self.OnSimplifyLHS},
                            {"element": wx.Button(self.panel, wx.NewId(), size=(self.butt_w,-1), label="Simplify RHS"),
                             "function": self.OnSimplifyRHS}])
        for i in range(len(self.buttons)):
            self.buttons[i]["element"].SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        ##############################################
        add_boxB = wx.BoxSizer(wx.HORIZONTAL)
        add_boxB.AddSpacer((self.getSpacerWn()/2.,-1))

        add_boxB.Add(self.buttons[1]["element"], 0, border=1, flag=flags)
        add_boxB.AddSpacer((self.getSpacerWn(),-1))
        
        add_boxB.Add(self.buttons[2]["element"], 0, border=1, flag=flags)
        add_boxB.AddSpacer((self.getSpacerWn(),-1))
        
        add_boxB.Add(self.buttons[0]["element"], 0, border=1, flag=flags)
        add_boxB.AddSpacer((self.getSpacerWn()/2.,-1))

        #return [add_boxbis, add_box]
        return [add_boxB]


    def OnPick(self, event):
        if event.mouseevent.button in self.act_butt:
            gid_parts = event.artist.get_gid().split(".")
    #def sendOtherPick(self, gid_parts):
            if gid_parts[-1] == "T":
                pp = gid_parts[0].split(":")
                if len(pp) == 3:
                    side, node, onoff = map(int, pp)
                    if self.trees[side] is not None and self.trees[side].hasNode(node):
                        if onoff == -1:
                            self.removeBranchQ(side, node)
                        else:
                            self.addBranchQ(side, node)
            elif gid_parts[-1] == "S":
                self.simplify(int(gid_parts[0]))

    def removeBranchQ(self, side, node):
        if self.trees[side].isLeafInNode(node):
            bidd = self.trees[side].getNodeLeaf(node)
            qu = self.queries[side].copy()
            qu.buk.pop(bidd)                        
            if qu != self.queries[side]:
                for n in self.trees[side].getLeaves():
                    if self.trees[side].getNodeLeaf(n) > bidd:
                        self.trees[side].setNodeLeaf(n, self.trees[side].getNodeLeaf(n)-1)
                self.trees[side].setNodeLeaf(node, -1)
                self.updateQuery(side, query=qu, update_trees=False)

    def addBranchQ(self, side, node):
        if self.trees[side].isLeafOutNode(node):
            buk = self.trees[side].getBranchQuery(node)
            qu = self.queries[side].copy()
            bid = qu.appendBuk(buk)
            if qu != self.queries[side]:
                self.trees[side].setNodeLeaf(node, bid)
                self.updateQuery(side, query=qu, update_trees=False)


    def OnSimplifyLHS(self, event):
        if self.okTrees():
            self.simplify(0)
    def OnSimplifyRHS(self, event):
        if self.okTrees():
            self.simplify(1)
    def simplify(self, side):
        qu = self.trees[side].getSimpleQuery()
        self.updateQuery(side, query=qu, force=True)

    def getCoordsXY(self, idp):
        return []            
    def getCoordsXYA(self, idp):
        v = self.store_supp["mat"][idp]
        pi = numpy.where(self.store_supp["parts"][idp,:])[0][0]
        pl = numpy.sum(self.store_supp["parts"][:idp,pi]*(self.store_supp["mat"][:idp]==v))
        _, points, nb, ppos = self.store_supp["pos"][(v, pi)]
        bott, top = ppos[0]
        center = bott + (top-bott)*pl/float(nb)

        return (self.all_width+self.margins_sides, center)
    
    def drawEntity(self, idp, fc, ec, sz=1, zo=5, dsetts={}):
        v = self.store_supp["mat"][idp]
        pi = numpy.where(self.store_supp["parts"][idp,:])[0][0]
        pl = numpy.sum(self.store_supp["parts"][:idp,pi]*(self.store_supp["mat"][:idp]==v))
        _, points, nb, ppos = self.store_supp["pos"][(v, pi)]
        bott, top = ppos[0]
        center = bott + (top-bott)*pl/float(nb)

        lines = []
        for l in ppos[1:]:
            ff = numpy.sign(l[0])*self.flat_space
            lines.extend(self.axe.plot((l[0], ff, 0), (l[1], center, center), color=fc, linewidth=1, zorder=zo))
        return lines

    def hasDotsReady(self):
        return self.store_supp is not None

    
    def drawAnnotation(self, xy, ec, tag, xytext=(-10, 15)):
        lines = []
        lines.extend(self.axe.plot((self.flat_space, xy[0]), (xy[1], xy[1]), color=ec, linewidth=1, alpha=0.5))
        lines.extend(self.axe.plot((self.flat_space, xy[0]), (xy[1], xy[1]), color=self.getColorHigh(), linewidth=1, alpha=0.3))
        
        lines.append(GView.drawAnnotation(self, xy, ec, tag, xytext))
        return lines

    def inCapture(self, event):
        return self.okTrees() and event.inaxes == self.axe and numpy.abs(event.xdata) < self.flat_space and event.ydata > self.height_inter[0] and event.ydata < self.height_inter[1]
               
    def getLidAt(self, x, y):
        pp, rp = self.getRPPoint(y)
        if pp is not None:
            # print "LID", self.store_supp["lids"][pp][rp], pp, rp, len(self.store_supp["lids"][pp])
            return self.store_supp["lids"][pp][rp]


    def getRPPoint(self, y):
        ### Get the code part and line rank for position y
        if self.store_supp is not None and "pmap" in self.store_supp:
            pmap = self.store_supp["pmap"]
            i = 0
            while i < len(pmap) and y > pmap[i][0]:
                i += 1
            if i < len(pmap) and pmap[i][-1] == 1:
                pp = pmap[i][1]
                return pp, min(int(self.store_supp["pos"][pp][2]*(y - self.store_supp["pos"][pp][3][0][0])/(self.store_supp["pos"][pp][3][0][1] - self.store_supp["pos"][pp][3][0][0])), self.store_supp["pos"][pp][2]-1)
            else:
                if i < len(pmap)-1 and y + self.margin_hov > pmap[i][0] and pmap[i+1][-1] == 1:
                    return pmap[i+1][1], 0

                elif i > 0 and y - self.margin_hov <= pmap[i-1][0] and pmap[i-1][-1] == 1:
                    pp = pmap[i-1][1]
                    return pp, self.store_supp["pos"][pp][2]-1
        return None, 0
