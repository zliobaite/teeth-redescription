import random, os.path, re
from toolLog import Log
from classRedescription import Redescription
from classBatch import Batch
from classExtension import ExtensionError, ExtensionsBatch
from classSouvenirs import Souvenirs
from classConstraints import Constraints
from classInitialPairs import InitialPairs
from classData import BoolColM, CatColM, NumColM

import numpy

import pdb

from classCharbonGMiss import CharbonGMiss
from classCharbonGStd import CharbonGStd
from classCharbonTAlt import CharbonTCW, CharbonTSprit, CharbonTSplit
from classCharbonTLayer import CharbonTLayer

TREE_CLASSES = { "layeredtrees": CharbonTLayer,
                 "cartwheel": CharbonTCW,
                 "splittrees": CharbonTSplit,
                 "sprit": CharbonTSprit}
TREE_DEF = CharbonTLayer

# PAIR_LOADS = [[1,2,3],
#               [2,4,6],
#               [3,6,10]]

class DummyLog(object):
    verbosity = 0
    def printL(self, level, message, type_message="*", source=None):
        pass
    def updateProgress(self, details, level=-1, id=None):
        pass


class ExpMiner(object):
    def __init__(self, ppid, count, data, charbon, constraints, souvenirs, logger=None, question_live=None):
        self.charbon = charbon
        self.data = data
        self.count = count
        self.ppid = ppid
        self.constraints = constraints
        self.souvenirs = souvenirs
        self.upSouvenirs = False
        self.question_live = question_live
        if logger is None:
            self.logger = DummyLog()
        else:
            self.logger = logger

    def questionLive(self):
        if self.question_live is None:
            return True
        return self.question_live()

    def expandRedescriptions(self, nextge, partial=None, final=None):
        if len(nextge) > 0 and self.questionLive():
            if partial is not None:
                partial["results"] = []
                partial["batch"].reset()
            else:
                partial = {"results":[], "batch": Batch()}
            partial["batch"].extend(nextge)
            if self.charbon.isTreeBased():
                return self.expandRedescriptionsTree(nextge, partial, final)
            else:
                return self.expandRedescriptionsGreedy(nextge, partial, final)

    def expandRedescriptionsTree(self, nextge, partial, final=None):
        for redi, red in enumerate(nextge):
            self.logger.printL(2, "Expansion %s.%s\t%s" % (self.count, redi, red), 'status', self.ppid)
            new_red = self.charbon.getTreeCandidates(-1, self.data, red.copy())
            if new_red is not None:
                partial["batch"].append(new_red)

            # self.logger.updateProgress({"rcount": self.count, "redi": redi}, 4, self.ppid)
            self.logger.printL(4, "Candidate %s.%d.%d grown" % (self.count, len(red), redi), 'status', self.ppid)

        self.logger.printL(4, "Generation %s.%d expanded" % (self.count, len(red)), 'status', self.ppid)
        self.logger.printL(1, {"partial":partial["batch"]}, 'result', self.ppid)

        ### Do before selecting next gen to allow tuning the beam
        ### ask to update results
        if 1 in partial["batch"].selected(self.constraints.getActions("partial")):
            addR = True
            ii = 0
            if final is not None:
                while addR and ii < len(final["batch"]):
                ### check identity
                    addR = (partial["batch"][1].supp(0) != final["batch"][ii].supp(0) or
                            partial["batch"][1].supp(1) != final["batch"][ii].supp(1) or
                            partial["batch"][1].invColsSide(0) != final["batch"][ii].invColsSide(0) or
                            partial["batch"][1].invColsSide(1) != final["batch"][ii].invColsSide(1))
                    ii += 1
            if addR:
                partial["results"].append(1)
        self.logger.printL(1, {"partial":partial["batch"]}, 'result', self.ppid)
        self.logger.printL(1, "%d redescriptions selected" % len(partial["results"]), 'status', self.ppid)
        for red in partial["results"]:
            self.logger.printL(2, "--- %s" % partial["batch"][red])
        return partial
        

    def expandRedescriptionsGreedy(self, nextge, partial, final=None):
        first_round = True
        while len(nextge) > 0:
            kids = set()
            redi = 0

            while redi < len(nextge):
                red = nextge[redi]
                if first_round:
                    self.logger.printL(2, "Expansion %s.%s\t%s" % (self.count, redi, red), 'status', self.ppid)
                ### To know whether some of its extensions were found already
                nb_extensions = red.updateAvailable(self.souvenirs)

                if red.nbAvailableCols() > 0:
                    bests = ExtensionsBatch(self.data.nbRows(), self.constraints.getCstr("score_coeffs"), red)
                    for side in [0,1]:
                    ##for side in [1]:
                        ### check whether we are extending a redescription with this side empty
                        if red.length(side) == 0:
                            init = 1
                        else:
                            init = red.usesOr(1-side)*-1 
                        for v in red.availableColsSide(side, self.constraints.getDeps(), self.data.single_dataset):
                            if not self.questionLive():
                                nextge = []
                        
                            else:
                                bests.update(self.charbon.getCandidates(side, self.data.col(side, v), red.supports(), init))

                    if self.logger.verbosity >= 4:
                        self.logger.printL(4, bests, "log", self.ppid)

                    try:
                        kids = bests.improvingKids(self.data, self.constraints.getCstr("min_impr"),
                                                   [self.constraints.getCstr("max_var", side=0), self.constraints.getCstr("max_var", side=1)])

                    except ExtensionError as details:
                        self.logger.printL(1,"OUILLE! Something went badly wrong during expansion of %s.%d.%d\n--------------\n%s\n--------------" % (self.count, len(red), redi, details.value), "log", self.ppid)
                        kids = []

                    partial["batch"].extend(kids)
                    ## SOUVENIRS
                    if self.upSouvenirs:
                        self.souvenirs.update(kids)

                    ### parent has been used remove availables
                    red.removeAvailables()
                # self.logger.updateProgress({"rcount": self.count, "generation": len(red), "cand": redi}, 4, self.ppid)
                self.logger.printL(4, "Candidate %s.%d.%d expanded" % (self.count, len(red), redi), 'status', self.ppid)
                redi += 1

            first_round = False
            self.logger.printL(4, "Generation %s.%d expanded" % (self.count, len(red)), 'status', self.ppid)
            nextge_keys = partial["batch"].selected(self.constraints.getActions("nextge"))
            nextge = [partial["batch"][i] for i in nextge_keys]

            partial["batch"].applyFunctTo(".removeAvailables()", nextge_keys, complement=True)
            self.logger.printL(1, {"partial":partial["batch"]}, 'result', self.ppid)

        ### Do before selecting next gen to allow tuning the beam
        ### ask to update results
        partial["results"] = partial["batch"].selected(self.constraints.getActions("partial"))
        self.logger.printL(1, {"partial":partial["batch"]}, 'result', self.ppid)
        self.logger.printL(1, "%d redescriptions selected" % len(partial["results"]), 'status', self.ppid)
        for red in partial["results"]:
            self.logger.printL(2, "--- %s" % partial["batch"][red])
        return partial


