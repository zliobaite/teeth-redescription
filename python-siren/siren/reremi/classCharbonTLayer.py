import numpy as np
from sklearn import tree

from classCharbon import CharbonTree
from classQuery import  *
from classRedescription import  *


import pdb

#########################################################################
################# from trees_m2
#########################################################################
# from sklearn import tree
# import numpy as np
# from classQuery import  *
### import sys


NID = 0
def next_nid():
    global NID
    NID += 1
    return NID

def gather_supp(tree_exp):
    def recurse_gather(tree_exp, node_id, support_vs, which=None):
        if "split" in tree_exp[node_id]:
            recurse_gather(tree_exp, tree_exp[node_id]["children"][0], support_vs, 0)
            recurse_gather(tree_exp, tree_exp[node_id]["children"][1], support_vs, 1)
        else:
            if which == 0:
                support_vs.append(tree_exp[node_id]["support"])
    support_vs = []
    recurse_gather(tree_exp["nodes"], tree_exp["root"], support_vs)
    return np.sum(support_vs,axis=0)

def set_supp(tree_exp, data_in, mask=None):
    def recurse_supp(tree_exp, data_in, node_id, support_v, over_supp, which=0):
        if "split" in tree_exp[node_id]:
            if tree_exp[node_id]["split"][-1] > 0:
                Ev = data_in[:,tree_exp[node_id]["split"][0]] <= tree_exp[node_id]["split"][-2]
            else:
                Ev = data_in[:,tree_exp[node_id]["split"][0]] > tree_exp[node_id]["split"][-2]
            recurse_supp(tree_exp, data_in, tree_exp[node_id]["children"][0], support_v*Ev, over_supp, 0)
            recurse_supp(tree_exp, data_in, tree_exp[node_id]["children"][1], support_v*np.logical_not(Ev), over_supp, 1)
        else:
            tree_exp[node_id]["support"] = np.zeros(mask.shape[0], dtype=bool)
            tree_exp[node_id]["support"][mask] = support_v
            if which == 0:
                over_supp += tree_exp[node_id]["support"]
    if mask is None:
        mask = np.ones(data_in.shape[0], dtype=bool)
    over_supp = np.zeros(mask.shape[0], dtype=bool)
    recurse_supp(tree_exp["nodes"], data_in, tree_exp["root"], np.ones(data_in.shape[0], dtype=bool), over_supp)
    tree_exp["over_supp"] = over_supp
    return over_supp    

def get_variables(tree_exp, node_id):
    variables = set()
    if "split" in tree_exp[node_id]:
        variables.add(tree_exp[node_id]["split"][1])
        variables |= get_variables(tree_exp, tree_exp[node_id]["children"][0])
        variables |= get_variables(tree_exp, tree_exp[node_id]["children"][1])
    return variables

def get_tree(decision_tree, candidates):
    def recurse(decision_tree, node_id, tree_exp, candidates=None, parent=None, depth=0, new_nid=None):
        if node_id == tree._tree.TREE_LEAF:
            raise ValueError("Invalid node_id %s" % tree._tree.TREE_LEAF)

        if new_nid is None:
            new_nid = next_nid()
        new_node = {"id": new_nid, "parent": parent} #,
        children = []
        if decision_tree.children_left[node_id] != tree._tree.TREE_LEAF:

            nvar = decision_tree.feature[node_id]
            if candidates is not None:
                try:
                    nvar = candidates[nvar]
                except IndexError:
                    pdb.set_trace()
                    print nvar, candidates
            lcid, rcid = (decision_tree.children_left[node_id], decision_tree.children_right[node_id])
            dl = decision_tree.value[lcid][0]
            dr = decision_tree.value[rcid][0]

            # jL = dl[1]/(dl[1]+dl[0]+dr[0])
            # jR = dr[1]/(dr[1]+dl[0]+dr[0])

            # if (dl[0] < dl[1] and dr[0] < dr[1]) or (dl[0] > dl[1] and dr[0] > dr[1]):
            # ### both are or aren't majority classes, either way stop extension
            #     tree_exp["root"] = None
            #     return

            #if jL > jR: 
            if dl[0] < dl[1] and dr[1] < dr[0]: ### left child is majority positive -> Bool False
                new_node["split"] = (decision_tree.feature[node_id], nvar, decision_tree.threshold[node_id], 1)
                children = [lcid, rcid]
                new_node["children"] = [next_nid(), next_nid()]
            #else:
            elif dl[1] < dl[0] and dr[0] < dr[1]: ### right child is majority positive -> Bool True
                new_node["split"] = (decision_tree.feature[node_id], nvar, decision_tree.threshold[node_id], -1)
                children = [rcid, lcid]
                new_node["children"] = [next_nid(), next_nid()]
            else: ### both are or aren't, either way stop extension
                 tree_exp["root"] = None
                 return
            for cci, cid in enumerate(children):
                recurse(decision_tree, cid, tree_exp, candidates, parent=new_nid, depth=depth + 1, new_nid = new_node["children"][cci])    

        if len(children) == 0:
            tree_exp["leaves"].append(new_nid)

        tree_exp["nodes"][new_nid] = new_node

    tree_exp = {"nodes": {}, "root": None, "leaves": []}
    if decision_tree.node_count > 2:
        tree_exp["root"] = next_nid()
        recurse(decision_tree, 0, tree_exp, candidates, new_nid=tree_exp["root"])
    return tree_exp

