import re
import wx
import numpy

import os.path, glob

from scipy.sparse.csgraph import shortest_path, minimum_spanning_tree, reconstruct_path
import scipy.spatial.distance
import scipy.misc
# The recommended way to use wx with mpl is with the WXAgg backend. 
# import matplotlib
# matplotlib.use('WXAgg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from classLView import LView

import pdb

WEDGES_POS_FILE = os.path.dirname(os.path.abspath(__file__))+"/wedges_pos_all.txt"
OFFSET = 0.5
INA = dict([(k,v) for (v,k) in enumerate(["r0", "r1", "alpha0", "alpha1", "flu"])])

def isAlphaIn(alpha, alpha0, alpha1):
    aa = alpha % 1
    return ((aa > alpha0) & (aa < alpha1)) | ((aa > alpha0+1) & (aa < alpha1+1))

def getXY(r, alpha):
    return (r*numpy.cos(alpha*2*numpy.pi), r*numpy.sin(alpha*2*numpy.pi))
def getRA(x, y):
    return (numpy.sqrt(x**2 + y**2), (numpy.arctan2(y, x)/(2*numpy.pi))%1)

def getEdgeX(r0, r1, alpha, reverse=False):
    tmp = (r0*numpy.cos(alpha*2*numpy.pi), r1*numpy.cos(alpha*2*numpy.pi))
    if reverse:
        return tmp[::-1]
    return tmp
def getEdgeY(r0, r1, alpha, reverse=False):
    tmp = (r0*numpy.sin(alpha*2*numpy.pi), r1*numpy.sin(alpha*2*numpy.pi))
    if reverse:
        return tmp[::-1]
    return tmp
def getArcX(r, alpha0, alpha1, increment, reverse=False):
    tmp = [r* numpy.cos(alpha*2*numpy.pi) for alpha in numpy.arange(alpha0, alpha1+.5*increment, increment)]
    if reverse:
        return tmp[::-1]
    return tmp
def getArcY(r, alpha0, alpha1, increment, reverse=False):
    tmp = [r* numpy.sin(alpha*2*numpy.pi) for alpha in numpy.arange(alpha0, alpha1+.5*increment, increment)]
    if reverse:
        return tmp[::-1]
    return tmp

def getPolyDots(data, increment):
    r0, r1, alpha0, alpha1 = (data[INA["r0"]], data[INA["r1"]], data[INA["alpha0"]], data[INA["alpha1"]])
    if r0 > 0:
        xx = getArcX(r0, alpha0, alpha1, increment) + getArcX(r1, alpha0, alpha1, increment, reverse=True)
        yy = getArcY(r0, alpha0, alpha1, increment) + getArcY(r1, alpha0, alpha1, increment, reverse=True)
    else:
        xx = getArcX(r1, alpha0, alpha1, increment)
        yy = getArcY(r1, alpha0, alpha1, increment)
    return numpy.array([xx, yy]).T 