class Miner(object):

### INITIALIZATION
##################
    def __init__(self, data, params, logger=None, mid=None, souvenirs=None, qin=None, cust_params={}):
        self.qin = qin
        self.org_data = None
        self.want_to_live = True
        if mid is not None:
            self.id = mid
        else:
            self.id = 1
        self.data = data

        self.max_processes = params["nb_processes"]["data"]
        self.pe_balance = params["pe_balance"]["data"]

        #### SETTING UP DATA
        row_ids = None
        if "area" in cust_params:
            inw, outw = cust_params.get("in_weight", 1), cust_params.get("out_weight", 1)
            if "in_weight" in params:
                inw = params["in_weight"]["data"]
            if "out_weight" in params:
                outw = params["out_weight"]["data"]
            weights = dict([(r,outw) for r in range(self.data.nbRows())])
            for old in cust_params["area"]:
                weights[old] = inw
            cust_params["weights"] = weights

        keep_rows = None
        if self.data.hasSelectedRows() or self.data.hasLT():
            keep_rows = self.data.getVizRows({"rset_id": "learn"})
            if "weights" not in cust_params:
                row_ids = dict([(v,[k]) for (k,v) in enumerate(keep_rows)])
            
        if "weights" in cust_params:
            row_ids = {}
            off = 0
            for (old, mul) in cust_params["weights"].items():
                if keep_rows is None or old in keep_rows:
                    row_ids[old] = [off+r for r in range(mul)]
                    off += mul

        if row_ids is not None:
            self.org_data = self.data
            self.data = self.data.subset(row_ids)


        if logger is not None:
            self.logger = logger
        else:
             self.logger = Log()       
        self.constraints = Constraints(self.data, params)

        self.charbon = self.initCharbon()
        if souvenirs is None:
            self.souvenirs = Souvenirs(self.data.usableIds(self.constraints.getCstr("min_itm_c"), self.constraints.getCstr("min_itm_c")), self.constraints.getCstr("amnesic"))
        else:
            self.souvenirs = souvenirs

        pairs_store = None
        if "pairs_store" in params and len(params["pairs_store"]["data"]) > 0:
            pairs_store = params["pairs_store"]["data"]
        self.initial_pairs = InitialPairs(self.constraints.getCstr("pair_sel"), self.constraints.getCstr("max_red"), save_filename=pairs_store)
        
        self.partial = {"results":[], "batch": Batch()}
        self.final = {"results":[], "batch": Batch()}

        ### Dependencies between variables 
        deps = []
        if self.data.hasNames():
            names = self.data.getNames()
            if len(names[0]) == len(names[1]) and re.search("^.* \[\[(?P<deps>[0-9,]*)\]\]$", names[0][0]) is not None:
                for name in names[0]:
                    deps.append(set(map(int, re.search("^.* \[\[(?P<deps>[0-9,]*)\]\]$", name).group("deps").split(","))))
        self.constraints.setDeps(deps)

    def initCharbon(self):
        if self.constraints.getCstr("algo_family") == "trees":
            if self.data.hasMissing():
                self.logger.printL(1, "THE DATA CONTAINS MISSING VALUES, FALLING BACK TO GREEDY...", 'log', self.id)
                return CharbonGStd(self.constraints)
            else:
                return TREE_CLASSES.get(self.constraints.getCstr("tree_mine_algo"), TREE_DEF)(self.constraints)

        else:
            if self.data.hasMissing():
                return CharbonGMiss(self.constraints)
            else:
                return CharbonGStd(self.constraints)

                            
    def kill(self):
        self.want_to_live = False

    def questionLive(self):
        if self.want_to_live and self.qin is not None:
            try:
                piece_result = self.qin.get_nowait()
                if piece_result["type_message"] == "progress" and piece_result["message"] == "stop":
                    self.want_to_live = False
            except:
                pass
        return self.want_to_live