#Function which does split of left and right trees
def splitting(in_target, in_data, candidates, max_depth= 1,  min_bucket=3, split_criterion="gini"):
    if sum(in_target) <= min_bucket:
        return {"root": None}

    data_rpart = tree.DecisionTreeClassifier(criterion=split_criterion, max_depth = 1, min_samples_leaf = min_bucket, random_state=0).fit(in_data, in_target)
    # split_vector = data_rpart.predict(in_data) #Binary vectoFile "/home/r/NetBeansProjects/RedescriptionTrees/src/redescriptiontrees_method2.py", line 201, in <module>r of the tree for Jaccard
    split_tree = get_tree(data_rpart.tree_, candidates)
    # print "SPLIT", data_rpart.tree_.feature[0], candidates[data_rpart.tree_.feature[0]], data_rpart.tree_.threshold[0], in_data.shape, in_data[:,data_rpart.tree_.feature[0]]
    # ttt = set_supp(split_tree, in_data)
    # if sum(ttt-split_vector) > 0:
    #     print "Something smells bad around here splitting..."
    #     pdb.set_trace()
    #     ttt = set_supp(split_tree, in_data)
    # print sum(ttt-split_vector), sum(ttt), "vs", sum(split_vector) 
    return split_tree

def init_tree(data, side, vid=None, more={}, cols_info=None):
    #### TEST INIT
    parent_tree = {"id": None,
                   "branch": None,
                   "candidates": range(data[side].shape[1])}
    if vid is not None:
        invol = more.get("involved", [vid])
        if cols_info is not None:
            ttm = [cols_info[side][c][1] for c in invol]
            invol = [kk for (kk,vv) in cols_info[side].items() if vv[1] in ttm]

        for vv in invol:
            parent_tree["candidates"].remove(vv)
        if "supp" in more:
            supp_pos = more["supp"]
            split = vid
        else:
            supp_pos = data[side][:,vid] > 0.5
            split = (vid, vid, 0.5, -1)
        parent_tree["over_supp"] = supp_pos
        
        nidt = next_nid()
        nidl = next_nid()
        nidr = next_nid()
        parent_tree["root"] = nidt
        parent_tree["leaves"] = [nidl, nidr]
        parent_tree["nodes"] = {nidt: {"id": nidt, "split": split, "parent": None, "children": [nidl,nidr]},
                                nidl: {"id": nidl, "support": supp_pos, "parent": nidt},
                                nidr: {"id": nidr, "support": np.logical_not(supp_pos), "parent": nidt}}
    else:
        nidt = next_nid()
        parent_tree["root"] = nidt
        parent_tree["init"] = True
        parent_tree["leaves"] = [nidt]
        parent_tree["nodes"] = {nidt: {"id": nidt, "support": np.ones(data[side].shape[0], dtype=bool)}}
                                    
    return parent_tree

def initialize_treepile(data, side_ini, vid, more={}, cols_info=None):
    trees_pile = [[[]],[[]]]
    trees_store = {}

    PID = 0
    anc_tree = init_tree(data, 1-side_ini)
    anc_tree["id"] = PID

    trees_pile[1-side_ini][-1].append(PID)
    trees_store[PID] = anc_tree
    PID += 1

    parent_tree = init_tree(data, side_ini, vid, more, cols_info)
    parent_tree["id"] = PID
    trees_pile[side_ini][-1].append(PID)
    trees_store[PID] = parent_tree
    PID += 1
    return trees_pile, trees_store, PID
    

