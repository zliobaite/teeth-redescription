from __future__ import unicode_literals
import wx
### from wx import ALIGN_CENTER, ALL, EXPAND, HORIZONTAL, ID_ANY, SL_HORIZONTAL, VERTICAL
### from wx import EVT_BUTTON, EVT_SCROLL_THUMBRELEASE, FONTFAMILY_DEFAULT, FONTSTYLE_NORMAL, FONTWEIGHT_NORMAL
### from wx import BoxSizer, Button, DefaultPosition, Font, Slider, StaticText

import numpy
# The recommended way to use wx with mpl is with the WXAgg
# backend. 
# import matplotlib
# matplotlib.use('WXAgg')
import matplotlib.transforms as mtransforms
import scipy.spatial.distance
import scipy.cluster

from ..reremi.classRedescription import Redescription
from ..reremi.classData import BoolColM, CatColM, NumColM
from ..reremi.classSParts import SSetts
from classGView import GView
from classInterObjects import ResizeableRectangle, DraggableRectangle

#### TODO: label on slide rectangle for categories seems broken
#### Recongnize numerical categories?

import pdb

def shuffle_ids(inl, i, cc):
    ii = (7*cc+8*i+1) % len(inl)
    if cc % 2:
        dt = numpy.hstack([inl,inl])[ii:(len(inl)+ii)]
    else:
        dt = numpy.hstack([inl,inl])[(len(inl)+ii):ii:-1]
    tmp = shuffle_order(dt)

    iii = (11*cc+3*i+1) % len(inl)
    ddt = numpy.array(range(len(inl)), dtype=numpy.int)
    if i % 2:
        ddt = numpy.hstack([ddt,ddt])[iii:(len(inl)+iii)]
    else:
        ddt = numpy.hstack([ddt,ddt])[(len(inl)+iii):iii:-1]

    dtmp = shuffle_order(ddt)
    ttt = tmp[dtmp]
    # print "ORD:", ii, i, cc, len(tmp), ttt[:10]
    # pdb.set_trace()
    return ttt

def shuffle_order(ids):
    scores = [max([ii-1 for ii,vv in enumerate(bin(v)) if vv!='1']) for v in range(len(ids))]
    vs = numpy.unique(scores)
    if vs.shape[0] == len(ids):
        return ids[numpy.argsort(scores)]

    ovs = shuffle_order(vs)
    return numpy.hstack([shuffle_order(ids[numpy.where(scores==v)[0]]) for v in ovs])

def assignBlockOrd(sorting_samples, subids, nb_clusters, scaled_m, v=0, i=0, nbb=1):
    if subids.shape[0] < 2:
        return
    d = scipy.spatial.distance.pdist(scaled_m[:,subids].T)
    Z = scipy.cluster.hierarchy.linkage(d)
    T = scipy.cluster.hierarchy.fcluster(Z, nb_clusters, criterion="maxclust")        
    for cc in numpy.unique(T):
        ci = shuffle_ids(numpy.where(T==cc)[0], i, cc)
        sorting_samples[subids[ci]] = -0.1*v+float(i)/nbb+10*numpy.arange(1., ci.shape[0]+1)

def getSamplingOrd(scaled_m, pos_axis, nb_clusters, max_group):
    sorting_samples = numpy.zeros(scaled_m[0,:].shape)
    left_over = []
    for v in numpy.unique(scaled_m[pos_axis,:]):
        ids = numpy.where(scaled_m[pos_axis,:]==v)[0]
        if ids.shape[0] < nb_clusters:
            sorting_samples[ids] = -0.1*v
        else:
            block_ft = [i*max_group for i in range(ids.shape[0]/max_group+1)]+[ids.shape[0]]
            if (block_ft[-1] - block_ft[-2]) < 3 and block_ft[-2] > 0:
                ### if the last block is not the first and contains less than 3 elements, merge with previous
                block_ft.pop(-2)
            if (block_ft[-1] - block_ft[-2]) < max_group/3.:
                ### if the last block contains less than a third of a normal, group with left-overs
                left_over.extend(ids[block_ft[-2]:])
                block_ft.pop(-1)
            nb_blocks = len(block_ft) - 1
            for i in range(nb_blocks):
                assignBlockOrd(sorting_samples, ids[block_ft[i]:block_ft[i+1]], nb_clusters, scaled_m, v, i, nb_blocks)
    assignBlockOrd(sorting_samples, numpy.array(left_over), nb_clusters, scaled_m, v)
    sampling_ord = numpy.argsort(sorting_samples)
    return sampling_ord