### RUN FUNCTIONS
################################

    def filter_run(self, redescs):
        batch = Batch(redescs)
        tmp_ids = batch.selected(self.constraints.getActions("redundant"))
        #tmp_ids = batch.selected(self.constraints.getActions("final"))
        return [batch[i] for i in tmp_ids]

    def part_run(self, cust_params):
        if "reds" in cust_params:
            reds = cust_params["reds"]
        elif "red" in cust_params:
            reds = [cust_params["red"]]
        else:
            reds = []
        if self.org_data is not None:
            for red in reds:
                red.recompute(self.data)

        if "side" in cust_params:
            self.souvenirs.cutOffSide(1-cust_params["side"])

        self.count = "C"

        self.logger.initProgressPart(self.constraints, self.souvenirs, reds, 1, self.id)
        self.logger.clockTic(self.id, "part run")        
        self.logger.printL(1, "Expanding...", 'status', self.id) ### todo ID

        partial = self.expandRedescriptions(reds)

        self.logger.clockTac(self.id, "part run", "%s" % self.questionLive())        
        if not self.questionLive():
            self.logger.printL(1, 'Interrupted...', 'status', self.id)
        else:
            self.logger.printL(1, 'Done...', 'status', self.id)
        self.logger.sendCompleted(self.id)
        return partial

    def full_run(self, cust_params={}):
        self.final["results"] = []
        self.final["batch"].reset()
        self.count = 0
        
        self.logger.printL(1, "Starting mining", 'status', self.id) ### todo ID
        #### progress initialized after listing pairs
        self.logger.clockTic(self.id, "pairs")
        self.initializeRedescriptions()
        self.logger.clockTac(self.id, "pairs")
        self.logger.clockTic(self.id, "full run")
        initial_red = self.initial_pairs.get(self.data, self.testIni)
        while initial_red is not None and self.questionLive():
            self.count += 1
            self.logger.clockTic(self.id, "expansion_%d-%d" % (self.count,0))
            self.logger.printL(1,"Expansion %d" % self.count, "log", self.id)
            partial = self.expandRedescriptions([initial_red])
            self.logger.updateProgress({"rcount": self.count}, 1, self.id)
            ## SOUVENIRS self.souvenirs.update(partial["batch"])

            
            # self.logger.clockTic(self.id, "select")        
            added = []
            if partial is not None:
                added = [len(self.final["batch"])+ i for i in range(len(partial["results"]))]
                self.final["batch"].extend([partial["batch"][i] for i in partial["results"]])
            self.final["results"] = self.final["batch"].selected(self.constraints.getActions("final"), ids=self.final["results"]+added, new_ids=added)
            # self.final["results"] = self.final["batch"].selected(self.constraints.getActions("final"))
            # if (self.final["results"] != ttt):
            #     pdb.set_trace()
            #     print "Not same"
            ### DEBUG self.final["results"] = range(len(self.final["batch"]))
            # self.logger.clockTac(self.id, "select")

            self.logger.clockTac(self.id, "expansion_%d-%d" % (self.count,0), "%s" % self.questionLive())
            self.logger.printL(1, {"final": self.final["batch"]}, 'result', self.id)
            initial_red = self.initial_pairs.get(self.data, self.testIni)

        self.logger.clockTac(self.id, "full run", "%s" % self.questionLive())        
        if not self.questionLive():
            self.logger.printL(1, 'Interrupted...', 'status', self.id)
        else:
            self.logger.printL(1, 'Done...', 'status', self.id)
        self.logger.sendCompleted(self.id)
        return self.final