def computeMapWedges(nbR):
    if nbR % 2 == 0:
        k = nbR + 1
    else:
        k = nbR
    if k not in [3,5,7]:
        return {}
        
    nbc = [int(scipy.misc.comb(k,i)) for i in range(k+1)] 
    lfold = k/2+1
    
    #### LEVELS 1 to 3
    lls = [[] for i in range(k+1)]
    lls[0].append(())
    
    last_odd = False
    #### Panning out
    for x0 in range(k):
        lls[1].append(tuple([x0]))
        if 2 < lfold:
            for jj, p in enumerate(range(1,k,2)[::-1]):
                x1 = (x0+p)%k
                lls[2].append((x0, x1))
                if 3 < lfold:
                    last_odd = True
                    x2s = []
                    if jj == 0:
                        x2s.append((x1+1)%k)
                    else:
                        x2s.append((x1+2)%k)
    
                    if jj < 2 or (jj == 2 and k%3 == 3 and x0%3 == 0): # (k/2-1):
                        x2s.append((x1+3)%k)
    
                    if jj < 3 and k > 7: # > (5+2) (k/2-1):
                        x2s.append((x1+5)%k)
                    lls[3].extend([(x0, x1, x2) for x2 in x2s])
    
    #### Equal levels
    for i, v in enumerate(lls[lfold-1]):
        if last_odd and ((i+1) % (nbc[lfold]/k) == 0):
            xx = (v[-1]+1)%k
        else:
            tmp = [x for x in lls[lfold-1][i-1] if x not in v]
            if len(tmp) == 1:
                xx = tmp[0]
            else:
                xx = -1
                print "Non singleton diff"
                pdb.set_trace()
        lls[lfold].append(tuple(list(v)+[xx]))
    
    #### Folding down
    for j in range(lfold+1, k):
        for i, v in enumerate(lls[j-1]):
            if i % (nbc[j-1]/k) < nbc[j]/k:
                tmp = [x for x in lls[j-1][i-1] if x not in v]
                if len(tmp) == 1:
                    xx = tmp[0]
                else:
                    xx = -1
                    print "Non singleton diff"
                    pdb.set_trace()
                lls[j].append(tuple(list(v)+[xx]))
    
    lls[-1].append(tuple(range(k)))

    llRs = lls
    if nbR != k:
        llRs = []
        for ll in lls:
            tmp = [ss for ss in ll if k-1 not in ss] # and f1 not in ss]
            if len(tmp) > 0:
                llRs.append(tmp)
    
    basisT = 2**nbR -1
    store = numpy.zeros((2**nbR, 3), dtype=int)
    for lli, lll in enumerate(llRs):
        for li, ll in enumerate(lll):
            code = basisT - sum([2**l for l in ll])
            store[code,:] = (lli, li, len(lll))
    return store

def makeMapWedges(keep):
    surplus = []
    nbR = len(keep)

    all_pos = numpy.loadtxt(WEDGES_POS_FILE, dtype=int)
    opts = numpy.unique(all_pos[:,0])
    if nbR not in opts:
        if nbR < min(opts):
            return [], keep, None, None
        else:
            surplus = keep[max(opts):]
            keep = keep[:max(opts)]
            nbR = len(keep)
            
    wedges_pos = all_pos[all_pos[:,0]==nbR,1:]
    nbc = [int(scipy.misc.comb(nbR,i)) for i in range(nbR+1)] 
    neighbors = makeNeighborsC(nbc)
    map_pos = dict([(tuple(wedges_pos[i,0:2]), i) for i in range(wedges_pos.shape[0])])
    nns = translateNeighs(neighbors, map_pos)
    return keep, surplus, wedges_pos, nns

def makeNeighborsC(nbc):
    map_neighs = {(0,0): {}}
    for ni in range(1, len(nbc)):
        for c in range(nbc[ni]):
            map_neighs[(ni, c)] = {(ni, (c-1)% nbc[ni]): -1, (ni, (c+1)% nbc[ni]): 1}
        if nbc[ni] < nbc[ni-1]:
            f, t = (ni, ni-1)
            lf, lt = (-2, 2)
        else:
            f, t = (ni-1, ni)
            lf, lt = (2,-2)

        tp = [(i-OFFSET)*float(nbc[t])/nbc[f] + OFFSET for i in range(nbc[f]+1)]
        collect = []
        for i in range(len(tp)-1):
            j = int(numpy.floor(tp[i]))
            while j < tp[i+1]:
                jm = j % nbc[t]
                map_neighs[(f,i)][(t,jm)] = lf
                map_neighs[(t,jm)][(f,i)] = lt
                collect.append((i,jm))
                j += 1
    return map_neighs

def translateNeighs(map_neighs, map_pos):
    return dict([(map_pos[k], dict([(map_pos[kk], vv) for (kk,vv) in vs.items()])) for (k, vs) in map_neighs.items()])

def getScoreEdgeDir(edge_type):
    return numpy.abs(edge_type)

