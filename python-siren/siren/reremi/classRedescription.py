import re, string, numpy, codecs
from classQuery import  *
from classSParts import  SParts, tool_pValSupp, tool_pValOver
from classBatch import Batch
import toolRead
import pdb

ACTIVE_RSET_ID = "S0"
SIDE_CHARS = {0:"L", 1:"R"}
NUM_CHARS = dict([(numpy.base_repr(ii, base=26), "%s" % chr(ii+ord("a"))) for ii in range(26)])

def digit_to_char(n):
    tmp = "".join([NUM_CHARS[t] for t in numpy.base_repr(n, base=26)])
    # print "%s -> %s" % (n, tmp)
    return tmp

def var_ltx_cmd(sid, vid):
    if sid in SIDE_CHARS:
        schar = SIDE_CHARS[sid]
    else:
        schar = digit_to_char(sid)
    vchar = digit_to_char(vid)
    return "\\v%sHS%s" % (schar.upper(), vchar.lower())

class Redescription(object):

    diff_score = Query.diff_length + 1
    print_delta_fields = set(SParts.print_delta_fields+["Tex_"+s for s in SParts.print_delta_fields])
    print_queries_headers = ["query_LHS", "query_RHS"]
    print_queries_namedsuff = "_named"
    print_default_fields_stats = ["acc", "pval", "card_alpha", "card_beta", "card_gamma", "card_delta"]
    print_default_fields_supp = ["alpha", "beta", "gamma"] #, "delta"]

    print_default_fields = print_queries_headers+print_default_fields_stats
    # ["query_LHS", "query_RHS", "acc", "pval", "card_alpha", "card_beta", "card_gamma", "card_delta"]
    print_default_fields_named = [p+print_queries_namedsuff for p in print_queries_headers]+print_default_fields_stats
    #["query_LHS_named", "query_RHS_named", "acc", "pval", "card_alpha", "card_beta", "card_gamma", "card_delta"]
    print_info_tex = [("acc", 3, "$%1.3f$"), ("card_gamma", 0, "$%i$"), ("pval", 3, "$%1.3f$")]

    print_fields_details = {}
    for sideq in print_queries_headers:
        print_fields_details[sideq] = (sideq, "", "%s" )
        print_fields_details[sideq+print_queries_namedsuff] = (sideq+print_queries_namedsuff, "", "%s" )
        for style in ["U", "Tex"]:
            print_fields_details[style+"_"+sideq] = (style+"_"+sideq, style, "%s" )
            print_fields_details[style+"_"+sideq+print_queries_namedsuff] = (style+"_"+sideq+print_queries_namedsuff, style, "%s" )
    for pif in SParts.print_iinfo:
        print_fields_details[pif] = (pif, None, "%d" )
    for pif in SParts.print_finfo:
        print_fields_details[pif] = (pif, None, "%f" )
    for pif in SParts.print_sinfo:
        print_fields_details[pif] = (pif, " ", "%s" )
    for pit in print_info_tex:
        print_fields_details["Tex_"+pit[0]] = pit

    print_fields_details["ratio_acc"] = ("ratio_acc", None, "%f")
    print_fields_details["Tex_ratio_acc"] = ("ratio_acc", 3, "$%1.3f$")
    print_fields_details["status_enabled"] = ("status_enabled", None, "%d")
    print_fields_details["track"] = ("track", ",", "%s")
    
    def __init__(self, nqueryL=None, nqueryR=None, nsupps = None, nN = -1, nPrs = [-1,-1], ssetts=None):
        self.resetRestrictedSuppSets()
        self.queries = [nqueryL, nqueryR]
        if nsupps is not None:
            self.sParts = SParts(ssetts, nN, nsupps, nPrs)
            self.dict_supp_info = None
        else:
            self.sParts = None
            self.dict_supp_info = {}
        self.lAvailableCols = [None, None]
        self.vectorABCD = None
        self.status = 1
        self.track = []

    def fromInitialPair(initialPair, data):
        if initialPair[0] is None and initialPair[1] is None:
            return None
        supps_miss = [set(), set(), set(), set()]
        queries = [None, None]
        for side in [0,1]:
            suppS, missS = (set(), set())
            if type(initialPair[side]) is Query:
                queries[side] = initialPair[side]
                suppS, missS = initialPair[side].recompute(side, data)
            else:
                queries[side] = Query()
                if type(initialPair[side]) is Literal:
                    queries[side].extend(None, initialPair[side])                
                    suppS, missS = data.literalSuppMiss(side, initialPair[side])
            supps_miss[side] = suppS
            supps_miss[side+2] = missS
        r = Redescription(queries[0], queries[1], supps_miss, data.nbRows(), [len(supps_miss[0])/float(data.nbRows()),len(supps_miss[1])/float(data.nbRows())], data.getSSetts())
        r.track = [(-1, -1)]
        if data.hasLT():
            r.setRestrictedSupp(data)
        return r
    fromInitialPair = staticmethod(fromInitialPair)

    def fromQueriesPair(queries, data):
        r = Redescription(queries[0].copy(), queries[1].copy())
        r.recompute(data)
        r.track = [tuple([0] + sorted(r.queries[0].invCols())), tuple([1] + sorted(r.queries[1].invCols()))]
        return r
    fromQueriesPair = staticmethod(fromQueriesPair)

    def getInfoDict(self, with_delta=False, rset_id=None):
        if self.dict_supp_info is not None and self.sParts is not None:
            if (rset_id is not None and "rset_id" not in self.dict_supp_info) or \
                   (rset_id is None and "rset_id" in self.dict_supp_info):
                #### if there is a dict_supp_info but it does not correspond to the one requested, erase
                self.dict_supp_info = None
        
        if self.dict_supp_info is None and self.sParts is not None:
            if rset_id in self.restricted_sets and self.restricted_sets[rset_id]["sParts"] is not None:
                self.dict_supp_info = self.restricted_sets[rset_id]["sParts"].toDict(with_delta)
                self.dict_supp_info["rset_id"] = rset_id
            else:
                self.dict_supp_info = self.sParts.toDict(with_delta)
        if self.dict_supp_info is not None:
            self.dict_supp_info["track"] = self.track
            return self.dict_supp_info
        return {}

    def dropSupport(self):
        if self.sParts is not None:
            self.dict_supp_info.toDict()
            self.sParts = None

    def compare(self, y):
        if self.score() > y.score():
            return Redescription.diff_score
        elif self.score() == y.score():
            return Query.comparePair(self.queries[0], self.queries[1], y.queries[0], y.queries[1])
        else:
            return -Redescription.diff_score

    def interArea(self, redB, side):
        if redB is not None:
            return len(redB.supp(side) & self.supp(side))* len(redB.invColsSide(side) & self.invColsSide(side))
        return 0
    def unionArea(self, redB, side):
        if redB is not None:
            return len(redB.supp(side) | self.supp(side))* len(redB.invColsSide(side) | self.invColsSide(side))
        return 0
    def overlapAreaSide(self, redB, side):
        if len(redB.invColsSide(side) & self.invColsSide(side)) == 0:
            return 0
        areaU = self.unionArea(redB, side)
        if areaU != 0:
            return self.interArea(redB, side) / float(areaU)
        return 0
    def overlapAreaTotal(self, redB):
        areaUL = self.unionArea(redB, 0)
        areaUR = self.unionArea(redB, 1)
        if areaUL+areaUR != 0:
            return (self.interArea(redB, 0) + self.interArea(redB, 1)) / float(areaUL+areaUR)
        return 0
    def overlapAreaL(self, redB):
        return self.overlapAreaSide(redB, 0)
    def overlapAreaR(self, redB):
        return self.overlapAreaSide(redB, 1)
    def overlapAreaMax(self, redB):
        return max(self.overlapAreaSide(redB, 0), self.overlapAreaSide(redB, 1))

    def overlapRows(self, redB):
        if redB is not None:
            return len(redB.getSuppI() & self.getSuppI())/float(min(redB.getLenI(), self.getLenI()))
        return 0
    
    def oneSideIdentical(self, redescription):
        return self.queries[0] == redescription.queries[0] or self.queries[1] == redescription.queries[1]
    def bothSidesIdentical(self, redescription):
        return self.queries[0] == redescription.queries[0] and self.queries[1] == redescription.queries[1]

    def equivalent(self, y):
       return abs(self.compare(y)) < Query.diff_balance
        
    # def __hash__(self):
    #      return int(hash(self.queries[0])+ hash(self.queries[1])*100*self.score())
        
    def __len__(self):
        return self.length(0) + self.length(1)

    def usesOr(self, side=None):
        if side is not None:
            return self.queries[side].usesOr()
        return self.queries[0].usesOr() or self.queries[1].usesOr()

    def supp(self, side):
        return self.sParts.supp(side)

    def miss(self, side):
        return self.sParts.miss(side)
            
    def score(self):
        return self.getAcc()

    def supports(self):
        return self.sParts

    def partsAll(self):
        return self.sParts.sParts

    def partsFour(self):
        return [self.sParts.suppA(), self.sParts.suppB(), self.sParts.suppI(), self.sParts.suppO()]

    def partsThree(self):
        return [self.sParts.suppA(), self.sParts.suppB(), self.sParts.suppI()]
    
    def partsNoMiss(self):
        return self.sParts.sParts[:4]
    
    def query(self, side=None):
        return self.queries[side]

    def getQueries(self):
        return self.queries

    def probas(self):
        return self.sParts.probas()

    def probasME(self, dbPrs, epsilon=0):
        return [self.queries[side].probaME(dbPrs, side, epsilon) for side in [0,1]]

    def surpriseME(self, dbPrs, epsilon=0):
        #return [-numpy.sum(numpy.log(numpy.absolute(SParts.suppVect(self.sParts.nbRows(), self.sParts.suppSide(side), 0) - self.queries[side].probaME(dbPrs, side)))) for side in [0,1]]
        return -numpy.sum(numpy.log(numpy.absolute(SParts.suppVect(self.sParts.nbRows(), self.sParts.suppI(), 0) - self.queries[0].probaME(dbPrs, 0)*self.queries[1].probaME(dbPrs, 1))))

    def exME(self, dbPrs, epsilon=0):
        prs = [self.queries[side].probaME(dbPrs, side, epsilon) for side in [0,1]]
        surprises = []
        tmp = [i for i in self.sParts.suppI() if prs[0][i]*prs[1][i] == 0]
        surprises.append(-numpy.sum(numpy.log([prs[0][i]*prs[1][i] for i in self.sParts.suppI()])))
        surprises.extend([-numpy.sum(numpy.log([prs[side][i] for i in self.sParts.suppSide(side)])) for side in [0,1]])

        return surprises + [len(tmp) > 0]

        N = self.sParts.nbRows()
        margsPr = [numpy.sum([prs[side][i] for i in self.sParts.suppSide(side)]) for side in [0,1]]
        pvals = [tool_pValOver(self.sParts.lenI(), N, int(margsPr[0]), int(margsPr[1])), tool_pValSupp(N, self.sParts.lenI(), margsPr[0]*margsPr[1]/N**2)]
        return surprises, pvals
    
    def length(self, side):
        return len(self.queries[side])
        
    def availableColsSide(self, side, deps = None, single_dataset=False):
        if self.lAvailableCols[side] is not None and self.length(1-side) != 0:
            tt = set(self.lAvailableCols[side])
	    if single_dataset:
		tt &= set(self.lAvailableCols[1-side])
            if deps is not None and len(deps) > 0:
                tn = tt
                excl = set()
                for c in self.queries[1-side].invCols():
                    excl |= deps[c]
                tt = [t for t in tn if len(deps[t] & excl) == 0]                
            return tt
        return set() 
    def nbAvailableCols(self):
        if self.lAvailableCols[0] is not None and self.lAvailableCols[1] is not None:
            return len(self.lAvailableCols[0]) + len(self.lAvailableCols[1])
        return -1
    def updateAvailable(self, souvenirs):
        nb_extensions = 0
        for side in [0, 1]:
            if self.lAvailableCols[side] is None or len(self.lAvailableCols[side]) != 0:
                self.lAvailableCols[side] =  souvenirs.availableMo[side] - souvenirs.extOneStep(self, side)
                nb_extensions += len(souvenirs.availableMo[side]) - self.length(side) - len(self.lAvailableCols[side])
        return nb_extensions
    def removeAvailables(self):
        self.lAvailableCols = [set(),set()]

    def update(self, data=None, side= -1, opBool = None, literal= None, suppX=None, missX=None):
        if side == -1 :
            self.removeAvailables()
        else:
            op = Op(opBool)
            self.queries[side].extend(op, literal)
            self.sParts.update(side, op.isOr(), suppX, missX)
            self.dict_supp_info = None
            if self.lAvailableCols[side] is not None:
                self.lAvailableCols[side].remove(literal.colId())
            self.track.append(((1-side) * 1-2*int(op.isOr()), literal.colId()))

    def setFull(self, max_var=None):
        if max_var is not None:
            for side in [0,1]:
                if self.length(side) >= max_var[side]:
                    self.lAvailableCols[side] = set()
                
    def kid(self, data, side= -1, op = None, literal= None, suppX= None, missX=None):
        kid = self.copy()
        kid.update(data, side, op, literal, suppX, missX)
        return kid
            
    def copy(self):
        r = Redescription(self.queries[0].copy(), self.queries[1].copy(), \
                             self.sParts.supparts(), self.sParts.nbRows(), self.probas(), self.sParts.getSSetts())
        for side in [0,1]:
            if self.lAvailableCols[side] is not None:
                r.lAvailableCols[side] = set(self.lAvailableCols[side])
        r.status = self.status
        r.track = list(self.track)
        return r

    def recomputeQuery(self, side, data= None, restrict=None):
        return self.queries[side].recompute(side, data, restrict)
    
    def invLiteralsSide(self, side):
        return self.queries[side].invLiterals()

    def invLiterals(self):
        return [self.invLiteralsSide(0), self.invLiteralsSide(1)]
    
    def invColsSide(self, side):
        return self.queries[side].invCols()

    def invCols(self):
        return [self.invColsSide(0), self.invColsSide(1)]
        
    def setRestrictedSupp(self, data):
        ### USED TO BE STORED IN: self.restrict_sub, self.restricted_sParts, self.restricted_prs = None, None, None
        self.setRestrictedSuppSets(data, supp_sets=None)

    def resetRestrictedSuppSets(self):
        self.restricted_sets = {}

    def setRestrictedSuppSets(self, data, supp_sets=None):
        self.dict_supp_info = None
        if supp_sets is None:
            if data.hasLT():
                supp_sets = data.getLT()
            else:
                supp_sets = {ACTIVE_RSET_ID: data.nonselectedRows()}
        for sid, sset in supp_sets.items():
            if len(sset) == 0:
                self.restricted_sets[sid] = {"sParts": None,
                                             "prs": None,
                                             "rids": set()}
            elif sid not in self.restricted_sets or self.restricted_sets[sid]["rids"] != sset:
                (nsuppL, missL) = self.recomputeQuery(0, data, sset)
                (nsuppR, missR) = self.recomputeQuery(1, data, sset)
                if len(missL) + len(missR) > 0:
                    rsParts = SParts(data.getSSetts(), sset, [nsuppL, nsuppR, missL, missR])
                else:
                    rsParts = SParts(data.getSSetts(), sset, [nsuppL, nsuppR])

                self.restricted_sets[sid] = {"sParts": rsParts,
                                             "prs": [self.queries[0].proba(0, data, sset),
                                                     self.queries[1].proba(1, data, sset)],
                                             "rids": set(sset)}
            
    def getNormalized(self, data=None, side=None):
        if side is not None:
            sides = [side]
        else:
            sides = [0,1]
        queries = [self.queries[side] for side in [0,1]]
        c = [False, False]
        for side in sides:
            queries[side], c[side] = self.queries[side].algNormalized()
        if c[0] or c[1]:
            red = Redescription.fromQueriesPair(queries, data)
            ### check that support is same
            # if self.supports() != red.supports():
            #     print "ERROR ! SUPPORT CHANGED WHEN NORMALIZING..."
            #     pdb.set_trace()
            return red, True            
        else:
            return self, False

        
    def recompute(self, data):
        (nsuppL, missL) = self.recomputeQuery(0, data)
        (nsuppR, missR) = self.recomputeQuery(1, data)