### HIGH LEVEL CALLING FUNCTIONS
################################

####################################################
#####      INITIAL PAIRS
####################################################

    def initializeRedescriptions(self, ids=None):
        self.initial_pairs.reset()
        if self.charbon.isTreeBased():
            self.initializeRedescriptionsTree(ids)
        else:
            self.initializeRedescriptionsGreedy(ids)

    def initializeRedescriptionsTree(self, ids=None):
        self.logger.printL(1, 'Searching for initial literals...', 'status', self.id)
        self.logger.initProgressFull(self.constraints, self.souvenirs, None, 1, self.id)
        
        if ids is None:
            ids = self.data.usableIds(self.constraints.getCstr("min_itm_c"), self.constraints.getCstr("min_itm_c"))

        sides = [0,1]
        if self.data.isSingleD(): sides = [0]
        for side in sides:
            for idl in ids[side]:
                for (l,v) in self.charbon.computeInitTerm(self.data.col(side, idl)):
                    if side == 0:
                        self.initial_pairs.add(l, None, {"score":v, side: idl, 1-side: -1})
                    else:
                        self.initial_pairs.add(None, l, {"score":v, side: idl, 1-side: -1})
        ## UNLIMITED PAIRS FOR TREES?
        # self.initial_pairs.setMaxOut(-1)
        self.logger.printL(1, 'Found %i literals' % (len(self.initial_pairs)), "log", self.id)
        # self.logger.sendCompleted(self.id)

        
    def initializeRedescriptionsGreedy(self, ids=None):
        self.initial_pairs.reset()

        ##### SELECTION USING FOLDS
        # folds = numpy.array(self.data.cols[0][-1].getVector())
        # counts_folds = 1.*numpy.bincount(folds) 
        # nb_folds = len(counts_folds)
        
        ### Loading pairs from file if filename provided
        loaded, done = self.initial_pairs.loadFromFile()
        if not loaded or done is not None:

            self.logger.printL(1, 'Searching for initial pairs...', 'status', self.id)
            explore_list = self.getInitExploreList(ids, done)
            self.logger.initProgressFull(self.constraints, self.souvenirs, explore_list, 1, self.id)

            self.initial_pairs.setExploreList(explore_list, done=done)
            total_pairs = len(explore_list)
            for pairs, (idL, idR, pload) in enumerate(explore_list):
                if not self.questionLive():
                    self.initial_pairs.saveToFile()
                    return

                self.logger.updateProgress({"rcount": self.count, "pair": pairs, "pload": pload})
                if pairs % 100 == 0:
                    self.logger.printL(3, 'Searching pair %d/%d (%i <=> %i) ...' %(pairs, total_pairs, idL, idR), 'status', self.id)
                    self.logger.updateProgress(level=3, id=self.id)
                if pairs % 10 == 5:

                    self.logger.printL(7, 'Searching pair %d/%d (%i <=> %i) ...' %(pairs, total_pairs, idL, idR), 'status', self.id)
                    self.logger.updateProgress(level=7, id=self.id)

                seen = []
                (scores, literalsL, literalsR) = self.charbon.computePair(self.data.col(0, idL), self.data.col(1, idR))
                for i in range(len(scores)):
                    if scores[i] >= self.constraints.getCstr("min_pairscore") and (literalsL[i], literalsR[i]) not in seen:
                        seen.append((literalsL[i], literalsR[i]))
                        # ########
                        self.logger.printL(6, 'Score:%f %s <=> %s' % (scores[i], literalsL[i], literalsR[i]), "log", self.id)
                        self.initial_pairs.add(literalsL[i], literalsR[i], {"score": scores[i], 0: idL, 1: idR})
                        # ########
                        # ######## Filter pair candidates on folds distribution
                        # rr = Redescription.fromInitialPair((literalsL[i], literalsR[i]), self.data)
                        # bcount = numpy.bincount(folds[list(rr.getSuppI())], minlength=nb_folds)
                        # if len(numpy.where(bcount > 0)[0]) > 1:
                        #     bb = bcount/counts_folds
                        #     # bpr = bcount/float(numpy.sum(bcount))
                        #     # entropS = -numpy.sum(numpy.log(bpr)*bpr)
                        #     bpr = bb/numpy.max(bb)
                        #     score = numpy.sum(bpr)
                        #     # entropM = -numpy.sum(numpy.log(bpr)*bpr)
                        #     if score > 1.5:
                        #         self.logger.printL(6, '\tfolds count: %f, %d, %s' % (score, numpy.sum(bcount), bcount), "log", self.id)
                        #         ####
                        #         # self.initial_pairs.add(literalsL[i], literalsR[i], {"score": scores[i], 0: idL, 1: idR})
                        #         self.initial_pairs.add(literalsL[i], literalsR[i], {"score": score, 0: idL, 1: idR})
                        # # if pairs % 50 == 0 and pairs > 0:
                        # #     exit()
                self.initial_pairs.addExploredPair((idL, idR))

            self.logger.printL(1, 'Found %i pairs, will try at most %i' % (len(self.initial_pairs), self.constraints.getCstr("max_red")), "log", self.id)
            self.logger.updateProgress(level=1, id=self.id)

            ### Saving pairs to file if filename provided
            self.initial_pairs.setExploredDone()
            self.initial_pairs.saveToFile()
        else:
            self.logger.initProgressFull(self.constraints, self.souvenirs, None, 1, self.id)
            self.logger.printL(1, 'Loaded %i pairs from file, will try at most %i' % (len(self.initial_pairs), self.constraints.getCstr("max_red")), "log", self.id)
        return self.initial_pairs
    
    def testIni(self, pair):
        if pair is None:
            return False
        return True
    
    def getInitExploreList(self, ids, done=set()):
        explore_list = []
        if ids is None:
            ids = self.data.usableIds(self.constraints.getCstr("min_itm_c"), self.constraints.getCstr("min_itm_c"))

        ### WARNING DANGEROUS few pairs for DEBUG!
        for idL in ids[0]:
            for idR in ids[1]:
                if ( not self.constraints.hasDeps() or \
                       len(self.constraints.getDeps(idR) & self.constraints.getDeps(idL)) == 0) and \
                       ( not self.data.isSingleD() or idR > idL or idR not in ids[0] or idL not in ids[1]):
                    if done is None or (idL, idR) not in done:
                        explore_list.append((idL, idR, self.getPairLoad(idL, idR)))
                    else:
                        self.logger.printL(3, 'Loaded pair (%i <=> %i) ...' %(idL, idR), 'log', self.id)
        return explore_list

    def getPairLoad(self, idL, idR):
        # pdb.set_trace()
        # print idL, idR, eval("0b"+"".join(["%d" %(((idL+idR)%10)%i ==0) for i in [8,4,2]]))
        ## + ((idL + idR)%10)/1000.0
        return max(1, self.data.col(0, idL).getNbValues()* self.data.col(1, idR).getNbValues()/50) + 1./(1+((idL + idR)%10))
        ## return max(1, self.data.col(0, idL).getNbValues()* self.data.col(1, idR).getNbValues()/50)
        # return PAIR_LOADS[self.data.col(0, idL).type_id-1][self.data.col(1, idR).type_id-1]


