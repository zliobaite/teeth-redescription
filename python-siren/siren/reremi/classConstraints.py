from classRedescription import  Redescription
import numpy
import pdb

class Constraints(object):
    
    #     self.cminPairsScore = setts_cust.param['min_score']        
    config_def = "miner_confdef.xml"
    special_cstrs = {}
    
    def __init__(self, data, params):
        self.deps = []
        self.folds = None
        self._pv = {}
        for k, v in params.items():
            self._pv[k] = v["data"]

        if data is not None:
            self.N = data.nbRows()
            if data.hasMissing() is False:
                self._pv["parts_type"] = "grounded"

            data.getSSetts().reset(self.getCstr("parts_type"), self.getCstr("method_pval"))
            self.ssetts = data.getSSetts() 
        else:
            self.N = -1
            self.ssetts = None

        if self.getCstr("amnesic") == "yes":
            self._pv["amnesic"] = True
        else:
            self._pv["amnesic"] = False

        #### scaling support thresholds
        self._pv["min_itm_c"], self._pv["min_itm_in"], self._pv["min_itm_out"] = self.scaleSuppParams(self.getCstr("min_itm_c"), self.getCstr("min_itm_in"), self.getCstr("min_itm_out"))
        _, self._pv["min_fin_in"], self._pv["min_fin_out"] = self.scaleSuppParams(-1, self.getCstr("min_fin_in"), self.getCstr("min_fin_out"))
        
        #### preparing query types
        for side_id in [0, 1]:
            for type_id in [1,2,3]:
                kp = "neg_query_s%d_%d" % (side_id, type_id)
                self._pv[kp] = []
                for v in params.get(kp, {"value": []})["value"]:
                    self._pv[kp].append(bool(v))
                    
            kp = "ops_query_s%d" % side_id
            self._pv[kp] = []
            for v in params.get(kp, {"value": []})["value"]:
                self._pv[kp].append(bool(v))

        #### preparing score coeffs
        self._pv["score_coeffs"] = {"impacc": self.getCstr("score.impacc", default=0),
                                 "rel_impacc": self.getCstr("score.rel_impacc", default=0),
                                 "pval_red": self.getCstr("score.pval_red", default=0),
                                 "pval_query": self.getCstr("score.pval_query", default=0),
                                 "pval_fact": self.getCstr("score.pval_fact", default=0)}


        #### preparing action registry
        self._actions = {
        "nextge": [("filtersingle", {"filter_funct": self.filter_nextge}),
                   ("sort", {"sort_funct": self.sort_nextge, "sort_reverse": True }),
                   ("cut", { "cutoff_nb": self.getCstr("batch_cap"), "cutoff_direct": 0})],
        "partial":[("filtersingle", {"filter_funct": self.filter_partial}),
                   ("sort", {"sort_funct": self.sort_partial, "sort_reverse": True }),
                   ("filterpairs", {"filter_funct": self.pair_filter_partial, "filter_max": 0}),
                   ("cut", { "cutoff_nb": self.getCstr("batch_out"), "cutoff_direct": 1, "equal_funct": self.sort_partial})],
        "final":  [("filtersingle", {"filter_funct": self.filter_final}),
                   ("sort", {"sort_funct": self.sort_partial, "sort_reverse": True }),
                   ("filterpairs", {"filter_funct": self.pair_filter_partial, "filter_max": 0})],
        "redundant": [("filterpairs", self.getFilterParams("redundant"))],
        "folds": [("filtersingle", {"filter_funct": self.filter_folds})]}

        
    def setFolds(self, data):
        fcol = data.getColsByName("^folds_split_")
        if len(fcol) == 1:
            self.folds = data.getFoldsStats(fcol[0][0], fcol[0][1])
        
    def scaleF(self, f):
        if f == -1 or f is None:
            return -1
        if f >= 1:
            return int(f)
        elif f >= 0 and f < 1 and self.N != 0:
            return  int(round(f*self.N))
        return 0
    def scaleSuppParams(self, min_c, min_in=None, min_out=None):
        sc_min_c = self.scaleF(min_c)
        if min_in == -1:
            sc_min_in = sc_min_c
        else:
            sc_min_in = self.scaleF(min_in)
        if min_out == -1:
            sc_min_out = sc_min_in
        else:
            sc_min_out = self.scaleF(min_out)
        return (sc_min_c, sc_min_in, sc_min_out)


    def getSSetts(self):
        return self.ssetts
    def getCstr(self, k, **kargs):
        if k in self.special_cstrs:
            return eval("self.%s" % self.special_cstrs[k])(**kargs)
            
        k_bak = k 
        if "side" in kargs:
            k += "_s%d" % kargs["side"]
        if "type_id" in kargs:
            k += "_%d" % kargs["type_id"]

        if k in self._pv:
            return self._pv[k]
        else:
            return self._pv.get(k_bak, kargs.get("default"))

    #### special constraints (not just lookup)    
    def allw_ops(self, side, init=False):
        if init > 0:
            return [True]
        else:
            tmp = self.getCstr("ops_query", side=side)
            if init < 0 and self._pv["single_side_or"]=="yes":
                tmp = [o for o in tmp if not o]
            return tmp
    special_cstrs["allw_ops"] = "allw_ops"

    def getActions(self, k):
        return self._actions.get(k, [])
        
    def getFilterParams(self, k):
        if k == "redundant":                 
            if self.getCstr("max_overlaparea") < 0:
                return {"filter_funct": self.pair_filter_redundant_rows, "filter_thres": -(self.getCstr("max_overlaparea") or 1), "filter_max":0}
            return {"filter_funct": self.pair_filter_redundant, "filter_thres": (self.getCstr("max_overlaparea") or 1), "filter_max":0}
       # possibly useful functions for reds comparison:
       # they should be symmetric
       #     .oneSideIdentical(self.batch[compare])
       #     .equivalent(self.batch[compare])
       #     .redundantArea(self.batch[compare])

        
    ##### filtering and sorting primitives   
    def filter_nextge(self, red):
        ### could add check disabled
        return red.nbAvailableCols() == 0

    def sort_nextge(self, red):
        return red.getAcc()

    def sort_partial(self, red):
        return (red.getAcc(), -(red.length(0) + red.length(1)), -abs(red.length(0) - red.length(1)))  
                 
    def filter_partial(self,red):
        # print "filter partial", red
        # print {'min_itm_out': red.getLenO() >= self.getCstr("min_itm_out"),
        #        'min_itm_in': red.getLenI() >= self.getCstr("min_itm_in"),
        #        'max_fin_pval': red.getPVal() <= self.getCstr("max_fin_pval")}
        # print {'min_itm_out': (red.getLenO(), self.getCstr("min_itm_out")),
        #        'min_itm_in': (red.getLenI(), self.getCstr("min_itm_in")),
        #        'max_fin_pval': (red.getPVal(), self.getCstr("max_fin_pval"))}

        if red.getLenO() >= self.getCstr("min_itm_out")\
               and red.getLenI() >= self.getCstr("min_itm_in") \
               and red.getPVal() <= self.getCstr("max_fin_pval"):
            # Constraints.logger.printL(3, 'Redescription complies with final constraints ... (%s)' %(red))
            # print "--------- RED KEEP"
            return False
        else:
            # Constraints.logger.printL(3, 'Redescription non compliant with final constraints ...(%s)' % (red))
            return True

    def filter_final(self,red):
        # print "filter final", red
        # print {'min_fin_var': red.length(0) + red.length(1) >= self.getCstr("min_fin_var"),
        #        'min_fin_out': red.getLenO() >= self.getCstr("min_fin_out"),
        #        'min_fin_in': red.getLenI() >= self.getCstr("min_fin_in"),
        #        'min_fin_acc': red.getAcc()  >= self.getCstr("min_fin_acc"),
        #        'max_fin_pval': red.getPVal() <= self.getCstr("max_fin_pval")}
        # print {'min_fin_var': (red.length(0) + red.length(1), self.getCstr("min_fin_var")),
        #        'min_fin_out': (red.getLenO(), self.getCstr("min_fin_out")),
        #        'min_fin_in': (red.getLenI(), self.getCstr("min_fin_in")),
        #        'min_fin_acc': (red.getAcc(), self.getCstr("min_fin_acc")),
        #        'max_fin_pval': (red.getPVal(), self.getCstr("max_fin_pval"))}


        if red.length(0) + red.length(1) >= self.getCstr("min_fin_var") \
                   and red.getLenO() >= self.getCstr("min_fin_out")\
                   and red.getLenI() >= self.getCstr("min_fin_in") \
                   and red.getAcc()  >= self.getCstr("min_fin_acc") \
                   and red.getPVal() <= self.getCstr("max_fin_pval"):
            # Constraints.logger.printL(3, 'Redescription complies with final constraints ... (%s)' %(red))
            # print "--------- RED KEEP"
            return False
        else:
            # Constraints.logger.printL(3, 'Redescription non compliant with final constraints ...(%s)' % (red))
            return True

    def pair_filter_partial(self, redA, redB):
        return (redA.oneSideIdentical(redB) and not redA.equivalent(redB)) or redA.bothSidesIdentical(redB)

    def pair_filter_redundant(self, redA, redB):
        return redA.overlapAreaMax(redB)

    def pair_filter_redundant_rows(self, redA, redB):
        return redA.overlapRows(redB)
    
   
    def filter_folds(self, red):
       if self.folds is None:
           return False

       bcountI = numpy.bincount(self.folds["folds"][list(red.getSuppI())], minlength=self.folds["nb_folds"])
       bcountU = numpy.bincount(self.folds["folds"][list(red.getSuppU())], minlength=self.folds["nb_folds"])
       bcountU[bcountU == 0] = 1
       accs = bcountI/(1.*bcountU)
       print "--------------------"
       print red.disp()
       print accs
       if len(numpy.where(accs >= red.getAcc())[0]) > 1:
           return False
           bb = accs # bcount/self.folds["counts_folds"]
           # bpr = bcount/float(numpy.sum(bcount))
           # entropS = -numpy.sum(numpy.log(bpr)*bpr)
           bpr = bb/numpy.max(bb)
           score = numpy.sum(bpr)
           print score
           # entropM = -numpy.sum(numpy.log(bpr)*bpr)
           if score > 1.5:
               return False
       return True

   
    #### Dependencies between variables (ex, single dataset)
    def setDeps(self, deps=[]):
       self.deps = deps

    def getDeps(self, col=None):
        if col is None:
            return self.deps
        else:
            return self.deps[col]

    def hasDeps(self):
        return len(self.deps) > 0

    
