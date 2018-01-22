import copy
import numpy as np
from sklearn import tree

from classCharbon import CharbonTree
from classQuery import  *
from classRedescription import  *

import pdb

class CharbonTCW(CharbonTree):
    name = "TreeCartWheel"

    def initializeData(self, side, data):
        in_data_l, tmp, tcols_l = data.getMatrix([(0, None)], bincats=True)
        in_data_r, tmp, tcols_r = data.getMatrix([(1, None)], bincats=True)

        in_data = [in_data_l.T, in_data_r.T]
        cols_info = [dict([(i,d) for (d,i) in tcols_l.items() if len(d) == 3]),
                     dict([(i,d) for (d,i) in tcols_r.items() if len(d) == 3])]
        return in_data, cols_info

    def initializeTrg(self, side, data, red):
        if red is None or len(red.queries[0]) + len(red.queries[1]) == 0:
            nsupp = np.random.randint(self.constraints.getCstr("min_node_size"), data.nbRows()-self.constraints.getCstr("min_node_size"))
            tmp = np.random.choice(range(data.nbRows()), nsupp, replace=False)
        elif side == -1: # and len(red.queries[0]) * len(red.queries[1]) != 0:
            side = 1
            if len(red.queries[side]) == 0:
                side = 1-side
            tmp = red.supp(side)
        else:
            tmp = red.getSuppI()
        target = np.zeros(data.nbRows())
        target[list(tmp)] = 1
        return target, side

    def getTreeCandidates(self, side, data, red):
        in_data, cols_info = self.initializeData(side, data)
        target, side = self.initializeTrg(side, data, red)
        if side is None:
            jj0, suppvs0, dtcs0 = self.getSplit(0, in_data, target, singleD=data.isSingleD(), cols_info=cols_info)
            jj1, suppvs1, dtcs1 = self.getSplit(1, in_data, target, singleD=data.isSingleD(), cols_info=cols_info)
            if jj0 > jj1:
                jj, suppvs, dtcs = (jj0, suppvs0, dtcs0)
            else:
                jj, suppvs, dtcs = (jj1, suppvs1, dtcs1)
        else:
            jj, suppvs, dtcs = self.getSplit(side, in_data, target, singleD=data.isSingleD(), cols_info=cols_info)

        if dtcs[0] is not None and dtcs[1] is not None:
            red = self.get_redescription(dtcs, suppvs, data, cols_info)
            # if True: ## check
            #     sL = set(np.where(np.array(suppvs[0]))[0])
            #     sR = set(np.where(np.array(suppvs[1]))[0])
            #     if sL != red.supp(0) or sR != red.supp(1):
            #         print "OUPS!"
            #         pdb.set_trace()
            return red
        return None

    def get_redescription(self, dtcs, suppvs, data, cols_info):
        left_query = self.get_pathway(0, dtcs[0], data, cols_info)
        right_query = self.get_pathway(1, dtcs[1], data, cols_info)
        return Redescription.fromQueriesPair((left_query, right_query), data)

    def get_pathway(self, side, tree, data, cols_info):
        def get_branch(side, left, right, child, features, threshold, data, cols_info):
            branch = []
            while child is not None:
                parent = None
                if child in left:
                    neg = True
                    parent = left.index(child)
                elif child in right:
                    neg = False
                    parent = right.index(child)
                if parent is not None:
                    if features[parent] in cols_info:
                        side, cid, cbin = cols_info[features[parent]]
                    else:
                        raise Warning("Literal cannot be parsed !")
                        cid = features[parent]
                    if data.cols[side][cid].typeId() == BoolTerm.type_id:
                        lit = Literal(neg, BoolTerm(cid))
                    elif data.cols[side][cid].typeId() == CatTerm.type_id:
                        lit = Literal(neg, CatTerm(cid, data.col(side, cid).getCatFromNum(cbin)))
                    elif data.cols[side][cid].typeId() == NumTerm.type_id:
                        if neg:
                            rng = (float("-inf"), data.cols[side][cid].getRoundThres(threshold[parent], "high"))
                        else:
                            rng = (data.cols[side][cid].getRoundThres(threshold[parent], "low"), float("inf")) 
                        lit = Literal(False, NumTerm(cid, rng[0], rng[1]))
                    else:
                        raise Warning('This type of variable (%d) is not yet handled with tree mining...' % data.cols[side][cid].typeId())
                    branch.append(lit)
                child = parent
            return branch

        left      = list(tree.tree_.children_left)
        right     = list(tree.tree_.children_right)
        to_parent = {}
        for tside, dt in enumerate([left, right]):
            for ii, ni in enumerate(dt):
                if ni > 0:
                    to_parent[ni] = (tside, ii)
        to_parent[0] = (None, None)
        threshold = tree.tree_.threshold
        features  = [i for i in tree.tree_.feature]
        mclass  = [i[0][0]<i[0][1] for i in tree.tree_.value]
        todo = [i for i in range(len(left)) if left[i] == -1 and mclass[i]]
        count_c = {}
        ii = 0
        while ii < len(todo):
            if to_parent[todo[ii]][1] in count_c:
                todo.append(to_parent[todo[ii]][1])
                tn = todo.pop(ii)
                todo.pop(count_c[to_parent[tn][1]])
                ### BUG IN HIDING...
                # try:
                #     todo.pop(count_c[to_parent[tn][1]])
                # except IndexError:
                #     print "Popping error !", len(todo), tn, to_parent[tn][1], count_c[to_parent[tn][1]]  
                #     pdb.set_trace()                    
                ii -= 1
            else:
                count_c[to_parent[todo[ii]][1]] = ii
                ii += 1

        buks = []
        for child in todo:
            tmp = get_branch(side, left, right, child, features, threshold, data, cols_info[side])
            if tmp is not None:
                buks.append(tmp)
        qu = Query(True, buks)
        return qu

    def getSplit(self, side, in_data, target, singleD=False, cols_info=None):
        suppvs = [None, None]
        dtcs = [None, None]
        best = (0, suppvs, dtcs)
        current_side = 1-side
        if sum(target) >= self.constraints.getCstr("min_node_size") and len(target)-sum(target) >= self.constraints.getCstr("min_node_size"):
            suppvs[side] = target
            rounds = 0
        else:
            rounds = -1

        while rounds < self.constraints.getCstr("max_rounds") and rounds >= 0:            
            rounds += 1
            try:
                ##### HERE
                if dtcs[1-current_side] is not None and singleD:
                    if cols_info is None:
                        tt = [c for c in dtcs[1-current_side].tree_.feature if c >= 0]
                    else:
                        ttm = [cols_info[current_side][c][1] for c in dtcs[1-current_side].tree_.feature if c >= 0]
                        tt = [kk for (kk,vv) in cols_info[current_side].items() if vv[1] in ttm]
                    feed_data = in_data[current_side].copy()
                    feed_data[:,tt] = 0.
                else:
                    feed_data = in_data[current_side]

                dtc, suppv = self.splitting_with_depth(feed_data, suppvs[1-current_side], self.constraints.getCstr("max_depth"), self.constraints.getCstr("min_node_size"))
            except IndexError:
                pdb.set_trace()
                print current_side
            if dtc is None or (dtcs[current_side] is not None and dtcs[1-current_side] is not None \
                               and suppvs[current_side] is not None and np.sum((suppvs[current_side] - suppv)**2) == 0):
            ### nothing found or no change
                rounds = -1
            else:
                suppvs[current_side] = suppv
                dtcs[current_side] = dtc
                current_side = 1-current_side
                if suppvs[0] is not None and suppvs[1] is not None:
                    jj = self.getJacc(suppvs)
                    if jj > best[0] and dtcs[current_side] is not None:
                        best = (jj, list(suppvs), list(dtcs))
        return best

    def getJacc(self, supps):
        lL = np.sum(supps[0])
        lR = np.sum(supps[1])
        lI = np.sum(supps[0] * supps[1])
        return lI/(lL+lR-lI)

    def splitting_with_depth(self, in_data, in_target, in_depth, in_min_bucket,  split_criterion="gini"):
        dtc = tree.DecisionTreeClassifier(criterion= split_criterion, max_depth = in_depth, min_samples_leaf = in_min_bucket, random_state=0)
        dtc = dtc.fit(in_data, in_target)
        
        #Form Vectors for computing Jaccard. The same vectors are used to form new targets
        suppv = dtc.predict(in_data) #Binary vector of the left tree for Jaccard
    
        if sum(suppv) < in_min_bucket or len(suppv)-sum(suppv) < in_min_bucket:
            return None, None
        return dtc, suppv