####################################################
#####      REDS EXPANSIONS
####################################################
    def expandRedescriptions(self, nextge):
        return ExpMiner(self.id, self.count, self.data, self.charbon, self.constraints, self.souvenirs, self.logger, self.questionLive).expandRedescriptions(nextge, self.partial, self.final)

#######################################################################
########### MULTIPROCESSING MINER
#######################################################################

import multiprocessing

class MinerDistrib(Miner):

    def full_run(self, cust_params={}):
        self.final["results"] = []
        self.final["batch"].reset()
        self.count = 0
        self.reinitOnNew = False
        self.workers = {}
        self.rqueue = multiprocessing.Queue()
        self.pstopqueue = multiprocessing.Queue()
        
        self.logger.printL(1, "Starting mining", 'status', self.id) ### todo ID

        #### progress initialized after listing pairs
        self.logger.clockTic(self.id, "pairs")
        self.initializeRedescriptions()

        self.logger.clockTic(self.id, "full run")
        # if self.charbon.isTreeBased():
        self.initializeExpansions()

        self.keepWatchDispatch()
        self.logger.clockTac(self.id, "full run", "%s" % self.questionLive())        
        if not self.questionLive():
            self.logger.printL(1, 'Interrupted...', 'status', self.id)
        else:
            self.logger.printL(1, 'Done...', 'status', self.id)
        self.logger.sendCompleted(self.id)
        return self.final

    def shareLogger(self):
        if not self.logger.usesOutMethods():
            return self.logger
        return None
        
    def initializeRedescriptionsGreedy(self, ids=None):
        self.initial_pairs.reset()
        self.pairs = 0
        ### Loading pairs from file if filename provided
        loaded, done = self.initial_pairs.loadFromFile()
        if not loaded or done is not None:

            self.logger.printL(1, 'Searching for initial pairs...', 'status', self.id)
            explore_list = self.getInitExploreList(ids, done)
            self.logger.initProgressFull(self.constraints, self.souvenirs, explore_list, 1, self.id)
            self.total_pairs = len(explore_list)

            min_bsize = 25
            if self.pe_balance == 0:
                #### Finish all pairs before exhausting,
                #### split in fixed sized batches, not sorted by cost
                K = self.max_processes
                batch_size = max(self.total_pairs/(5*K), min_bsize) #self.total_pairs / (self.max_processes-1)
                ## print "Batch size=", batch_size
                pointer = 0
            else:
                #### Sort from easiest to most expensive
                tot_cost = sum([c[-1] for c in explore_list])
                explore_list.sort(key=lambda x:x[-1], reverse =True)
                thres_cost = (tot_cost/self.max_processes)*(1-self.pe_balance/10.)

                cost = 0
                off = 0
                while off < len(explore_list)-1  and cost < thres_cost:
                    off += 1
                    cost += explore_list[-off][-1]
                if len(self.initial_pairs) > off:
                    off = 0
                ## print "OFF", off
                K = self.max_processes-1
                batch_size = max((self.total_pairs-off) / K, min_bsize)

                ### Launch last worker
                if K*batch_size < len(explore_list):
                    ## print "Init PairsProcess ", K, len(explore_list[K*batch_size:])
                    self.workers[K] = PairsProcess(K, explore_list[K*batch_size:], self.charbon, self.data, self.rqueue)
                pointer = -1
                
            self.initial_pairs.setExploreList(explore_list, pointer, batch_size, done)
            ### Launch other workers
            for k in range(K):
                ll = self.initial_pairs.getExploreNextBatch(pointer=k)
                if len(ll) > 0:
                    ## print "Init PairsProcess ", k, len(ll)
                    self.workers[k] = PairsProcess(k, ll, self.charbon, self.data, self.rqueue)
                else:
                    pointer = -1
                    
            self.pairWorkers = len(self.workers)
            if pointer == 0:
                pointer = self.pairWorkers
            self.initial_pairs.setExplorePointer(pointer)
        else:
            self.initial_pairs.setExploredDone()
            self.logger.initProgressFull(self.constraints, self.souvenirs, None, 1, self.id)
            self.logger.printL(1, 'Loaded %i pairs from file, will try at most %i' % (len(self.initial_pairs), self.constraints.getCstr("max_red")), "log", self.id)
        return self.initial_pairs


    def initializeExpansions(self):
        self.reinitOnNew = False
        for k in set(range(self.max_processes)).difference(self.workers.keys()):
            initial_red = self.initial_pairs.get(self.data, self.testIni)
            if self.questionLive():
                if initial_red is None:
                    self.reinitOnNew = True
                else:
                    self.count += 1
                    self.logger.printL(1,"Expansion %d" % self.count, "log", self.id)
                    self.logger.clockTic(self.id, "expansion_%d-%d" % (self.count,k))
                    ## print "Init ExpandProcess ", k, self.count
                    self.workers[k] = ExpandProcess(k, self.id, self.count, self.data,
                                                    self.charbon, self.constraints,
                                                    self.souvenirs, self.rqueue, [initial_red],
                                                    final=self.final, logger=self.shareLogger())
       
    def handlePairResult(self, m):
        scores, literalsL, literalsR, idL, idR, pload = m["scores"], m["lLs"], m["lRs"], m["idL"], m["idR"], m["pload"]
        self.pairs += 1
        self.logger.updateProgress({"rcount": 0, "pair": self.pairs, "pload": pload})
        if self.pairs % 100 == 0:
            self.logger.printL(3, 'Searching pair %d/%d (%i <=> %i) ...' %(self.pairs, self.total_pairs, idL, idR), 'status', self.id)
            self.logger.updateProgress(level=1, id=self.id)

        if self.pairs % 10 == 5:
                            
            self.logger.printL(7, 'Searching pair %d/%d (%i <=> %i) ...' %(self.pairs, self.total_pairs, idL, idR), 'status', self.id)
            self.logger.updateProgress(level=7, id=self.id)

        added = 0
        for i in range(len(scores)):
            if scores[i] >= self.constraints.getCstr("min_pairscore"):
                added += 1
                self.logger.printL(6, 'Score:%f %s <=> %s' % (scores[i], literalsL[i], literalsR[i]), "log", self.id)
                self.initial_pairs.add(literalsL[i], literalsR[i], {"score": scores[i], 0: idL, 1: idR})
        self.initial_pairs.addExploredPair((idL, idR))
        if added > 0 and self.reinitOnNew:
            self.initializeExpansions()

    def handleExpandResult(self, m):
        added = [len(self.final["batch"])+ i for i in range(len(m["out"]["results"]))]
        self.final["batch"].extend([m["out"]["batch"][i] for i in m["out"]["results"]])

        # self.logger.clockTic(self.id, "select_%d-%d" % (m["count"], m["id"]))        
        self.final["results"] = self.final["batch"].selected(self.constraints.getActions("final"), ids=self.final["results"]+added, new_ids=added)
        # self.final["results"] = self.final["batch"].selected(self.constraints.getActions("final"))
        # self.logger.clockTac(self.id, "select_%d-%d" % (m["count"], m["id"]))

        if not self.constraints.getCstr("amnesic"):
            self.souvenirs.update(m["out"]["batch"].values())
        self.logger.clockTac(self.id, "expansion_%d-%d" % (m["count"], m["id"]), "%s" % self.questionLive())
        self.logger.printL(1, {"final":self.final["batch"]}, 'result', self.id)
        self.logger.updateProgress({"rcount": m["count"]}, 1, self.id)

    def leftOverPairs(self):
        # print "LEFTOVER", self.workers
        return self.initial_pairs.exhausted() and len(self.workers) > 0 and len([(wi, ww) for (wi, ww) in self.workers.items() if ww.isExpand()]) == 0
        
    def keepWatchDispatch(self):
        while len(self.workers) > 0 and self.questionLive():
            m = self.rqueue.get()
            if m["what"] == "done":
                ## print "Worker done", m["id"]
                del self.workers[m["id"]]

                if self.initial_pairs.getExplorePointer() >= 0:
                    ll = self.initial_pairs.getExploreNextBatch()
                    if len(ll) > 0:
                        ## print "Init Additional PairsProcess ", m["id"], self.explore_pairs["pointer"], len(ll)
                        self.workers[m["id"]] = PairsProcess(m["id"], ll, self.charbon, self.data, self.rqueue)
                        self.initial_pairs.incrementExplorePointer()
                    else:
                        self.initial_pairs.setExplorePointer(-1)

                if self.initial_pairs.getExplorePointer() == -1:
                    self.pairWorkers -= 1
                    if self.pe_balance > 0:
                        self.initializeExpansions()
                    # else:
                    #     print "Waiting for all pairs to complete..."

                if self.pairWorkers == 0:
                    self.logger.updateProgress({"rcount": 0}, 1, self.id)
                    self.logger.clockTac(self.id, "pairs")
                    self.logger.printL(1, 'Found %i pairs, will try at most %i' % (len(self.initial_pairs), self.constraints.getCstr("max_red")), "log", self.id)
                    self.logger.updateProgress(level=1, id=self.id)
                    self.initial_pairs.setExploredDone()
                    self.initial_pairs.saveToFile()
                    if self.pe_balance == 0:
                        self.initializeExpansions()
                        ## print "All pairs complete, launching expansion..."

                
            elif m["what"] == "pairs":
                self.handlePairResult(m)

            elif m["what"] == "expansion":
                self.handleExpandResult(m)
                del self.workers[m["id"]]
                self.initializeExpansions()

            if self.leftOverPairs():
                self.logger.printL(1, 'Found %i pairs, tried %i before testing all' % (len(self.initial_pairs), self.constraints.getCstr("max_red")), "log", self.id)
                self.initial_pairs.saveToFile()
                break

    