def piece_together(trees_store, trees_pile_side):
    out = None
    for ii in range(len(trees_pile_side[0])-1, -1, -1):
        if trees_store[trees_pile_side[0][ii]].get("init", False):
            del trees_store[trees_pile_side[0][ii]]
            trees_pile_side[0].pop(ii)
        if len(trees_pile_side[0]) == 0:
            trees_pile_side.pop(0)

    while len(trees_pile_side) > 1:
        current_layer = trees_pile_side.pop()
        for tree in current_layer:
            toplug = trees_store[tree]["branch"]
            # print "PLUG: ", toplug
            pnid = trees_store[toplug[0]]["nodes"][toplug[1]]["parent"]
            rp = trees_store[toplug[0]]["nodes"][pnid]["children"].index(toplug[1])
            trees_store[toplug[0]]["nodes"][pnid]["children"][rp] = trees_store[tree]["root"] 
            # trees_store[tree]["nodes"][trees_store[tree]["root"]]["replace"] = toplug[1]
            del trees_store[toplug[0]]["nodes"][toplug[1]]
            trees_store[toplug[0]]["nodes"].update(trees_store[tree]["nodes"])
            trees_store[toplug[0]]["leaves"].remove(toplug[1])
            trees_store[toplug[0]]["leaves"].extend(trees_store[tree]["leaves"])
            del trees_store[tree]
    if len(trees_pile_side[0]) > 1:
        print "Many trees left..."
    for treeid in trees_pile_side.pop():
        for field in ["candidates", "over_supp", "branch", "id"]:
            del trees_store[treeid][field]
        out = treeid
    return out

def get_trees_pair(data, trees_pile, trees_store, side_ini, max_level, min_bucket, split_criterion="gini", PID=0, singleD=False, cols_info=None):
    if singleD:
        candidates = list(trees_store[1]["candidates"])

    current_side = side_ini
    #### account for dummy tree on other side when counting levels
    while min(len(trees_pile[side_ini]),len(trees_pile[1-side_ini])-1) < max_level and len(trees_pile[current_side][-1]) > 0:
        # print side_ini, len(trees_pile[side_ini]), len(trees_pile[1-side_ini]), len(trees_pile[current_side][-1])
        target = np.sum([trees_store[tree]["over_supp"] for tree in trees_pile[current_side][-1]], axis=0)
        # print "TARGET", current_side, sum(target)
        current_side = 1-current_side
        trees_pile[current_side].append([])
        
        for gpid in trees_pile[current_side][-2]:
            gp_tree = trees_store[gpid]
            if not singleD:
                candidates = gp_tree["candidates"]
            
            dt = data[current_side][:, candidates]
            for leaf in gp_tree["leaves"]:            
                mask = gp_tree["nodes"][leaf]["support"]
                # print "BRANCH\t(%d,%d)\t%d %d\t%d:%d/%d"  % (current_side, len(trees_pile[current_side]),
                #                                              gp_tree["id"], leaf, sum(mask),
                #                                              sum(target[mask]), sum(mask)-sum(target[mask]))
                # print current_side, dt[mask,:].shape
                split_tree = splitting(target[mask], dt[mask,:], candidates,
                                       max_depth=1, min_bucket=min_bucket, split_criterion=split_criterion)
                if split_tree["root"] is not None:
                    set_supp(split_tree, dt[mask,:], mask)
                    # print "\tX", split_tree["nodes"][split_tree["root"]]["split"], [sum(split_tree["nodes"][lf]["support"]) for lf in split_tree["leaves"]], sum(split_tree["over_supp"])
                    
                    split_tree["branch"] = (gp_tree["id"], leaf)
                    vrs = get_variables(split_tree["nodes"], split_tree["root"])
                    
                    if cols_info is None:
                        ncandidates = [vvi for vvi in candidates if vvi not in vrs]
                    else:
                        ttm = [cols_info[current_side][c][1] for c in vrs]
                        ncandidates = [vvi for vvi in candidates if cols_info[current_side][vvi][1] not in ttm]

                    split_tree["candidates"] = list(ncandidates)
                    # print "CANDIDATES", current_side, vrs
                    split_tree["id"] = PID
                    trees_pile[current_side][-1].append(PID)
                    trees_store[PID] = split_tree
                    PID += 1
    # print side_ini, len(trees_pile[side_ini]), len(trees_pile[1-side_ini]), len(trees_pile[current_side][-1])
    # pdb.set_trace()
    return trees_pile, trees_store, PID

def extract_reds(trees_pile, trees_store, data, cols_map):
    outids = (piece_together(trees_store, trees_pile[0]), piece_together(trees_store, trees_pile[1]))
    if outids[0] is not None and outids[1] is not None:
        qus = (make_lits(0, trees_store[outids[0]], data, cols_map[0]), make_lits(1, trees_store[outids[1]], data, cols_map[1]))
        supps = (gather_supp(trees_store[outids[0]]), gather_supp(trees_store[outids[1]]))
        trees = (trees_store[outids[0]], trees_store[outids[1]])
        return qus, supps, trees
    return None