class CharbonTSprit(CharbonTCW):
    name = "TreeSprit"
    def getSplit(self, side, in_data, target, singleD=False, cols_info=None):
        suppvs = [None, None]
        dtcs = [None, None]
        best = (0, suppvs, dtcs)
        current_side = 1-side
        if sum(target) >= self.constraints.getCstr("min_node_size") and len(target)-sum(target) >= self.constraints.getCstr("min_node_size"):
            suppvs[side] = target
            rounds = 0
        else:
            rounds = -1

        depth = [2,2]
        while depth[0] <= self.constraints.getCstr("max_depth") or depth[1] <= self.constraints.getCstr("max_depth"):
        # while rounds < 30 and rounds >= 0:            
            rounds += 1
            ##### HERE
            if dtcs[1-current_side] is not None and singleD:
                if cols_info is None:
                    tt = [c for c in dtcs[1-current_side].tree_.feature if c >= 0]
                else:
                    ttm = [cols_info[current_side][c][1] for c in dtcs[1-current_side].tree_.feature if c >= 0]
                    tt = [kk for (kk,vv) in cols_info[current_side].items() if vv[1] in ttm]
                feed_data = in_data[current_side].copy()
                feed_data[:,tt] = 0.
            else:
                feed_data = in_data[current_side]

            dtc, suppv = self.splitting_with_depth(feed_data, suppvs[1-current_side], depth[current_side], self.constraints.getCstr("min_node_size"), split_criterion=self.constraints.getCstr("split_criterion"))
            if dtc is None or (dtcs[current_side] is not None and dtcs[1-current_side] is not None \
                               and suppvs[current_side] is not None and np.sum((suppvs[current_side] - suppv)**2) == 0):
            ### nothing found or no change
                rounds = -1
                depth[current_side] = self.constraints.getCstr("max_depth")+1
                depth[1-current_side] = self.constraints.getCstr("max_depth")+1
            else:
                depth[current_side] += 1
                suppvs[current_side] = suppv
                dtcs[current_side] = dtc
                current_side = 1-current_side
                if suppvs[0] is not None and suppvs[1] is not None:
                    jj = self.getJacc(suppvs)
                    if jj > best[0] and dtcs[current_side] is not None:
                        best = (jj, list(suppvs), list(dtcs))
        return best