class PairsProcess(multiprocessing.Process):
    def __init__(self, sid, explore_list, charbon, data, rqueue):
        multiprocessing.Process.__init__(self)
        self.daemon = True
        self.id = sid
        self.explore_list = explore_list
        self.charbon = charbon
        self.data = data
        self.queue = rqueue
        self.start()

    def isExpand(self): ### expand or init?
        return False

    def run(self):
        for pairs, (idL, idR, pload) in enumerate(self.explore_list):
            (scores, literalsL, literalsR) = self.charbon.computePair(self.data.col(0, idL), self.data.col(1, idR))
            self.queue.put({"id": self.id, "what": "pairs", "lLs": literalsL, "lRs": literalsR, "idL": idL, "idR": idR, "scores": scores, "pload": pload})
        self.queue.put({"id": self.id, "what": "done"})

class ExpandProcess(multiprocessing.Process, ExpMiner):
    
    def __init__(self, sid, ppid, count, data, charbon, constraints, souvenirs, rqueue,
                 nextge, partial=None, final=None, logger=None,
                 question_live=None):
        multiprocessing.Process.__init__(self)
        self.daemon = True
        self.id = sid
        self.ppid = ppid
        self.count = count
        
        self.charbon = charbon
        self.data = data
        self.queue = rqueue

        self.constraints = constraints
        self.souvenirs = souvenirs
        self.upSouvenirs = False
        self.question_live = question_live
        if logger is None:
            self.logger = DummyLog()
        else:
            self.logger = logger

        self.nextge= nextge
        self.partial= partial
        self.final= final
        self.start()

    def isExpand(self): ### expand or init?
        return True

    def run(self):
        partial = self.expandRedescriptions(self.nextge, partial=self.partial, final=self.final)
        self.queue.put({"id": self.id, "what": "expansion", "out": partial, "count": self.count})