def reduceRs(nbR, wedges_pos, neighbors, stats):
    center = 2**nbR -1
    lRs = []
    for ri in range(nbR):
        singleton = 2**ri
        cids = [cid for cid in range(wedges_pos.shape[0]) if numpy.bitwise_and(cid,singleton)]
        map_cids = dict([(v,k) for (k,v) in enumerate(cids)])
        filled = [k for cid, k in map_cids.items() if cid in stats or (cid == singleton)]
        mat = numpy.zeros((len(cids), len(cids)))
        for ci in range(len(cids)):
            for cj in range(ci):
                if cids[ci] in neighbors[cids[cj]]:
                    score = getScoreEdgeDir(neighbors[cids[cj]][cids[ci]])*(9*(cids[ci] not in stats or cids[cj] not in stats) + 1)
                    mat[cj, ci] = score
                    mat[ci,cj] = score

        dist_mat, pred = shortest_path(mat, return_predecessors=True)
        sp_tree = minimum_spanning_tree(dist_mat[:,filled][filled, :])
        edges_red = [(filled[e[0]], filled[e[1]])  for e in zip(*sp_tree.nonzero())]
        all_nodes = set()
        for edge_red in edges_red:
            path = [edge_red[1]]
            while path[-1] != edge_red[0]:
                path.append(pred[edge_red[0], path[-1]])
            all_nodes.update(path)
        bones = [cids[k] for k in all_nodes]
        contains1 = False
        for i in bones:
            if wedges_pos[i][0] == 1:
                contains1 = True
                continue
            for j,v in neighbors[i].items():
                if v == -2 and j not in bones and j in cids and wedges_pos[i][0] == 2:
                    bones.append(j)
                if numpy.abs(v) == 1 and j not in bones and j in cids:
                    nexte = [j]
                    while len(nexte) == 1:
                        bones.append(nexte[0])
                        nexte = [jj for (jj, vv) in neighbors[bones[-1]].items() if vv == v and jj not in bones and jj in cids]

        if contains1 and center not in bones:
            bones.append(center)
        ## print singleton, singleton in bones
        # lRs.append([cids[k] for k in all_nodes])
        lRs.append(bones)
        # lRs.append(cids)
    return lRs
        
def getEnveloppe(ri, cids, wedges_abs, neighbors):
    if len(cids) == 1:
        return [], [(wedges_abs[cids[0],INA["r1"]], 0, 1)]
    arcs = []
    edges = []
    for cid in cids:
        for nid in set(neighbors[cid].keys()).difference(cids):
            if neighbors[cid][nid] == -1:
                edges.append((wedges_abs[cid,INA["r0"]], wedges_abs[cid,INA["r1"]], wedges_abs[cid,INA["alpha0"]]))
            elif neighbors[cid][nid] == 1:
                edges.append((wedges_abs[cid,INA["r0"]], wedges_abs[cid,INA["r1"]], wedges_abs[cid,INA["alpha1"]]))
            else:
                if wedges_abs[cid,INA["flu"]] == -2:
                    arc_start = wedges_abs[nid,INA["alpha0"]]
                    arc_ends = wedges_abs[nid,INA["alpha1"]]
                elif wedges_abs[nid,INA["flu"]] == -2:
                    arc_start = wedges_abs[cid,INA["alpha0"]]
                    arc_ends = wedges_abs[cid,INA["alpha1"]]
                else:
                    off_cid, off_nid = (0, 0)
                    if wedges_abs[cid,INA["flu"]] == 1 and wedges_abs[nid,INA["flu"]] == -1:
                        off_cid = 1
                    elif wedges_abs[nid,INA["flu"]] == 1 and wedges_abs[cid,INA["flu"]] == -1:
                        off_nid = 1
                    arc_start = max(off_nid+wedges_abs[nid,INA["alpha0"]], off_cid+wedges_abs[cid,INA["alpha0"]])
                    arc_ends = min(off_nid+wedges_abs[nid,INA["alpha1"]], off_cid+wedges_abs[cid,INA["alpha1"]])
                if neighbors[cid][nid] == -2:
                    arcs.append((wedges_abs[cid,INA["r0"]], arc_start, arc_ends))
                elif neighbors[cid][nid] == 2:
                    arcs.append((wedges_abs[cid,INA["r1"]], arc_start, arc_ends))
    arcs.sort()
    i = 0
    while i < len(arcs)-1:
        if arcs[i][0] == arcs[i+1][0] and arcs[i][2] == arcs[i+1][1]:
            arcs[i] = (arcs[i][0], arcs[i][1], arcs[i+1][2])
            arcs.pop(i+1)
        else:
            i+=1
    return edges, arcs