class CharbonTSplit(CharbonTCW):

    name = "TreeSplit"
    def getTreeCandidates(self, side, data, red):
        in_data, cols_info = self.initializeData(side, data)
        target, side = self.initializeTrg(side, data, red)

        current_split_result = self.getSplit(in_data[0], in_data[1], target, 2, self.constraints.getCstr("min_node_size"), data.isSingleD(), cols_info)
        if current_split_result['data_rpart_l'] is not None and current_split_result['data_rpart_r'] is not None:
            return self.get_redescription([current_split_result['data_rpart_l'], current_split_result['data_rpart_r']],
                                          [current_split_result['split_vector_l'], current_split_result['split_vector_l']],
                                          data, cols_info)
        return None


    def getSplit(self, in_data_l, in_data_r, target, depth, in_min_bucket, singleD=False, cols_info=None):
        current_split_result = {'data_rpart_l': None, 'data_rpart_r': None}
        if np.count_nonzero(target) > in_min_bucket:
            flag = True
            
            while flag:
                if depth <= self.constraints.getCstr("max_depth"):
                    current_split_result = splitting_with_depth_both(in_data_l, in_data_r, target, depth, in_min_bucket, singleD, cols_info, current_split_result, split_criterion=self.constraints.getCstr("split_criterion"))
                    # print "Round", depth, current_split_result['data_rpart_l'].tree_.feature, current_split_result['data_rpart_r'].tree_.feature
                    #Check if we have both vectors (split was successful on the left and right matrix) 
                    if current_split_result['data_rpart_l'] is None or current_split_result['data_rpart_r'] is None:
                        if depth != 2:
                            #Check if left tree was able to split
                            if current_split_result['split_vector_l'] is None:
                                current_split_result['split_vector_l'] = copy.deepcopy(previous_split_result['split_vector_l'])
                                current_split_result['data_rpart_l'] = copy.deepcopy(previous_split_result['data_rpart_l'])
                                #print("split_vector_l didn't split")
                            #Check if right tree was able to split 
                            if current_split_result['split_vector_r'] is None:
                                current_split_result['split_vector_r'] = copy.deepcopy(previous_split_result['split_vector_r'])
                                current_split_result['data_rpart_r'] = copy.deepcopy(previous_split_result['data_rpart_r'])
                                #print("split_vector_r didn't split")
                            previous_split_result = None
                        flag = False
                    else:
                        if depth==2: #depth = 2 means the first iteration, no previous results exist here. Thus, no additional checks are available
                            previous_split_result = copy.deepcopy(current_split_result)
                            depth = depth + 1
                        else:
                            #Here we have successful splits and have to check wethere trees has changed          
                            if (set(previous_split_result['split_vector_l']) == set(current_split_result['split_vector_l'])) or (set(previous_split_result['split_vector_r']) == set(current_split_result['split_vector_r'])):
                                #print("one of trees doesn't change anymore")
                                previous_split_result = None
                                flag = False
                            else:
                                previous_split_result = copy.deepcopy(current_split_result)
                                depth = depth + 1
                else:
                    flag = False
        # print "Result", current_split_result['data_rpart_l'].tree_.feature, current_split_result['data_rpart_r'].tree_.feature
        # pdb.set_trace()
        return current_split_result