def make_lits(side, tree_exp, data, cols_info):
    def recurse_lits(side, tree_exp, node_id, data, cols_info, which=0):
        lls = []
        if "split" in tree_exp[node_id]:
            lit = make_literal(side, tree_exp[node_id]["split"], data, cols_info)
            for l in recurse_lits(side, tree_exp, tree_exp[node_id]["children"][0], data, cols_info, which=0):
                try:
                    lls.append([lit.copy()]+l)
                except AttributeError:
                    pdb.set_trace()
            lit.flip()
            for l in recurse_lits(side, tree_exp, tree_exp[node_id]["children"][1], data, cols_info, which=1):
                lls.append([lit.copy()]+l)
        elif which == 0:
            lls.append([])
        return lls
    tmp = recurse_lits(side, tree_exp["nodes"], tree_exp["root"], data, cols_info)
    return Query(True, tmp)

def make_literal(side, node, data, cols_info):
    lit=None
    ### HERE test for literal
    if isinstance(node, Literal):
        lit = node
    elif len(node) > 2:
        if node[-3] in cols_info:
            side, cid, cbin = cols_info[node[-3]]
        else:
            raise Warning("Literal cannot be parsed !")
            cid = node[-3]
        threshold = node[-2]
        direct = node[-1]

        if data.cols[side][cid].typeId() == BoolTerm.type_id:
            lit = Literal(direct > 0, BoolTerm(cid))
        elif data.cols[side][cid].typeId() == CatTerm.type_id:
            lit = Literal(direct > 0, CatTerm(cid, data.col(side, cid).getCatFromNum(cbin)))
        elif data.cols[side][cid].typeId() == NumTerm.type_id:
            if direct > 0:
                rng = (float("-inf"), data.col(side, cid).getRoundThres(threshold, "high"))
            else:
                rng = (data.col(side,cid).getRoundThres(threshold, "low"), float("inf")) 
            lit = Literal(False, NumTerm(cid, rng[0], rng[1]))
        else:
            raise Warning('This type of variable (%d) is not yet handled with tree mining...' % data.cols[side][cid].typeId())
    return lit


#########################################################################
#########################################################################

    
class CharbonTLayer(CharbonTree):

    name = "TreeLayer"
    def getTreeCandidates(self, side, data, red):
        if side not in [0,1]:
            side = 1
            if len(red.queries[0]) == 1:
                side = 0
        if len(red.queries[side]) != 1:
            return None

        in_data_l, tmp, tcols_l = data.getMatrix([(0, None)], bincats=True)
        in_data_r, tmp, tcols_r = data.getMatrix([(1, None)], bincats=True)

        cols_info = [dict([(i,d) for (d,i) in tcols_l.items() if len(d) == 3]),
                     dict([(i,d) for (d,i) in tcols_r.items() if len(d) == 3])]

        llt = red.queries[side].listLiterals()[0]
        ss = data.supp(side, llt)
        data_tt = [in_data_l.T, in_data_r.T]

        supp = np.zeros(data.nbRows(), dtype=bool)
        supp[list(ss)] = True
        if side == 0:
            mmap = tcols_l
        else:
            mmap = tcols_r
        if llt.typeId() == 2:
            off = data.cols[side][llt.colId()].numEquiv(llt.getTerm().getCat())
        else:
            off = 0
        vid = mmap[(side, llt.colId(), off)]
        more = {"involved": [vid], "supp": supp}
        trees_pile, trees_store, PID = initialize_treepile(data_tt, side, llt, more, cols_info=cols_info)
        trees_pile, trees_store, PID = get_trees_pair(data_tt, trees_pile, trees_store, side,
                                                      max_level=self.constraints.getCstr("max_depth"),
                                                      min_bucket=self.constraints.getCstr("min_node_size"),
                                                      split_criterion=self.constraints.getCstr("split_criterion"),
                                                      PID=PID, singleD=data.isSingleD(), cols_info=cols_info)

        redt = extract_reds(trees_pile, trees_store, data, cols_info)
        if redt is not None:
            red = Redescription.fromQueriesPair(redt[0], data)
            # if np.sum(redt[1][0]*redt[1][1]) != red.sParts.lenI():
            #     print np.sum(redt[1][0]*redt[1][1])
            #     pdb.set_trace()
            return red
        return None