#######################################################################
########### MINER INSTANCIATION
#######################################################################

def instMiner(data, params, logger=None, mid=None, souvenirs=None, qin=None, cust_params={}):
    if params["nb_processes"]["data"] > 1:
        return MinerDistrib(data, params, logger, mid, souvenirs, qin, cust_params)
    else:
        return Miner(data, params, logger, mid, souvenirs, qin, cust_params)

class StatsMiner:
    def __init__(self, data, params, logger=None, cust_params={}):
        self.data = data
        self.params = params
        self.logger = logger
        self.cust_params = cust_params
        
    def run_stats(self):
        splits_info = self.data.getFoldsInfo()
        stored_splits_ids = sorted(splits_info["split_ids"].keys(), key=lambda x: splits_info["split_ids"][x])
        summaries = {}
        nbfolds = len(stored_splits_ids)
        for kfold in range(nbfolds):
            ids = {"learn": [], "test": []}
            for splt in range(nbfolds):
                if splt == kfold:
                    ids["test"].append(stored_splits_ids[splt])
                else:
                    ids["learn"].append(stored_splits_ids[splt])
            self.data.assignLT(ids["learn"], ids["test"])
            miner = instMiner(self.data, self.params, self.logger)
            try:
                miner.full_run()
            except KeyboardInterrupt:
                self.logger.printL(1, 'Stopped...', "log")
            
            stats = []
            reds = []
            for pos in miner.final["results"]:
                red = miner.final["batch"][pos]
                red.recompute(self.data)
                stats.append([red.getAccRatio({"rset_id_num": "test", "rset_id_den": "learn"}),
                              red.getAcc(), red.getAcc({"rset_id": "learn"}), red.getAcc({"rset_id": "test"}),
                              red.getLenI()/float(red.getLenT()),
                              red.getLenI({"rset_id": "learn"})/float(red.getLenT({"rset_id": "learn"})),
                              red.getLenI({"rset_id": "test"})/float(red.getLenT({"rset_id": "test"})),
                              red.getPVal(), red.getPVal({"rset_id": "learn"}), red.getPVal({"rset_id": "test"})])
                reds.append(red)
            summaries[kfold] = {"reds": reds, "stats": stats}

        reds_map = []
        stack_stats = []
        all_stats = {}
        for k,rr in summaries.items():
            all_stats[k] = rr["stats"]
            stack_stats.extend(rr["stats"])
            for ri, r in enumerate(rr["reds"]):
                found = None
                i = 0
                while i < len(reds_map) and found is None:
                    if reds_map[i]["red"].compare(r) == 0:
                        found = i
                    i += 1
                if found is None:
                    reds_map.append({"red": r, "pos": [(k, ri)]})
                else:
                    reds_map[i]["pos"].append((k,ri))
        reds_map.sort(key=lambda x: x["red"].getAcc(), reverse=True)
        reds_list = []
        for rr in reds_map:
            rr["red"].track = rr["pos"]
            reds_list.append(rr["red"])
        all_stats[-1] =  stack_stats
        header = ["J ratio", "J all", "J learn", "J test",
                  "E11/E all", "E11/E learn", "E11/E test",
                  "pV all", "pV learn", "pV test"]
        return reds_list, all_stats, header, summaries