def splitting_with_depth_both(in_data_l, in_data_r, in_target, in_depth, in_min_bucket, singleD=False, cols_info=None, current_split_result=None, split_criterion="gini"):
    feed_data = in_data_l.copy()
    if singleD and current_split_result['data_rpart_r'] is not None:
        if cols_info is None:
            tt = [c for c in current_split_result['data_rpart_r'].tree_.feature if c >= 0]
        else:
            # print "R", current_split_result['data_rpart_r'].tree_.feature, [c for c in current_split_result['data_rpart_r'].tree_.feature if c >= 0]
            ttm = [cols_info[1][c][1] for c in current_split_result['data_rpart_r'].tree_.feature if c >= 0]
            tt = [kk for (kk,vv) in cols_info[1].items() if vv[1] in ttm]
        feed_data[:,tt] = 0.
    
    data_rpart_l = tree.DecisionTreeClassifier(criterion= split_criterion, max_depth = in_depth, min_samples_leaf = in_min_bucket, random_state=0)
    data_rpart_l = data_rpart_l.fit(feed_data, in_target)
    
    #Form Vectors for computing Jaccard. The same vectors are used to form new targets
    split_vector_l = data_rpart_l.predict(in_data_l) #Binary vector of the left tree for Jaccard
    
    if (len(set(split_vector_l)) <= 1):
        split_vector_l = None
        split_vector_r = None
        data_rpart_l = None
        data_rpart_r = None
    else:

        feed_data = in_data_r.copy()
        if singleD:
            if cols_info is None:
                tt = [c for c in data_rpart_l.tree_.feature if c >= 0]
            else:
                # print "L", data_rpart_l.tree_.feature, [c for c in data_rpart_l.tree_.feature if c >= 0]
                ttm = [cols_info[0][c][1] for c in data_rpart_l.tree_.feature if c >= 0]
                tt = [kk for (kk,vv) in cols_info[0].items() if vv[1] in ttm]
            feed_data[:,tt] = 0.
        target = split_vector_l
    
        data_rpart_r = tree.DecisionTreeClassifier(criterion= split_criterion, max_depth = in_depth, min_samples_leaf = in_min_bucket, random_state=0)
        data_rpart_r = data_rpart_r.fit(feed_data, target)
        
        #Form Vectors for computing Jaccard. The same vectors are used to form new targets
        split_vector_r = data_rpart_r.predict(in_data_r) #Binary vector of the left tree for Jaccard
    
        if (len(set(split_vector_r)) <= 1):
            split_vector_r = None
            data_rpart_r = None
    result = {'split_vector_l': split_vector_l, 'split_vector_r' : split_vector_r,
              'data_rpart_l' : data_rpart_l, 'data_rpart_r' : data_rpart_r}
    return result 