#        print self.disp()
#        print ' '.join(map(str, nsuppL)) + ' \t' + ' '.join(map(str, nsuppR))
        if len(missL) + len(missR) > 0:
            self.sParts = SParts(data.getSSetts(), data.nbRows(), [nsuppL, nsuppR, missL, missR])
        else:
            self.sParts = SParts(data.getSSetts(), data.nbRows(), [nsuppL, nsuppR])
        self.prs = [self.queries[0].proba(0, data), self.queries[1].proba(1, data)]
        if data.hasLT():
            self.setRestrictedSupp(data)
        self.dict_supp_info = None

    def check(self, data):
        result = 0
        details = None
        if self.sParts is not None:
            (nsuppL, missL) = self.recomputeQuery(0, data)
            (nsuppR, missR) = self.recomputeQuery(1, data)
            
            details = ( len(nsuppL.symmetric_difference(self.sParts.supp(0))) == 0, \
                     len(nsuppR.symmetric_difference(self.sParts.supp(1))) == 0, \
                     len(missL.symmetric_difference(self.sParts.miss(0))) == 0, \
                     len(missR.symmetric_difference(self.sParts.miss(1))) == 0 )        
            result = 1
            for detail in details:
                result*=detail
        return (result, details)

    def hasMissing(self):
        return self.sParts.hasMissing()

    def getStatus(self):
        return self.status

    def flipEnabled(self):
        self.status = -self.status

    def setEnabled(self):
        self.status = 1
    def setDisabled(self):
        self.status = -1

    def setDiscarded(self):
        self.status = -2

    ##### GET FIELDS INFO INVOLVING ADDITIONAL DETAILS (PRIMARILY FOR SIREN)
    def getQueriesU(self, details=None):
        if details is not None and "names" in details:
            return self.queries[0].disp(details["names"][0], style="U") + "---" + self.queries[1].disp(details["names"][1], style="U")
        else:
            return self.queries[0].disp(style="U") + "---" + self.queries[1].disp(style="U")

    def getQueryLU(self, details=None):
        if details is not None and "names" in details:
            return self.queries[0].disp(details["names"][0], style="U") #, unicd=True)
        else:
            return self.queries[0].disp(style="U")

    def getQueryRU(self, details=None):
        if details is not None and "names" in details:
            return self.queries[1].disp(details["names"][1], style="U") #, unicd=True)
        else:
            return self.queries[1].disp(style="U")

    def getTrack(self, details=None):
        if details is not None and ( details.get("aim", None) == "list" or details.get("format", None) == "str"):
            return ";".join(["%s:%s" % (t[0], ",".join(map(str,t[1:]))) for t in self.track])
        else:
            return self.track

    def getSortAble(self, details=None):
        if details.get("aim") == "sort":
            return (self.status, details.get("id", "?"))
        return ""

    def getShortRid(self, details=None):
        return "R%s" % details.get("id", "?")

    def getEnabled(self, details=None):
        return 1*(self.status>0)

    def getRSet(self, details=None):
        if details is not None and details.get("rset_id") in self.restricted_sets:
            return self.restricted_sets[details.get("rset_id")]
        elif ACTIVE_RSET_ID in self.restricted_sets:
            return self.restricted_sets[ACTIVE_RSET_ID]
        else:
            return None

    def getRSetParts(self, details=None):
        if details is not None and details.get("rset_id") in self.restricted_sets:
            return self.restricted_sets[details.get("rset_id")]["sParts"]
        elif ACTIVE_RSET_ID in self.restricted_sets:
            return self.restricted_sets[ACTIVE_RSET_ID]["sParts"]
        else:
            return self.sParts


    def getAccRatio(self, details=None):
        if details is not None and details.get("rset_id_num") in self.restricted_sets \
               and details.get("rset_id_den") in self.restricted_sets:
            acc_num = self.restricted_sets[details.get("rset_id_num")]["sParts"].acc()
            acc_den = self.restricted_sets[details.get("rset_id_den")]["sParts"].acc()
            if acc_den == 0:
                return float('Inf')
            return acc_num/acc_den
        return 1.

    def getAcc(self, details=None):
        return self.getRSetParts(details).acc()

    def getPVal(self, details=None):
        return self.getRSetParts(details).pVal()

    def getRoundAcc(self, details=None):
        return round(self.getAcc(details), 3)

    def getRoundPVal(self, details=None):
        return round(self.getPVal(details), 3)

    def getRoundAccRatio(self, details=None):
        return round(self.getAccRatio(details), 3)


    def getLenI(self, details=None):
        return self.getRSetParts(details).lenI()
    def getLenU(self, details=None):
        return self.getRSetParts(details).lenU()
    def getLenL(self, details=None):
        return self.getRSetParts(details).lenL()
    def getLenR(self, details=None):
        return self.getRSetParts(details).lenR()
    def getLenO(self, details=None):
        return self.getRSetParts(details).lenO()
    def getLenT(self, details=None):
        return self.getRSetParts(details).lenT()
    def getLenA(self, details=None):
        return self.getRSetParts(details).lenA()
    def getLenB(self, details=None):
        return self.getRSetParts(details).lenB()
    
    def getSuppI(self, details=None):
        return self.getRSetParts(details).suppI()
    def getSuppU(self, details=None):
        return self.getRSetParts(details).suppU()
    def getSuppL(self, details=None):
        return self.getRSetParts(details).suppL()
    def getSuppR(self, details=None):
        return self.getRSetParts(details).suppR()
    def getSuppO(self, details=None):
        return self.getRSetParts(details).suppO()
    def getSuppT(self, details=None):
        return self.getRSetParts(details).suppT()
    def getSuppA(self, details=None):
        return self.getRSetParts(details).suppA()
    def getSuppB(self, details=None):
        return self.getRSetParts(details).suppB()