class ParaView(GView):

    TID = "PC"
    SDESC = "Pa.Co."
    ordN = 2
    title_str = "Parallel Coordinates"
    typesI = "vr"

    rect_halfwidth = 0.05
    rect_alpha = 0.7
    rect_color = "0.7"
    rect_ecolor = "0.3"

    org_spreadL = 0.49 #(2/3.-0.5)
    org_spreadR = 0.49
    flat_space = 0.06
    maj_space = 0.05
    max_group_clustering = 2**8
    nb_clusters = 5
    margins_sides = 0.05
    margins_tb = 0.05
    margin_hov = 0.01
    missing_yy = -0.1
    missing_w = -0.05

    ann_xy = (10,0)
    
    def __init__(self, parent, vid, more=None):
        self.reps = set()
        self.current_r = None
        self.prepared_data = {}
        self.sld = None
        self.ri = None
        self.ticks_ann = []
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
            red.setRestrictedSupp(self.getParentData())
            self.suppABCD = red.supports().getVectorABCD()
            self.current_r = red
            self.updateText(red)
            self.updateMap()
            return red

    def updateQuery(self, sd=None, query=None, force=False, upAll=True):
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
            red.setRestrictedSupp(self.getParentData())
            self.suppABCD = red.supports().getVectorABCD()
            self.current_r = red
            if upAll:
                self.updateText(red)
                self.makeMenu()
                self.sendEditBack(red)
            self.updateMap()
            return red
        else: ### wrongly formatted query, revert
            for side in [0,1]:
                self.updateQueryText(self.queries[side], side)
        return None
        
    def getCanvasConnections(self):
        return [('key_press_event', self.key_press_callback),
                ('button_press_event', self.on_press),
                ('button_release_event', self.on_release),
                ('motion_notify_event', self.on_motion_all),
                ('axes_leave_event', self.on_axes_out),
                ('draw_event', self.on_draw)]


    def prepareData(self, lits, draw_ppos=None):
        
        pos_axis = len(lits[0])
        
        ranges = self.updateRanges(lits)
        
        side_cols = []
        lit_str = []
        for side in [0,1]:
            for l, dets in lits[side]:
                side_cols.append((side, l.colId()))
                lit_str.append(self.getParentData().getNames(side)[l.colId()])
                # lit_str.append("v%d" % l.colId())
        side_cols.insert(pos_axis, None)

        if self.prepared_data.get("side_cols", None) != side_cols:
            precisions = [10**numpy.floor(numpy.log10(self.getParentData().col(sc[0], sc[1]).minGap())) for sc in side_cols if sc is not None]

            precisions.insert(pos_axis, 1)
            precisions = numpy.array(precisions)
        
            mat, details, mcols = self.getParentData().getMatrix(nans=numpy.nan)
            mcols[None] = -1
            cids = [mcols[sc] for sc in side_cols]
            if draw_ppos is not None:
                data_m = numpy.vstack([mat, draw_ppos[self.suppABCD]])[cids]
            else:
                data_m = numpy.vstack([mat, self.suppABCD])[cids]

            limits = numpy.vstack([numpy.nanmin(data_m, axis=1),
                                   numpy.nanmax(data_m, axis=1), precisions, numpy.zeros(precisions.shape)])
            denoms = limits[1,:]-limits[0,:]
            denoms[denoms==0] = 1.
            scaled_m = numpy.vstack([(data_m[i,:]-limits[0,i])/denoms[i] for i in range(data_m.shape[0])])

            ### spreading lines over range
            pos_lids = self.getPos(scaled_m, data_m, limits, denoms, pos_axis)

            qcols = [l[0] for l in lits[0]]+[None]+[l[0] for l in lits[1]]
            xlabels = lit_str
            xticks = [x for x,v in enumerate(side_cols)]# if v is not None]
            lit_str.insert(pos_axis, None)
            ycols = [-1]
            xs = [-1]
            for i in range(len(side_cols)):
                ycols.extend([i,i])
                xs.extend([i-self.flat_space, i+self.flat_space])
            ycols.append(-2)
            xs.append(len(side_cols))

            #### ORDERING LINES FOR DETAILS SUBSAMPLING BY GETTING CLUSTERS
            sampling_ord = getSamplingOrd(scaled_m, pos_axis, self.nb_clusters, self.max_group_clustering)
            return {"pos_axis": pos_axis, "N": data_m.shape[1],
                    "side_cols": side_cols, "qcols": qcols, "lits": lits,
                    "xlabels": xlabels, "xticks": xticks, "ycols": ycols, "xs": xs,
                    "limits": limits, "ranges": ranges, "sampling_ord": sampling_ord,
                    "data_m": data_m, "scaled_m": scaled_m, "pos_lids": pos_lids}

        else:
            limits = self.prepared_data["limits"].copy()
            data_m = self.prepared_data["data_m"].copy()
            scaled_m = self.prepared_data["scaled_m"].copy()

            if draw_ppos is not None:
                data_m[pos_axis,:] = numpy.array([draw_ppos[self.suppABCD]])
            else:
                data_m[pos_axis,:] = numpy.array(self.suppABCD)

            ### test whether support changed
            if numpy.sum(data_m[pos_axis,:] != self.prepared_data["data_m"][pos_axis,:]) > 0:
                limits[:, pos_axis] = numpy.array([numpy.nanmin(data_m[pos_axis,:]), numpy.nanmax(data_m[pos_axis,:]), 1, 0])
                denoms = numpy.ones(limits[1,:].shape)
                denoms[pos_axis] = limits[1,pos_axis]-limits[0,pos_axis]
                if denoms[pos_axis] == 0:
                    scaled_m[pos_axis,:] = (data_m[pos_axis,:]-limits[0,pos_axis])
                else:
                    scaled_m[pos_axis,:] = (data_m[pos_axis,:]-limits[0,pos_axis])/denoms[pos_axis]

                update_pos = [pos_axis]
                pos_lids = self.prepared_data["pos_lids"].copy()
                tmp_pos_lids = self.getPos(scaled_m, data_m,
                                           limits, denoms, pos_axis, update_pos)
                for i, j in enumerate(update_pos):
                    pos_lids[j,:] = tmp_pos_lids[i,:]
                return {"lits": lits,
                        "limits": limits, "ranges": ranges,
                        "data_m": data_m, "scaled_m": scaled_m, "pos_lids": pos_lids}
            else:
                return {"lits": lits, "ranges": ranges}



    def updateRanges(self, lits):
        ranges = []
        for side in [0,1]:
            for l, dets in lits[side]:
                if l.typeId() == BoolColM.type_id:                    
                    ranges.append([self.getParentData().col(side, l.colId()).numEquiv(r)
                                   for r in [dets[0][-1], dets[0][-1]]])
                else:
                    ranges.append([self.getParentData().col(side, l.colId()).numEquiv(r)
                                   for r in l.valRange()])
        ranges.insert(len(lits[0]), [None, None])
        return ranges


    def literalsEffect(self, red):
        lits = [[],[]]
        map_q = {}
        org_abcd = numpy.array(red.supports().getVectorABCD())
        for side in [0,1]:
            for (ls, q) in red.queries[side].minusOneLiteral():
                queries = [red.queries[0], red.queries[1]]
                queries[side] = q
                elem = red.queries[side].getBukElemAt(ls)
                r = Redescription.fromQueriesPair(queries, self.getParentData())
                direct = 0
                if len(r.supp(side)) > len(red.supp(side)):
                    direct = -1
                elif len(r.supp(side)) < len(red.supp(side)):
                    direct = 1
                r_abcd = numpy.array(r.supports().getVectorABCD())
                diff = numpy.where(org_abcd != r_abcd)[0]
                subs = {}
                for  d in diff:
                    tx = (r_abcd[d], org_abcd[d])
                    if tx not in subs:
                        subs[tx] = set()
                    subs[tx].add(d)
                lsubs = dict([(k,len(v)) for (k,v) in subs.items()])
                lits[side].append((elem, [(ls, False, not elem.isNeg()),]))
                map_q[(side, ls)] = {"query": q, "acc": r.getAcc(), "subsets": subs, "lsubsets": lsubs, "direct": direct}
            lits[side].sort(key=lambda x:x[1])
        return lits, map_q
    
    def updateMap(self):
        """ Redraws the map
        """
        if self.current_r is not None:
            self.clearPlot()
            
            red = self.current_r
            draw_settings = self.getDrawSettings()

            self.dots_draws = self.prepareEntitiesDots()

            #### Contribs of literals
            if self.getLitContribOn():
                lits, map_q = self.literalsEffect(red)
            else:
                lits = [sorted(red.queries[side].listLiteralsDetails().items(), key=lambda x:x[1]) for side in [0,1]]
                map_q = None

            
            self.prepared_data.update(self.prepareData(lits, draw_ppos = draw_settings["draw_ppos"]))

            ### SAMPLING ENTITIES
            t = 0.1
            if self.sld is not None:
                td = self.sld.GetValue()
                t = (5*(td/100.0)**8+1*(td/100.0)**2)/6
            self.reps = list(self.prepared_data["sampling_ord"][:int(t*self.prepared_data["N"])])
            self.reps.sort(key=lambda x: draw_settings["draw_pord"][self.suppABCD[x]])
            #self.reps = set(self.prepared_data["sampling_ord"])

            ### SELECTED DATA
            selected = self.getUnvizRows()
            # selected = self.getParentData().selectedRows()
            if self.sld_sel is not None and len(selected) > 0:
                selp = self.sld_sel.GetValue()/100.0
                self.dots_draws["fc_dots"][numpy.array(list(selected)), -1] *= selp
                self.dots_draws["ec_dots"][numpy.array(list(selected)), -1] *= selp
                self.dots_draws["lc_dots"][numpy.array(list(selected)), -1] *= selp

            ### PLOTTING
            ### Lines
            for r in self.reps:
                # if numpy.sum(~numpy.isfinite(self.prepared_data["data_m"][:,r])) == 0:
                if self.dots_draws["lc_dots"][r,-1] > 0:
                    self.drawEntity(r, fc=self.getPlotColor(r, "lc")) #, zo=self.getPlotProp(r, "zord"))

            ### Bars slidable/draggable rectangles
            rects_drag = {}
            rects_rez = {}
            for i, rg in enumerate(self.prepared_data["ranges"]):
                if rg[0] is not None:
                    bds = self.getYsforRange(i, rg)
                    rects = self.axe.bar(i-self.rect_halfwidth, bds[1]-bds[0], 2*self.rect_halfwidth, bds[0],
                                         edgecolor=self.rect_ecolor, color=self.rect_color, alpha=self.rect_alpha, zorder=10)

                    if self.prepared_data["qcols"][i] is not None:
                        if self.prepared_data["qcols"][i].typeId() == NumColM.type_id:
                            rects_rez[i] = rects[0]
                        elif self.prepared_data["qcols"][i].typeId() == CatColM.type_id or \
                                 self.prepared_data["qcols"][i].typeId() == BoolColM.type_id:   
                            rects_drag[i] = rects[0]

            # self.annotation = self.axe.annotate("", xy=(0.5, 0.5), xytext=(0.5,0.5), backgroundcolor="w")
            self.drs = []
            self.ri = None
            for rid, rect in rects_rez.items():
                dr = ResizeableRectangle(rect, rid=rid, callback=self.receive_release, \
                                                  pinf=self.getPinvalue, annotation=None) #self.annotation)
                self.drs.append(dr)

            for rid, rect in rects_drag.items():
                dr = DraggableRectangle(rect, rid=rid, callback=self.receive_release, \
                                                  pinf=self.getPinvalue, annotation=None) #self.annotation)
                self.drs.append(dr)

            if self.getParentData().hasMissing():
                bot = self.missing_yy-self.margins_tb
            else:
                bot = 0-self.margins_tb

            # #### fit window size HERE FIT
            # extent = [numpy.min(self.prepared_data["xticks"])-1, numpy.max(self.prepared_data["xticks"])+1,
            #           self.missing_yy-self.margins_tb, 0]
            # self.axe.fill([extent[0], extent[1], extent[1], extent[0]],
            #               [extent[2], extent[2], extent[3], extent[3]],
            #               color='1', alpha=0.66, zorder=5, ec="1" )
            height = 1.

            if map_q is not None:
                for pos in range(len(self.prepared_data["ranges"])):
                    self.makeEffPlot(pos, lits, map_q, draw_settings)
                height += 0.5

            ### Labels
            self.axe.set_xticks(self.prepared_data["xticks"])
            self.axe.set_xticklabels(["" for i in self.prepared_data["xlabels"]]) #, rotation=20, ha="right")
            side = 0
            self.ticks_ann = []
            for lbi, lbl in enumerate(self.prepared_data["xlabels"]):
                if lbl is None:
                    side = 1
                else:
                    tt = self.axe.annotate(lbl,
                                           xy =(self.prepared_data["xticks"][lbi], bot),
                                           xytext =(self.prepared_data["xticks"][lbi]+0.2, bot-0.5*self.margins_tb), rotation=25,
                                           horizontalalignment='right', verticalalignment='top', color=draw_settings[side]["color_l"],
                                           bbox=dict(boxstyle="round", fc="w", ec="none", alpha=0.7), zorder=15
                                           )
                    self.ticks_ann.append(tt)
                    
                    self.axe.annotate(lbl,
                                      xy =(self.prepared_data["xticks"][lbi], bot),
                                      xytext =(self.prepared_data["xticks"][lbi]+0.2, bot-0.5*self.margins_tb), rotation=25,
                                      horizontalalignment='right', verticalalignment='top', color=draw_settings[side]["color_l"],
                                      bbox=dict(boxstyle="round", fc=draw_settings[side]["color_l"], ec="none", alpha=0.3), zorder=15
                                      )

            # borders_draw = [numpy.min(self.prepared_data["xticks"])-1-self.margins_sides, bot,
            #                 numpy.max(self.prepared_data["xticks"])+1+self.margins_sides, 1+self.margins_tb]

            self.axe.set_xlim([numpy.min(self.prepared_data["xticks"])-1-self.margins_sides,
                               numpy.max(self.prepared_data["xticks"])+1+self.margins_sides])
            self.axe.set_ylim([bot,height+self.margins_tb])            
            
            self.updateEmphasize(review=False)
            self.MapcanvasMap.draw()
            self.MapfigMap.canvas.SetFocus()

    def makeEffPlot(self, pos, lits, map_q, draw_settings):
        pos_axis = self.prepared_data["pos_axis"]
        ty, tx = (1/8., 1/8.) #(2.*len(self.prepared_data["ranges"]))
        side = 0
        idx = pos
        if pos == pos_axis:
            return 
        if pos > pos_axis:
            side = 1
            idx -= (pos_axis+1)
        if (side, lits[side][idx][1][0][0]) not in map_q:
            pdb.set_trace()
            return
        
        corners = numpy.vstack([tx*numpy.array([-1., 1., 0., 0.])+pos, ty*numpy.array([0., 0., 1., -1.])+1.25]).T        
        dets = map_q[(side, lits[side][idx][1][0][0])]
        if side == 0:
            arrow = [(SSetts.alpha, SSetts.gamma), (SSetts.delta, SSetts.beta)]
        else:
            arrow = [(SSetts.beta, SSetts.gamma), (SSetts.delta, SSetts.alpha)]
        if dets["direct"] > 0:
            arrow = [arrow[1], arrow[0]]
            

        for i in arrow[0]+arrow[1]:
            self.axe.plot(corners[i,0], corners[i,1], color=draw_settings[i]["color_l"], marker="o")

        a_xy = numpy.mean(corners[arrow[0],:], axis=0)
        a_dxy = numpy.mean(corners[arrow[1],:], axis=0) - numpy.mean(corners[arrow[0],:], axis=0)
        if dets["direct"] != 0:
            head_width = 0.25*numpy.sqrt(a_dxy[0]**2+a_dxy[1]**2)/1.25
            self.axe.arrow(a_xy[0], a_xy[1], a_dxy[0], a_dxy[1], color="k", length_includes_head=True, head_width=head_width)
        else:
            self.axe.plot([a_xy[0], a_xy[0]+a_dxy[0]], [a_xy[1], a_xy[1]+a_dxy[1]], '-k')

        for si, ss in enumerate([(arrow[0][0],arrow[1][0]), (arrow[0][1],arrow[1][1])]):
            xy = (numpy.mean(corners[ss,0]), numpy.mean(corners[ss,1]))
            ha = "left"
            if si == side:
                ha = "right"
                
            self.axe.annotate("%d" % dets["lsubsets"].get(ss, 0), xy, ha=ha, va="center")
                #pdb.set_trace()
        self.axe.annotate("J = %.3f" % dets["acc"],  (corners[SSetts.gamma,0], corners[SSetts.gamma,1]+0.05), ha="center", va="bottom")

            
    def on_press(self, event):
        if event.inaxes != self.axe: return
        i = 0
        while self.ri is None and i < len(self.drs):
            contains, attrd = self.drs[i].contains(event)
            if contains:
                self.ri = i
            i+=1
        if self.ri is not None:
            self.drs[self.ri].do_press(event)

    def on_release(self, event):
        if event.inaxes != self.axe: return
        if self.ri is not None:
            self.drs[self.ri].do_release(event)
        else:
            self.on_click(event)
        self.ri = None
        
    def on_axes_out(self, event):
        if self.ri is not None:
            self.drs[self.ri].do_release(event)
        self.ri = None

    def on_motion_all(self, event):
        if event.inaxes == self.axe and self.ri is not None:
            self.drs[self.ri].do_motion(event)
        else:
            self.on_motion(event)

    def getVforY(self, rid, y):
        return self.prepared_data["limits"][0,rid] + y*(self.prepared_data["limits"][1,rid]-self.prepared_data["limits"][0,rid])
    def getYforV(self, rid, v, direc=0):
        return (v-self.prepared_data["limits"][0,rid]+direc*0.5*self.prepared_data["limits"][-1,rid])/(self.prepared_data["limits"][1,rid]-self.prepared_data["limits"][0,rid])
    def getYsforRange(self, rid, range):
        return [self.getYforV(rid, range[0], direc=-1), self.getYforV(rid, range[1], direc=1)]

    def getPinvalue(self, rid, b, direc=0):
        if "qcols" not in self.prepared_data or self.prepared_data["qcols"][rid] is None:
            return 0
        elif self.prepared_data["qcols"][rid].typeId() == NumColM.type_id:
            v = self.getVforY(rid, b)
            prec = -numpy.log10(self.prepared_data["limits"][2, rid])
            #tmp = 10**-prec*numpy.around(v*10**prec)
            if direc < 0:
                tmp = 10**-prec*numpy.ceil(v*10**prec)
            elif direc > 0:
                tmp = 10**-prec*numpy.floor(v*10**prec)
            else:
                tmp = numpy.around(v, prec)            
            if tmp >= self.prepared_data["limits"][1, rid]:
                tmp = float("Inf")
            elif tmp <= self.prepared_data["limits"][0, rid]:
                tmp = float("-Inf")
            return tmp
        elif self.prepared_data["qcols"][rid].typeId() == CatColM.type_id or \
                 self.prepared_data["qcols"][rid].typeId() == BoolColM.type_id:
            v = int(round(b*(self.prepared_data["limits"][1, rid]-self.prepared_data["limits"][0,rid])+self.prepared_data["limits"][0, rid]))
            if v > self.prepared_data["limits"][1, rid]:
                v = self.prepared_data["limits"][1, rid]
            elif v < self.prepared_data["limits"][0, rid]:
                v = self.prepared_data["limits"][0, rid]
            side = 0
            if self.prepared_data["pos_axis"] < rid:
                side = 1
            c = self.getParentData().col(side, self.prepared_data["qcols"][rid].colId())
            if c is not None:
                return c.getCatFromNum(v)
            
    def receive_release(self, rid, rect):
        if self.current_r is not None and "pos_axis" in self.prepared_data:
            pos_axis = self.prepared_data["pos_axis"]
            side = 0
            pos = rid
            if rid > pos_axis:
                side = 1
                pos -= (pos_axis+1)
            copied = self.current_r.queries[side].copy()
            ### HERE RELEASE
            l, dets = self.prepared_data["lits"][side][pos]
            alright = False
            upAll = False
            if l.typeId() == NumColM.type_id:
                ys = [(rect.get_y(), -1), (rect.get_y() + rect.get_height(), 1)]
                bounds = [self.getPinvalue(rid, b, direc) for (b, direc) in ys]
                upAll = (l.valRange() != bounds)
                if upAll:
                    for path, comp, neg in dets:
                        ll = copied.getBukElemAt(path)
                        ll.getTerm().setRange(bounds)
                        if comp:
                            ll.flip()
                alright = True
            elif l.typeId() == CatColM.type_id:
                cat = self.getPinvalue(rid, rect.get_y() + rect.get_height()/2.0, 1)
                if cat is not None:
                    upAll = (l.getCat() != cat)
                    if upAll:
                        for path, comp, neg in dets:
                            copied.getBukElemAt(path).getTerm().setRange(cat)
                    alright = True
            elif l.typeId() == BoolColM.type_id:
                bl = self.getPinvalue(rid, rect.get_y() + rect.get_height()/2.0, 1)
                if bl is not None:
                    upAll = bl != dets[0][-1]
                    if upAll:
                        for path, comp, neg in dets:
                            copied.getBukElemAt(path).flip()
                    alright = True
            if alright:
                self.prepared_data["ranges"][rid] = [self.getParentData().col(side, l.colId()).numEquiv(r) for r in l.valRange()]
                if upAll:
                    self.current_r = self.updateQuery(side, copied, force=True, upAll=upAll)
                else:
                    self.updateMap()

    def getCoordsXY(self, idp):
        return (self.prepared_data["xs"], self.prepared_data["pos_lids"][self.prepared_data["ycols"],idp])
    def getCoordsXYA(self, idp):
        return (self.prepared_data["xs"][-1]+self.margins_sides, self.prepared_data["pos_lids"][self.prepared_data["ycols"][-1],idp])
            
    def drawEntity(self, idp, fc, ec=None, sz=1, zo=4, dsetts={}):
        x, y = self.getCoordsXY(idp)
        return self.axe.plot(x, y, color=fc, linewidth=1, zorder=zo)
        
    def additionalElements(self):
        t = self.parent.dw.getPreferences()
        
        flags = wx.ALIGN_CENTER | wx.ALL # | wx.EXPAND

        self.buttons = []
        self.buttons.append({"element": wx.Button(self.panel, size=(self.butt_w,-1), label="Expand"),
                             "function": self.OnExpandSimp})
        self.buttons[-1]["element"].SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        
        self.sld = wx.Slider(self.panel, -1, t["details_level"]["data"], 0, 100, wx.DefaultPosition, (self.sld_w, -1), wx.SL_HORIZONTAL)
        self.sld_sel = wx.Slider(self.panel, -1, 10, 0, 100, wx.DefaultPosition, (self.sld_w, -1), wx.SL_HORIZONTAL)

        ##############################################
        add_boxB = wx.BoxSizer(wx.HORIZONTAL)
        add_boxB.AddSpacer((self.getSpacerWn()/2.,-1))

        v_box = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self.panel, wx.ID_ANY,u"- opac. disabled +")
        label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        v_box.Add(label, 0, border=1, flag=flags) #, userData={"where": "*"})
        v_box.Add(self.sld_sel, 0, border=1, flag=flags) #, userData={"where":"*"})
        add_boxB.Add(v_box, 0, border=1, flag=flags)
        add_boxB.AddSpacer((self.getSpacerWn(),-1))

        v_box = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self.panel, wx.ID_ANY, "-        details       +")
        label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        v_box.Add(label, 0, border=1, flag=flags) #, userData={"where": "*"})
        v_box.Add(self.sld, 0, border=1, flag=flags) #, userData={"where": "*"})
        add_boxB.Add(v_box, 0, border=1, flag=flags)   

        add_boxB.AddSpacer((self.getSpacerWn(),-1))
        add_boxB.Add(self.buttons[-1]["element"], 0, border=1, flag=flags)

        add_boxB.AddSpacer((self.getSpacerWn()/2.,-1))
        
        #return [add_boxbis, add_box]
        return [add_boxB]


    def additionalBinds(self):
        self.MapredMapQ[0].Bind(wx.EVT_TEXT_ENTER, self.OnEditQuery)
        self.MapredMapQ[1].Bind(wx.EVT_TEXT_ENTER, self.OnEditQuery)
        for button in self.buttons:
            button["element"].Bind(wx.EVT_BUTTON, button["function"])
        self.sld.Bind(wx.EVT_SCROLL_THUMBRELEASE, self.OnSlide)
        self.sld_sel.Bind(wx.EVT_SCROLL_THUMBRELEASE, self.OnSlide)


    def OnSlide(self, event):
        self.updateMap()

    def getLidAt(self, x, y):
        axid = int(numpy.around(x))
        if "pos_lids" in self.prepared_data:
            rlid = numpy.argmin((self.prepared_data["pos_lids"][axid,self.reps]-y)**2)
            lid = self.reps[rlid]
            if abs(self.prepared_data["pos_lids"][axid,lid]-y) < self.margin_hov:
                return lid
        return None


    def getPos(self, scaled_m, data_m, limits, denoms, pos_axis, update_pos=None):
        N = data_m.shape[1]
        avgs = numpy.nanmean(numpy.vstack([scaled_m, numpy.zeros_like(scaled_m[0,:])]), axis=0)
        pos_lids = []
        do_all = False
        if update_pos is None:
            do_all = True
            update_pos = range(data_m.shape[0])
        for i in update_pos:
            idsNAN = list(numpy.where(~numpy.isfinite(scaled_m[i,:]))[0])
            nanvs = None
            if len(idsNAN) > 0:
                scaled_m[i,idsNAN] = self.missing_yy
                top, bot = self.missing_yy-len(idsNAN)*self.missing_w/N, \
                           self.missing_yy+len(idsNAN)*self.missing_w/N
                nanvs = numpy.linspace(top, bot, len(idsNAN))

            spreadv = numpy.zeros(data_m[i,:].shape)
            w = abs(limits[2,i])
            limits[0,i]-=0.5*w
            limits[1,i]+=0.5*w
            av_space = w - self.maj_space * denoms[i]
            if av_space > 0:
                limits[-1,i] = av_space
                ww = numpy.array([50, 10, 100])
                if scaled_m.shape[0] == 1:
                    pos_help = numpy.ones(scaled_m[i,:].shape)
                else:
                    if i == 0:
                        cc = [i+1, i+1, pos_axis]
                    elif i == data_m.shape[0]-1:
                        cc = [i-1, i-1, pos_axis]
                    else:
                        cc = [i-1, i+1, pos_axis]
                    pos_help = numpy.dot(ww, scaled_m[cc,:])+avgs
                
                vs = numpy.unique(scaled_m[i,:])
                for v in vs:
                    if v != self.missing_yy:
                        vids = list(numpy.where(scaled_m[i,:]==v)[0])
                        vids.sort(key=lambda x: pos_help[x])
                        top, bot = -len(vids)*av_space*0.5/N, len(vids)*av_space*0.5/N
                        spreadv[vids] += numpy.linspace(top, bot, len(vids))

            pos_lids.append((data_m[i,:]-limits[0,i] + spreadv)/(limits[1,i]-limits[0,i]))
            if nanvs is not None:
                pos_lids[-1][idsNAN] = nanvs

        if do_all:
            spreadL = numpy.zeros(data_m[i,:].shape)
            spreadL[numpy.argsort(pos_lids[0])] = numpy.linspace(0.5-self.org_spreadL, 0.5+self.org_spreadL, N)
            spreadR = numpy.zeros(data_m[i,:].shape)
            spreadR[numpy.argsort(pos_lids[-1])] = numpy.linspace(0.5-self.org_spreadR, 0.5+self.org_spreadR, N)

            pos_lids.extend([spreadR,spreadL])
        pos_lids = numpy.vstack(pos_lids)
        return pos_lids

        
    def on_draw(self, event):

        renderer1 = self.MapcanvasMap.get_renderer()
        llboxes = []
        for ll in self.ticks_ann:
            lbbox = ll.get_window_extent(renderer1)
            llboxes.append(lbbox.inverse_transformed(self.MapfigMap.transFigure))

        if len(llboxes) > 0:
            lcbbox = mtransforms.Bbox.union(llboxes)
            if 1.1*lcbbox.height > 0.1:
                self.MapfigMap.subplots_adjust(bottom=1.1*lcbbox.height)
            elif self.MapfigMap.subplotpars.bottom != 0.1:
                self.MapfigMap.subplots_adjust(bottom=0.1)
            if lcbbox.extents[0] < 0:
                self.MapfigMap.subplots_adjust(left=1.1*(self.MapfigMap.subplotpars.left-lcbbox.extents[0]))
            elif self.MapfigMap.subplotpars.left != 0.1:
                self.MapfigMap.subplots_adjust(left=0.1)