class InterView(LView):

    cversion = 0
    TID = "INT"
    SDESC = "InterLViz"
    ordN = 0
    title_str = "InterTree View"
    typesI = "r"

    
    color_list = [(0.4, 0.165, 0.553), (0.949, 0.482, 0.216), (0.47, 0.549, 0.306), \
                  (0.925, 0.165, 0.224), (0.141, 0.345, 0.643), (0.965, 0.633, 0.267), \
                  (0.627, 0.118, 0.165), (0.878, 0.475, 0.686)]
    color_palet = {'before': (0.2,0.2,0.2),
                   'before_light': (0.2,0.2,0.2),
                   'add': (1,1,0.25),
                   'add_light': (1,1,0.25)}
    pick_sz = 5
    wait_delay = 300    

    def getCanvasConnections(self):
        return [('button_release_event', self.on_click)]
        
    def prepareDrawingElements(self, etor, keep, dists, wedges_pos, neighbors):
        """ Generate the elements for the visualization
        """
        elements = {}
        if len(keep) == 0:
            return elements
        
        ### decide ordering of the redescription around the circle
        order_seq = list(wedges_pos[[2**j for j in range(len(keep))],1])
        candidates = range(len(keep))
        firstc = numpy.argmax(etor[:,keep].sum(axis=0))
        reorder = [firstc]
        candidates.pop(firstc)
        while len(candidates) > 0:
            nextc = numpy.argmin(dists[keep[reorder[-1]],[keep[c] for c in candidates]])
            reorder.append(candidates[nextc])
            candidates.pop(nextc)
        process_order = [keep[reorder[i]] for i in order_seq]
            
        stats, assv = self.makeCountsWedges(etor, process_order)
        sums_layers = numpy.ones(max(wedges_pos[:,0])+1)
        tot = 0
        for s,v in stats.items():
            sums_layers[wedges_pos[s,0]] += v["#"]
            tot += v["#"]
        
        radii = [0]
        off = etor.shape[0]/float(3.*len(sums_layers))
        for i in range(len(sums_layers)):
            # radii.append((i+1)*100.)
            # radii.append(numpy.sqrt(sums_layers[:(i+1)].sum()/numpy.pi + sum(radii))) ### Area prop
            # radii.append(sums_layers[:(i+1)].sum()) ### Radius prop
            radii.append(sums_layers[:(i+1)].sum() + (i+1)*off) ### Radius prop
        radii[-1] *=10/9.
        standard = (tot, radii[-2]/radii[-1])
        radii = numpy.array(radii)/radii[-1]
        lRs = reduceRs(len(keep), wedges_pos, neighbors, stats)
        ns = len(lRs)
        x0, x1, y0, y1 = (-radii[-1],radii[-1],-radii[-1],radii[-1])
        bx, by = (x1-x0)/100.0, (y1-y0)/100.0

        wedges_abs = numpy.vstack([radii[wedges_pos[:,0]], radii[wedges_pos[:,0]+1],
                                       (wedges_pos[:,1]-OFFSET)/wedges_pos[:,2],
                                       (wedges_pos[:,1]+(1-OFFSET))/wedges_pos[:,2],
                                       1*(wedges_pos[:,1] % wedges_pos[:,2] == 0) \
                                       -1*((wedges_pos[:,1]+1) % wedges_pos[:,2] == 0) \
                                       -2*(wedges_pos[:,2] == 1)]).T

        xys = numpy.vstack([(wedges_pos[:,0] > 0) *
                                (radii[wedges_pos[:,0]] + 0.5*(radii[wedges_pos[:,0]+1]-radii[wedges_pos[:,0]]))*
                                numpy.cos(wedges_pos[:,1]*2*numpy.pi/wedges_pos[:,2]),
                                (wedges_pos[:,0] > 0) *
                                (radii[wedges_pos[:,0]] + 0.5*(radii[wedges_pos[:,0]+1]-radii[wedges_pos[:,0]]))*
                                numpy.sin(wedges_pos[:,1]*2*numpy.pi/wedges_pos[:,2])]).T

        sRs = [2**ri for ri in range(ns)]
        xyRs  = numpy.vstack([(radii[wedges_pos[sRs,0]+1] + 0.5*(radii[wedges_pos[sRs,0]+2]-radii[wedges_pos[sRs,0]+1]))*
                                  numpy.cos(wedges_pos[sRs,1]*2*numpy.pi/wedges_pos[sRs,2]),
                                  (radii[wedges_pos[sRs,0]+1] + 0.5*(radii[wedges_pos[sRs,0]+2]-radii[wedges_pos[sRs,0]+1]))*
                                  numpy.sin(wedges_pos[sRs,1]*2*numpy.pi/wedges_pos[sRs,2])]).T
        Rs_abs = numpy.vstack([radii[wedges_pos[sRs,0]+1], radii[wedges_pos[sRs,0]+2],
                                   (wedges_pos[sRs,1]-OFFSET)/wedges_pos[sRs,2],
                                   (wedges_pos[sRs,1]+(1-OFFSET))/wedges_pos[sRs,2],
                                   1*(wedges_pos[sRs,1] % wedges_pos[sRs,2] == 0) \
                                   -1*((wedges_pos[sRs,1]+1) % wedges_pos[sRs,2] == 0) \
                                   -2*(wedges_pos[sRs,2] == 1)]).T
                                   
        increment = 1./(2*numpy.prod(numpy.unique(wedges_pos[:,-1])))
        if increment > 0.02:
            increment /= 10

        assv[etor.sum(axis=1)==0] = -1
            
        return {"wedges_abs": wedges_abs, "wedges_xys": xys, "wedges_off": numpy.zeros((wedges_abs.shape[0],2)),
                "Rs_abs": Rs_abs, "Rs_xys": xyRs, "Rs_off": numpy.zeros((Rs_abs.shape[0],2)),
                "wedges_neighbors": neighbors, "wedges_stats": stats, "dots_wedges": assv,
                "Rs_wedges": lRs, "Rs_nb": ns, "Rs_process_order": process_order,                
                "boundaries": (x0, x1, y0, y1, bx, by), "increment": increment, "standard": standard,
                }

    def prepareDrawingRemains(self, etor, non_inter, elems):        
        counts = sorted([(etor[:,i].sum(), i) for i in non_inter])
        if self.getDeltaOn():
            counts.append((numpy.sum(etor.sum(axis=1)==0), -1))
            
        if len(counts) == 0:
            return elems
        
        if len(elems) == 0:
            standard = (etor.shape[0], 9/10.)
            increment = 0.01
            margin = 1 - standard[1]
            nbW = 0
            nbR = 0
            assv = -numpy.ones(etor.shape[0], dtype=int)
            stats = {}
            lRs = []
            process_order = []
            neighbors = {}
            ns = len(counts)
            (x0, x1, y0, y1, bx, by) = (float("Inf"),float("-Inf"),float("Inf"),float("-Inf"), margin/4., margin/4.)

        else:
            standard = elems["standard"]
            increment = elems["increment"]
            margin = 1 - standard[1]
            nbW = elems["wedges_abs"].shape[0]
            nbR = elems["Rs_abs"].shape[0]
            assv = elems["dots_wedges"]
            stats = elems["wedges_stats"]
            lRs = elems["Rs_wedges"]
            process_order = elems["Rs_process_order"]
            neighbors = elems["wedges_neighbors"]
            ns = elems["Rs_nb"]+len(counts)
            (x0, x1, y0, y1, bx, by) = elems["boundaries"]

        for ni, (s, i) in enumerate(counts):
            lRs.append([ni+nbW])
            stats[ni+nbW] = {"bin": "-", "#": s}
            if i == -1:
                assv[etor.sum(axis=1)==0] = ni+nbW
            else:
                assv[etor[:,i]] = ni+nbW
            process_order.append(i)
            neighbors[ni+nbW] = {-1: -1}

        wedges_abs = numpy.array([[0, standard[1]*numpy.sqrt(float(c)/standard[0]), 0., 1., 0] for c, ri in counts])
        Rs_abs = wedges_abs[:,(1, 1, 2, 3, 4)]
        Rs_abs[:,1] += margin
        
        y = -(1+margin+wedges_abs[:,1].max())
        xleft = -numpy.sum(margin+wedges_abs[:,1])
        centers = numpy.array([(xleft+2*numpy.sum(margin+wedges_abs[:i,1])+numpy.sum(margin+wedges_abs[i,1]), y) for i in range(wedges_abs.shape[0])])

        Rs_xys = numpy.vstack([ (Rs_abs[:,0]+0.5*margin)* numpy.cos(0.66*2*numpy.pi),
                                (Rs_abs[:,0]+0.5*margin)* numpy.sin(0.66*2*numpy.pi)]).T

        (x0, x1, y0, y1) = (min(x0, xleft), max(x1, -xleft), min(y0, -(1+2*(margin+wedges_abs[:,1].max()))), max(y1,-1)) 

        nelems = {"wedges_neighbors": neighbors, "wedges_stats": stats, "dots_wedges": assv,
                    "Rs_wedges": lRs, "Rs_nb": ns, "Rs_process_order": process_order,                
                    "boundaries": (x0, x1, y0, y1, bx, by), "increment": increment, "standard": standard,
                    "wedges_abs": wedges_abs, "wedges_xys": numpy.zeros(centers.shape), "wedges_off": centers,
                    "Rs_abs": Rs_abs, "Rs_xys": Rs_xys, "Rs_off": centers
                    }

        if len(elems) > 0:
            for field in ["wedges_abs", "wedges_xys", "wedges_off", "Rs_abs", "Rs_xys", "Rs_off"]:
                nelems[field] = numpy.vstack([elems[field], nelems[field]])
        return nelems
        
    def drawElements(self, elems):        
        artists = {"Rs": {}, "wedges": {}, "highlight": {}}
        axe = self.axe
        to_draw = set([]).union(*elems["Rs_wedges"])
        
        for s in range(elems["wedges_abs"].shape[0]):
            if s in to_draw:
                lbl = None
                if s in elems["wedges_stats"]:
                    # self.axe.plot(xys[s,0],xys[s,1], "ok")
                    # self.axe.text(xys[k,0],xys[k,1], "%s" % (numpy.binary_repr(k, width=ns)))
                    lbl = axe.text(elems["wedges_xys"][s,0]+elems["wedges_off"][s,0],
                                   elems["wedges_xys"][s,1]+elems["wedges_off"][s,1],
                                   "%s" % elems["wedges_stats"][s]["#"], va="center", ha="center", visible=False)
                
                artists["wedges"][s] = {"Rs": {}, "lbl": lbl, "borders": []}
                poly_xy = getPolyDots(elems["wedges_abs"][s], elems["increment"]) + elems["wedges_off"][s,:]
                artists["wedges"][s]["borders"].append(axe.plot(poly_xy[range(poly_xy.shape[0])+[0],0],
                                                                poly_xy[range(poly_xy.shape[0])+[0],1],
                                                                "-", color = "#555555", linewidth=0.5, visible=False))
            
        for ri in range(elems["Rs_nb"])[::-1]: # [3]: #
            if elems["Rs_process_order"][ri] == -1:
                color = self.color_palet["before_light"]
            else:
                color = self.color_list[elems["Rs_process_order"][ri] % len(self.color_list)]
            poly_xy = getPolyDots(elems["Rs_abs"][ri], elems["increment"]) + elems["Rs_off"][ri,:]

            Rpoly = Polygon(poly_xy, fill=True, linewidth=0, color=color, alpha=0.2, visible=False)
            axe.add_patch(Rpoly)
            lbl = axe.text(elems["Rs_xys"][ri,0]+elems["Rs_off"][ri,0], elems["Rs_xys"][ri,1]+elems["Rs_off"][ri,1],
                           elems["Rs_lbls"][ri], color=color, va="center", ha="center")

            artists["Rs"][ri] = {"poly": Rpoly, "lbl": lbl, "borders": [], "ws": {}}    
            
            for s in elems["Rs_wedges"][ri]:
                poly_xy = getPolyDots(elems["wedges_abs"][s], elems["increment"]) + elems["wedges_off"][s,:]
                wpoly = Polygon(poly_xy, fill=True, linewidth=0, color=color, alpha=0.2)
                artists["Rs"][ri]["ws"][s] = wpoly
                artists["wedges"][s]["Rs"][ri] = wpoly
                axe.add_patch(wpoly)
                
            edges, arcs = getEnveloppe(ri, elems["Rs_wedges"][ri],
                                           elems["wedges_abs"], elems["wedges_neighbors"])
            for edge in edges:
                xx = getEdgeX(edge[0], edge[1], edge[2]) + elems["Rs_off"][ri,0]
                yy = getEdgeY(edge[0], edge[1], edge[2]) + elems["Rs_off"][ri,1]
                artists["Rs"][ri]["borders"].append(axe.plot(xx, yy,
                                                    "-", color = color, linewidth=3, visible=False))

            for arc in arcs:
                xx = getArcX(arc[0], arc[1], arc[2], elems["increment"])+ elems["Rs_off"][ri,0]
                yy = getArcY(arc[0], arc[1], arc[2], elems["increment"])+ elems["Rs_off"][ri,1]
                artists["Rs"][ri]["borders"].append(axe.plot(xx, yy,
                                                    "-", color = color, linewidth=3, visible=False))

        return artists

    def getRLbl(self, ri, rl, dupls):
        if rl == -1:
            return ""
        dd = ["R%s" % self.srids[r] for r in dupls.get(rl, [])]
        if len(dd) > 0:
            return "R%s [%s]" % (self.srids[rl], ",".join(dd))
        return "R%s" % self.srids[rl]
    
    def updateMap(self):
        """ Redraws the map
        """

        if hasattr( self, 'etor' ):
            self.clearPlot()

            etor = self.etor
            keep, dupls, non_inter, dists = self.filterRs(etor)
            keep, surplus, wedges_pos, neighbors = makeMapWedges(keep)
            elems = self.prepareDrawingElements(etor, keep, dists, wedges_pos, neighbors)
            self.elems = self.prepareDrawingRemains(etor, non_inter, elems)
            self.elems["Rs_lbls"] = [self.getRLbl(ri, rl, dupls) for (ri, rl) in enumerate(self.elems["Rs_process_order"])]
            self.artists = self.drawElements(self.elems)
            dots = self.makeDotsE(self.elems)
            if self.getDeltaOn():
                self.axe.plot(dots[0], dots[1], ".k")
            else:
                ids_draw = numpy.where(self.elems["dots_wedges"] > -1)[0]
                self.axe.plot(dots[0][ids_draw], dots[1][ids_draw], ".k")
            self.axe.axis([self.elems["boundaries"][0]-self.elems["boundaries"][-2],
                           self.elems["boundaries"][1]+self.elems["boundaries"][-2],
                           self.elems["boundaries"][2]-self.elems["boundaries"][-1],
                           self.elems["boundaries"][3]+self.elems["boundaries"][-1]])
            self.axe.set_xticks([])
            self.axe.set_yticks([])

            ## plt.show()
        else:
            self.axe.plot(range(3), range(3), ".k")
            
    def makeDotsE(self, elems):
        ass = elems["dots_wedges"]
        rands = numpy.random.random((ass.shape[0], 2))
        zz = elems["wedges_abs"][ass, INA["r0"]] == 0
        rands[zz,0] += numpy.random.random(zz.sum())
        rands[rands[:,0] > 1,0] =  2 - rands[rands[:,0] > 1,0]
        rands[elems["wedges_abs"][ass, INA["r0"]] > 0,:] = 0.9 * rands[elems["wedges_abs"][ass, INA["r0"]] > 0,:] + 0.05
        rands[elems["wedges_abs"][ass, INA["r0"]] == 0,0] *= 0.95
        
        rs = elems["wedges_abs"][ass, INA["r0"]] + rands[:,0]*(elems["wedges_abs"][ass, INA["r1"]] - elems["wedges_abs"][ass, INA["r0"]])
        alphas = elems["wedges_abs"][ass, INA["alpha0"]] + rands[:,1]*(elems["wedges_abs"][ass, INA["alpha1"]] - elems["wedges_abs"][ass, INA["alpha0"]])
        x,y = getXY(rs, alphas)
        x += elems["wedges_off"][ass,0]
        y += elems["wedges_off"][ass,1]
        return (x,y)
        

    def getEtoR(self):
        nbE = 0
        if len(self.srids) > 0:
            nbE = self.reds[self.srids[0]].sParts.nbRows()
        etor = numpy.zeros((nbE, len(self.srids)), dtype=bool)
        for r, rid in enumerate(self.srids):
            etor[list(self.reds[rid].getSuppI()), r] = True
        return etor

    def setCurrent(self, reds_map):
        self.reds = dict(reds_map)
        self.srids = [rid for (rid, red) in reds_map]
        self.etor = self.getEtoR()
        self.updateMap()

    def filterRs(self, etor):
        dists = scipy.spatial.distance.squareform(scipy.spatial.distance.pdist(etor.T, "jaccard"))
        duplicatesX, duplicatesY = numpy.where(numpy.triu(dists == 0, 1))
        seen = set()
        dupls = {}
        for i in range(duplicatesX.shape[0]):
            if duplicatesX[i] not in seen:
                if duplicatesX[i] not in dupls:
                    dupls[duplicatesX[i]] = []
                dupls[duplicatesX[i]].append(duplicatesY[i])
                seen.add(duplicatesY[i])
        keep = [r for r in range(etor.shape[1]) if r not in seen]
        dists = dists[keep,:][:,keep]
        non_inter = numpy.where(dists.sum(axis=0)+1 == dists.shape[0])[0]
        keep = [r for (i,r) in enumerate(keep) if i not in non_inter]
        if len(keep) > 7:
            pdb.set_trace()
            
        return keep, dupls, non_inter, dists

    def makeCountsWedges(self, etor, keep):
        assv = numpy.inner(etor[:, keep], numpy.array([[2**i for i in range(len(keep))]])).flatten()
        return dict([(k, {"#":v, "bin": numpy.binary_repr(k, width=len(keep))}) for (k,v) in enumerate(numpy.bincount(assv)) if v > 0 and k > 0]), assv

    def getWedgeAt(self, x, y):
        r, alpha = getRA(x-self.elems["wedges_off"][:,0], y-self.elems["wedges_off"][:,1])
        ids = numpy.where((self.elems["wedges_abs"][:, INA["r0"]] < r) &
                          (self.elems["wedges_abs"][:, INA["r1"]] > r) &
                          isAlphaIn(alpha, self.elems["wedges_abs"][:, INA["alpha0"]],
                                        self.elems["wedges_abs"][:, INA["alpha1"]]))[0]
        if len(ids) == 1:
            if ids[0] != 0:
                return ("w", ids[0])                

        r, alpha = getRA(x-self.elems["Rs_off"][:,0], y-self.elems["Rs_off"][:,1])
        rids = numpy.where((self.elems["Rs_abs"][:, INA["r0"]] < r) &
                           (self.elems["Rs_abs"][:, INA["r1"]] > r) &
                           isAlphaIn(alpha, self.elems["Rs_abs"][:, INA["alpha0"]],
                                         self.elems["Rs_abs"][:, INA["alpha1"]]))[0]
        if len(rids) == 1:
            return ("r", rids[0])
        return None

    def getWedgeAtDot(self, x, y):        
        r, alpha = getRA(x, y)
        ids = numpy.where((self.elems["wedges_abs"][:, INA["r0"]] < r) &
                          (self.elems["wedges_abs"][:, INA["r1"]] > r) &
                          isAlphaIn(alpha, self.elems["wedges_abs"][:, INA["alpha0"]],
                                        self.elems["wedges_abs"][:, INA["alpha1"]]))[0]
        if len(ids) != 1:
            return None
        if ids[0] == 0:
            rids = numpy.where((self.elems["Rs_abs"][:, INA["r0"]] < r) &
                               (self.elems["Rs_abs"][:, INA["r1"]] > r) &
                                isAlphaIn(alpha, self.elems["Rs_abs"][:, INA["alpha0"]],
                                            self.elems["Rs_abs"][:, INA["alpha1"]]))[0]
            if len(rids) != 1:
                return None
            return ("r", rids[0])
        return ("w", ids[0])

    
    def on_click(self, event):
        if event.inaxes != self.axe: return
        wid = self.getWedgeAt(event.xdata, event.ydata)
        if wid is not None:
            print wid
            if wid[0] == "r" and wid[1] in self.artists["Rs"]:
                # print wid, self.artists["Rs"][wid[1]]
                data = self.artists["Rs"][wid[1]]
                borders = data["borders"]
            elif wid[0] == "w" and wid[1] in self.artists["wedges"]:
                # print wid, self.artists["wedges"][wid[1]]
                data = self.artists["wedges"][wid[1]]
                borders = []
                for rr in data["Rs"].keys():
                    # borders.extend(self.artists["Rs"][rr]["borders"])
                    b = self.artists["Rs"][rr]["poly"]
                    b.set_visible(not b.get_visible())
                
            for bs in borders:
                for b in bs:
                    b.set_visible(not b.get_visible())
            self.MapcanvasMap.draw()