##### PRINTING AND PARSING METHODS
    #### FROM HERE ALL PRINTING AND READING
    def __str__(self):
        str_av = ["?", "?"]
        for side in [0,1]:
            if self.availableColsSide(side) is not None:
                str_av[side] = "%d" % len(self.availableColsSide(side))
        return ('%s + %s terms:' % tuple(str_av)) + ('\t (%i): %s\t%s\t%s\t%s' % (len(self), self.queries[0].disp(), self.queries[1].disp(), self.disp(list_fields=["acc", "card_gamma", "pval"], sep=" "), self.getTrack({"format":"str"})))

    def dispHeader(list_fields=None, sep="\t", named=False):
        if list_fields is None:
            if named:
                list_fields = Redescription.print_default_fields_named
            else:
                list_fields = Redescription.print_default_fields
        return sep.join(list_fields)
    dispHeader = staticmethod(dispHeader)

    def formatDetails(info_tmp, list_fields, with_fname=False):
        details = []
        for info_key in list_fields:
            if type(info_key) is tuple:
                if len(info_key) > 1:
                    info_lbl = info_key[1]
                else:
                    info_lbl = None #info_key[0]
                info_key = info_key[0]
            else:
                info_lbl = None #info_key
            tmp = "-"
            if info_key in Redescription.print_fields_details:
                info_name, info_round, info_format = Redescription.print_fields_details[info_key]
                if info_lbl is None:
                    info_lbl = info_name
                try:
                    if info_lbl in info_tmp:
                        if type(info_round) is int:
                            tmp = info_format % round(info_tmp[info_lbl], info_round)
                        else:
                            if type(info_tmp[info_lbl]) in [list, set]:
                                tmp = info_format % (info_round.join(map(str, info_tmp[info_lbl])))
                            else:
                                tmp = info_format % info_tmp[info_lbl]
                except Exception:
                    tmp = "-"
            if with_fname:
                info_lbl = info_lbl+":"
            else:
                info_lbl = ""
            details.append(info_lbl+tmp)
        return details
    formatDetails = staticmethod(formatDetails)
    
    def prepareQueries(self, list_fields, names=[None, None]):
        info_tmp = {}
        for side, query_f in enumerate(Redescription.print_queries_headers):
            for style in ["", "U", "Tex"]:
                if len(style) > 0:
                    tmp_f = style +"_"+query_f
                else:
                    tmp_f = query_f
                if tmp_f in list_fields:
                    info_tmp[tmp_f] = self.queries[side].disp(style=style)
                        
                if (tmp_f + Redescription.print_queries_namedsuff ) in list_fields and ( names[side] is not None or tmp_f not in list_fields):
                    info_tmp[tmp_f + Redescription.print_queries_namedsuff] = self.queries[side].disp(names=names[side], style=style)
        return info_tmp
    

    def disp(self, names= [None, None], lenIndex=0, list_fields=None, sep="\t", with_fname=False):
        if list_fields is None:
            if names[0] is not None or names[1] is not None:
                list_fields = Redescription.print_default_fields_named
            else:
                list_fields = Redescription.print_default_fields
        info_tmp = self.getInfoDict(with_delta = len(Redescription.print_delta_fields.intersection(list_fields)) > 0)
        info_tmp["status_enabled"] = self.status
        for side, query_f in enumerate(Redescription.print_queries_headers):
            for style in ["", "U", "Tex"]:
                if len(style) > 0:
                    tmp_f = style +"_"+query_f
                else:
                    tmp_f = query_f
                if tmp_f in list_fields:
                    info_tmp[tmp_f] = self.queries[side].disp(style=style)
                        
                if (tmp_f + Redescription.print_queries_namedsuff ) in list_fields and ( names[side] is not None or tmp_f not in list_fields):
                    info_tmp[tmp_f + Redescription.print_queries_namedsuff] = self.queries[side].disp(names=names[side], style=style)

        details = []
        for info_key in list_fields:
            tmp = "-"
            if info_key in Redescription.print_fields_details:
                info_name, info_round, info_format = Redescription.print_fields_details[info_key]
                try:
                    if info_name in info_tmp:
                        if type(info_round) is int:
                            tmp = info_format % round(info_tmp[info_name], info_round)
                        else:
                            if type(info_tmp[info_name]) in [list, set]:
                                tmp = info_format % (info_round.join(map(str, info_tmp[info_name])))
                            else:
                                tmp = info_format % info_tmp[info_name]
                except Exception:
                    tmp = "-"
            if with_fname:
                info_name = info_name+":"
            else:
                info_name = ""
            details.append(info_name+tmp)
            
        ex_str = sep.join(details)
        #### SPREAD ON TWO LINES 
        # ex_str = "%s & & %s & %s \\\\ %% & %s\n & \\multicolumn{2}{r}{ %s } \\\\ [.3em]" % (details[0], details[2], details[3], details[4], details[1])
        return ex_str

    def dispQueries(self, names=[None,None], sep='\t'):
        if names[0] is not None or names[1] is not None:
            list_fields = Redescription.print_default_fields_named
        else:
            list_fields = Redescription.print_default_fields
        return self.disp(list_fields=list_fields, sep=sep, names=names)

    def dispStats(self, sep='\t'):
        return self.disp(list_fields=Redescription.print_default_fields_stats, sep=sep)
        
    def dispSupp(self):
        return self.sParts.dispSupp()
    
    def write(self, output, suppOutput, namesOutput=None, names=None, addto=''):
        output.write(self.disp()+addto+'\n')
        output.flush()
        if namesOutput is not None and names is not None:
            namesOutput.write(self.disp(names)+addto+'\n')
            namesOutput.flush()
        if suppOutput is not None:
            suppOutput.write(self.sParts.dispSupp()+'\n')
            suppOutput.flush()
            
    ################# START FOR BACKWARD COMPATIBILITY WITH XML
    def fromXML(self, node):
        self.queries = [None, None]
        dsi = {}
        for query_data in node.getElementsByTagName("query"):
            side = toolRead.getTagData(query_data, "side", int)
            if side not in [0,1]:
                print "Unknown side (%s)!" % side
            else:
                query_tmp = toolRead.getTagData(query_data, "ids_expression")
                self.queries[side] = Query.parseApd(query_tmp)
        supp_tmp = node.getElementsByTagName("support")
        self.track = [tuple([0] + sorted(self.queries[0].invCols())), tuple([1] + sorted(self.queries[1].invCols()))]
        if len(supp_tmp) == 1:
            for child in toolRead.children(supp_tmp[0]):
                if toolRead.isElementNode(child):
                    supp_key = toolRead.tagName(child)
                    supp_val = None
                    if child.hasChildNodes():
                        supp_val = toolRead.getValues(child, int, "row")
                    else:
                        supp_val = toolRead.getValue(child, float)
                    if supp_val is not None:
                        dsi[supp_key] = supp_val
            self.sParts = None # SParts(None, dsi)
            self.dict_supp_info = dsi
        tmp_en = toolRead.getTagData(node, "status_enabled", int)
        if tmp_en is not None:
            self.status = tmp_en
    ################# END FOR BACKWARD COMPATIBILITY WITH XML

    def parseHeader(string, sep=None):
        if sep is None:
            seps = ["\t", ",", ";"]
        else:
            seps = [sep]
        for ss in seps:
            fields = [s.strip() for s in string.split(ss)]
            if all([len([f for f in fields if re.match("%s(%s)?" % (h, Redescription.print_queries_namedsuff), f)]) > 0 for h in Redescription.print_queries_headers]):
                return fields, ss
        return None, None
    parseHeader = staticmethod(parseHeader)    

    def parseQueries(string, list_fields=None, sep="\t", names=[None, None]):
        if type(string) is str:
            string = codecs.decode(string, 'utf-8','replace')
            
        if list_fields is None:
            list_fields = Redescription.print_default_fields
        poplist_fields = list(list_fields) ### to pop out the query fields...

        queries = [None, None]
        lpartsList = {}
        
        parts = string.rsplit(sep)
        for part in parts:
            str_top = None
            tmp = part.split(":")
            if len(tmp) == 2:
                if tmp[0] in poplist_fields:
                    key_info =  tmp[0].strip()
                    str_top =  tmp[1].strip()
                else:
                    key_info = None
            else:
                str_top = part.strip()
                if len(poplist_fields) > 0:
                    key_info = poplist_fields[0]
                else:
                    key_info = None ### or raise Error number of fields mismatch?

            if key_info in Redescription.print_fields_details:
                fname, info_round, info_format = Redescription.print_fields_details[key_info]
                poplist_fields.remove(key_info) ### consume the token
            else:
                continue
                
            if fname in [k+Redescription.print_queries_namedsuff for k in Redescription.print_queries_headers]:
                side = 1
                if fname == Redescription.print_queries_headers[0]+Redescription.print_queries_namedsuff:
                    side = 0
                #### named query, try to parse if no alternative
                print names[side], str_top, type(str_top)
                if Redescription.print_queries_headers[side] not in list_fields and names[side] is not None: 
                    try:
                        query = Query.parse(str_top, names[side])
                    except Exception as e:
                         raise Warning("Failed parsing named query %d, %s !:\n\t%s" % (side, str_top, e) )
                    # except UnicodeDecodeError:
                    #      pdb.set_trace()

                    if query is not None:
                        queries[side] = query

            elif fname in Redescription.print_queries_headers:
                side = 1
                if fname == Redescription.print_queries_headers[0]:
                    side = 0
                try:
                    query = Query.parse(str_top)
                    if query is not None:
                        queries[side] = query
                except Exception as e:
                    raise Warning("Failed parsing query %d, %s !:\n\t%s" % (side, str_top, e) )

            else:
                if type(info_round) is str:
                    if len(str_top.strip()) == 0:
                        lpartsList[fname] = []
                    else:
                        lpartsList[fname] = map(int, str_top.strip().split(info_round))
                else:
                    try:
                        lpartsList[fname] = int(str_top)
                    except ValueError:
                        try:
                            lpartsList[fname] = float(str_top)
                        except ValueError:
                            lpartsList[fname] = str_top
                    
        for side in [0, 1]:
            if queries[side] is None:
                queries[side] =  Query()
        if len(lpartsList) == 0:
            lpartsList = None
        return (queries[0], queries[1], lpartsList)
    parseQueries = staticmethod(parseQueries)

    def parse(stringQueries, stringSupport = None, data = None, list_fields=None, sep="\t"):
        if data is not None and data.hasNames():
            names = data.getNames()
        else:
            names = [None, None]
        (queryL, queryR, lpartsList) = Redescription.parseQueries(stringQueries, list_fields, sep, names)
        status_enabled = None
        if "status_enabled" in lpartsList:
            status_enabled = lpartsList.pop("status_enabled")
        r = None
        if data is not None and stringSupport is not None and type(stringSupport) == str and re.search('\t', stringSupport) :
            supportsS = SParts.parseSupport(stringSupport, data.nbRows(), data.getSSetts())
            if supportsS is not None:
                r = Redescription(queryL, queryR, supportsS.supparts(), data.nbRows(), [set(),set()], [ queryL.proba(0, data), queryR.proba(1, data)], data.getSSetts())

                tmp = r.getInfoDict()
                for key in lpartsList.keys():
                    if tmp.get(key, None) != lpartsList[key]:
                        raise Warning("Something wrong in the supports ! (%s: %s ~ %s)\n" \
                                  % (key, tmp.get(key, None), lpartsList[key]))

        if r is None:
            r = Redescription(queryL, queryR)
            if data is not None:
                r.recompute(data)
            else:
                r.supp_info = lpartsList
        if r is not None and status_enabled is not None:
            r.status = status_enabled
        return r
    parse = staticmethod(parse)
  
    def load(queriesFp, supportsFp = None, data= None):
        stringQueries = queriesFp.readline()
        if len(stringQueries) == 0:
            return (None, -1, -1)
        indComm = stringQueries.find('#')
        comment = ''
        if indComm != -1 :
            comment = stringQueries[indComm:].rstrip()
            stringQueries = stringQueries[:indComm]
        
        if type(supportsFp) == file :
            stringSupp = supportsFp .readline()
            indComm = stringSupp.find('#')
            commentSupp = ''
            if indComm != -1 :
                commentSupp = stringSupp[indComm:].rstrip()
                stringSupp = stringSupp[:indComm]

        else: stringSupp= None; commentSupp = ''
        return (Redescription.parse(stringQueries, stringSupp, data), comment, commentSupp)
    load = staticmethod(load)

def printTexRedList(red_list, names=[None, None], fields=None):
    tex_fields = ["Tex_query_LHS_named", "Tex_query_RHS_named", "Tex_acc", "Tex_card_gamma", "Tex_pval"]
    tex_headers = ["$q_\\iLHS$","$q_\\iRHS$","$\\jacc(R)$","$\\supp(R)$", "\\pValue"]

    if type(fields) is list and len(fields) > 0:
        if fields[0] == -1:
            tex_fields.extend(fields[1:])
            tex_headers.extend(fields[1:])
        else:
            tex_fields = fields
            tex_headers = list(fields)
    names_alts = []
    names_commands = ""
    numvs_commands = ""
    for i, ns in enumerate(names):
        if ns is not None:
            names_alts.append([])
            for ni, n in enumerate(ns):
                vlc = var_ltx_cmd(i, ni)
                names_alts[i].append("$"+vlc+"{}$")
                names_commands += "\\newcommand{%s}{\\text{%s}}\n" % (vlc, re.sub("_", "\\_", n))
                numvs_commands += "%% \\newcommand{%s}{\\text{v%d}}\n" % (vlc, ni)
        else:
            names_alts.append(None)
                
    str_out = "" + \
              "\\documentclass{article}\n"+ \
              "\\usepackage{amsmath}\n"+ \
              "\\usepackage{amsfonts}\n"+ \
              "\\usepackage{amssymb}\n"+ \
              "\\usepackage{booktabs}\n"+ \
              "\\usepackage[mathletters]{ucs}\n"+ \
              "\\usepackage[utf8x]{inputenc}\n"+ \
              "\\newcommand{\\iLHS}{\\mathbf{L}} % index for left hand side\n"+ \
              "\\newcommand{\\iRHS}{\\mathbf{R}} % index for right hand side\n"+ \
              "\\newcommand{\\pValue}{$p$\\nobreakdash-\\hspace{0pt}value}\n"+ \
              "\\DeclareMathOperator*{\\jacc}{J}\n"+ \
              "\\DeclareMathOperator*{\\supp}{supp}\n"+ \
              names_commands+ \
              numvs_commands+ \
              "\\begin{document}\n"+ \
              "\\begin{table}[h]\n"+ \
              "\\scriptsize\n" + \
              "\\begin{tabular}{@{\\hspace*{1ex}}p{0.027\\textwidth}@{}p{0.35\\textwidth}@{\\hspace*{1em}}p{0.4\\textwidth}@{\\hspace*{1em}}rrr@{\\hspace*{0.5ex}}}\n" + \
              "\\toprule\n"
              #### SPREAD ON TWO LINES 
              # "\\begin{tabular}{@{\\hspace*{1ex}}r@{\\hspace*{1ex}}p{0.75\\textwidth}@{}r@{\\hspace*{4ex}}r@{\\hspace*{2ex}}r@{\\hspace*{1ex}}}\n" + \

            
    str_out += " & " + Redescription.dispHeader(tex_headers, " & ") + " \\\\\n"
    str_out += "%%% & " + Redescription.dispHeader(tex_fields, " & ") + " \\\\\n"
    #### SPREAD ON TWO LINES 
    # str_out += " & " + Redescription.dispHeader(tex_headers[:-1], " & ") + " \\\\ %% &"+ tex_headers[-1] +" \n"
    # str_out += "%%% & " + Redescription.dispHeader(tex_fields[:-1], " & ") + " \\\\ %% &"+ tex_fields[-1] +" \n"
    str_out += "\\midrule\n"
    for ri, red in enumerate(red_list):

        str_out += '(%i) & ' % ri
        str_out += red.disp(names_alts, list_fields=tex_fields, sep=" & ") + " \\\\\n" # 

    str_out += "" + \
        "\\bottomrule\n"+ \
        "\\end{tabular}\n"+ \
        "\\end{table}\n"+ \
        "\\end{document}"
    return str_out

def printRedList(red_list, names=[None, None], fields=None, full_supp=False):
    all_fields = list(Redescription.print_default_fields)
    if names[0] is not None or names[1] is not None:
        all_fields = Redescription.print_default_fields_named
    if type(fields) is list and len(fields) > 0:
        if fields[0] == -1:
            all_fields.extend(fields[1:])
        else:
            all_fields = fields
    if full_supp:
        all_fields.extend(Redescription.print_default_fields_supp)
    str_out = Redescription.dispHeader(all_fields, "\t") + "\n"
    for ri, red in enumerate(red_list):
        str_out += red.disp(list_fields=all_fields, names=names, sep="\t")  + "\n"
    return str_out

def parseRedList(fp, data, reds=None):
    list_fields = None
    more = []
    if reds is None:
        reds = []
    lid = 0
    for line in fp:
        lid += 1
        if len(line.strip()) > 0 and not re.match("^[ \t]*#", line):
            if list_fields is None:
                list_fields, sep = Redescription.parseHeader(line)
            else:                    
                r = Redescription.parse(line, data=data, list_fields=list_fields, sep=sep)
                if r is not None:
                    reds.append(r)
                    more.append(line)
    return reds, {"fields": list_fields, "sep": sep, "lines": more}

if __name__ == '__main__':
    from classData import Data
    from classQuery import Query
    import sys

    rep = "/home/galbrun/TKTL/redescriptors/data/37billionmiles/"
    data = Data([rep+"vehicules_out.csv", rep+"grid250m_attributes_out.csv", {}, "NA"], "csv")

    filename = "/home/galbrun/TKTL/redescriptors/sandbox/runs/37billionmiles/37billionmiles_1.queries"
    filep = open(filename, mode='r')

    reds = Batch([])
    parseRedList(filep, data, reds)
    for red in reds:
        print red.disp()

    exit()
    rep = "/home/galbrun/TKTL/redescriptors/data/vaalikone/"
    data = Data([rep+"vaalikone_profiles_test.csv", rep+"vaalikone_questions_test.csv", {}, "NA"], "csv")

    reds = []
    with codecs.open("../../bazar/queries.txt", encoding='utf-8', mode='r') as f:
        for line in f:
            if len(line.strip().split("\t")) >= 2:
                try:
                    tmpLHS = Query.parse(line.strip().split("\t")[0], data.getNames(0))
                    tmpRHS = Query.parse(line.strip().split("\t")[1], data.getNames(1))
                except:
                    continue
                r = Redescription.fromQueriesPair([tmpLHS, tmpRHS], data)
                reds.append(r)

    with codecs.open("../../bazar/queries_list2.txt", encoding='utf-8', mode='w') as f:
        f.write(printRedList(reds))

    with codecs.open("../../bazar/queries_list2.txt", encoding='utf-8', mode='r') as f:
        reds, _ = parseRedList(f, data)

    for red in reds:
        print red.disp()
