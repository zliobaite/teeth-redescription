from scipy.special import gammaln
from scipy.stats import binom
import numpy, random
import pdb

def tool_hypergeomPMF(k, M, n, N):
    tot, good = M, n
    bad = tot - good
    return numpy.exp(gammaln(good+1) - gammaln(good-k+1) - gammaln(k+1) + gammaln(bad+1) \
                              - gammaln(bad-N+k+1) - gammaln(N-k+1) - gammaln(tot+1) \
                              + gammaln(tot-N+1) + gammaln(N+1))
#same as the following but numerically more precise
#return comb(good,k) * comb(bad,N-k) / comb(tot,N)

def tool_pValOver(kInter, nbRows, suppL, suppR):
    ## probability that two sets of these size have intersection equal or larger than kInter
    return sum([ tool_hypergeomPMF(k, nbRows, suppL, suppR) for k in range(kInter, min(suppL, suppR)+1)])

def tool_pValSupp(nbRows, supp, pr):
    ## probability that an termset with marginal probability pr has support equal or larger than supp
    return 1-binom.cdf(supp-1, nbRows, pr) 

class SSetts(object):

    # labels = ['\t|  \n', '\t  |\n', '\t| |\n', '\t   \n', '\t| :\n', '\t: |\n', '\t  :\n', '\t:  \n', '\t: :\n' ]
    # labels = ['**', '__', '==', '  ', '*.', '"_', '..', '""', '::' ]
    labels = ['alpha', 'beta', 'gamma', 'delta', 'mua', 'mub', 'muaB', 'mubB', 'mud' ]
    for i, l in enumerate(labels):
        exec("%s = %d" % (l,i))

    io_labels = ["into", "out", "tot", "imiss"]
    for i, l in enumerate(io_labels):
        exec("%s = %d" % (l,i))

    # # indexes of the parts
    # (alpha, beta, gamma, delta, mua, mub, muaB, mubB, mud) = range(9)
    # (into, out, tot, imiss) = range(4)

    # (self.alpha, self.beta, self.gamma, self.delta, self.mua, self.mub, self.muaB, self.mubB, self.mud) = range(9)
    # (self.into, self.out, self.tot, self.imiss) = range(4)


    ## TRUTH TABLE:
    ## A B    OR    AND
    ## T T    T     T
    ## T F    T     F
    ## T M    T     M
    ## F F    F     F
    ## F M    M     F
    ## M M    M     M

    ## PARTS:
    ##         A  |  B
    ## ----------------
    ## alpha   T  |  F
    ## beta    F  |  T
    ## gamma   T  |  T
    ## delta   F  |  F
    ## mu_a    T  |  M
    ## mu_b    M  |  T
    ## mu_aB   F  |  M
    ## mu_bB   M  |  F
    ## mu_d    M  |  M


    def __init__(self, type_parts="none", methodpVal="Marg"):
        self.type_parts = None
        self.resetPartsIds(type_parts)
        self.setMethodPVal(methodpVal)

    def reset(self, type_parts=None, methodpVal=None):
        if type_parts is not None:
            self.resetPartsIds(type_parts)
        if methodpVal is not None:
            self.setMethodPVal(methodpVal)
        
    def resetPartsIds(self, type_parts):
        if type_parts is True:
            type_parts = "grounded"
        if type_parts is False:
            type_parts = "none"
            
        if self.type_parts == type_parts:
            return
        elif self.type_parts == "none":
            return

        self.type_parts = type_parts
        
        # indexes from the parts when looking from the right (A=L, B=R) or the left (A=R,B=L) 
        self.side_index = [[0,1,2,3,4,5,6,7,8], [1,0,2,3,5,4,7,6,8]]

        # indexes for the intersections with parts
        # (into: part inter X_True, out: part inter X_False, miss: part inter X_Missing, tot: total part = into + out + miss)
        # indexed for the intersections with parts when considering positive or negative X
        self.neg_index = [[0, 1, 2, 3], [1, 0, 2, 3]]

        ## and same for initializing relative parts
        for i, l in enumerate(self.labels):
            exec("%s = %d" % (l,i))
        for i, l in enumerate(self.io_labels):
            exec("%s = %d" % (l,i))

        # (alpha, beta, gamma, delta, mua, mub, muaB, mubB, mud) = range(9)

        if type_parts == "none":

            #####################################################################################
            ###############             WITHOUT MISSING VALUES                      #############
            #####################################################################################

            self.bottom = alpha
            self.top = delta
            ##############################################################
            #### BASIC
            ##############################################################

            ##### TO COMPUTE ADVANCE while building, INDEXED BY OPERATOR (0: AND, 1: OR)
            # Parts in numerator (BLUE), independent of X 
            self.IDS_fixnum = [[], [(tot, gamma)]]
            # Parts in numerator (BLUE), dependent of X: toBlue
            self.IDS_varnum = [[(into, gamma)] ,[(into, beta)]]
            # Parts in denominator (RED), independent of X
            self.IDS_fixden = [[(tot, gamma), (tot, beta)], [(tot, gamma), (tot, alpha), (tot, beta)]]
            # Parts in denominator (RED), dependent of X: toRed
            self.IDS_varden = [[(into, alpha)], [(into, delta)]]
            # Parts left uncovered (OUT), (always dependent of X)
            self.IDS_out = [[(out, alpha), (tot, delta)], [(out, delta)]]
            # Parts in contribution (CONT), (always dependent of X)
            # Contribution: AND entities removed from alpha, OR: entities added to gamma
            self.IDS_cont = [[(out, alpha)], [(into, beta)]]
            # Parts in the new support of the extended query
            self.IDS_nsupp = [[(into, alpha), (into, gamma)], [(tot, alpha), (tot, gamma), (into, beta), (into, delta)]]

            #### TO COMPUTE ACCURACY after building
            self.IDS_diff = [alpha, beta]
            self.IDS_dL = [alpha]
            self.IDS_dR = [beta]
            self.IDS_inter = [gamma]
            self.IDS_uncovered = [delta]

            ##############################################################

            #### TO COMPUTE SUPPORTS, no index
            self.IDS_supp = (gamma, alpha)
            self.IDS_miss = ()
            # indexes swaping when negating one side (0: negating A, 1: negating B)
            self.IDS_negated = [(delta, gamma, beta, alpha), \
                           (gamma, delta, alpha, beta)]

            #### END NO MISSING VALUES
            #####################################################################################


        else:

            #####################################################################################
            ###############                WITH MISSING VALUES                      #############
            #####################################################################################
            self.bottom = alpha
            self.top = mud
            ##############################################################
            #### GROUNDED
            ##############################################################

            if type_parts == "grounded":

                ##### TO COMPUTE ADVANCE while building, INDEXED BY OPERATOR (0: AND, 1: OR)
                # Parts in numerator (BLUE), independent of X 
                self.IDS_fixnum = [[],
                              [(tot, gamma)]]
                # Parts in numerator (BLUE), dependent of X: toBlue
                self.IDS_varnum = [[(into, gamma)] ,
                              [(into, beta), (into, mub)]]
                # Parts in denominator (RED), independent of X
                self.IDS_fixden = [[(tot, beta)],
                              [(tot, gamma), (tot, alpha)]]
                # Parts in denominator (RED), dependent of X: toRed
                self.IDS_varden = [[(into, alpha), (into, gamma), (out, gamma), (out, mub)],
                              [(into, mub), (into, mubB), (into, delta), (into, beta), (out, beta)]]

                # Parts left uncovered (OUT), (always dependent of X)
                self.IDS_out = [[(out, alpha), (out, mubB), (tot, delta)],
                           [(out, delta)]]
                # Parts in contribution (CONT), (always dependent of X)
                # Contribution: AND entities removed from alpha, OR: entities added to gamma
                self.IDS_cont = [[(out, alpha)],
                            [(into, beta), (into, mub)]]
                # Parts in the new support of the extended query
                self.IDS_nsupp = [[(into, alpha), (into, gamma)],
                             [(tot, alpha), (tot, gamma), (tot, mua), (into, mub), (into, beta), (into, delta), (into, mubB), (into, muaB), (into, mud)]]

                #### TO COMPUTE ACCURACY after building
                self.IDS_diff = [alpha, beta]
                self.IDS_dL = [alpha]
                self.IDS_dR = [beta]
                self.IDS_inter = [gamma]
                self.IDS_uncovered = [delta]


            ##############################################################
            #### OPTIMISTIC
            ##############################################################

            elif type_parts == "optimistic":

                ##### TO COMPUTE ADVANCE while building, INDEXED BY OPERATOR (0: AND, 1: OR)
                self.IDS_fixnum = [[(imiss, mua), (imiss, mub), (imiss, mud), (imiss, gamma)],
                                     [(tot, mua), (tot, gamma), (tot, mud), (tot, mub), (imiss, muaB), (imiss, beta)]]
                self.IDS_varnum = [[(into, mua), (into, gamma), (into, mub), (into, mud)],
                                     [(into, muaB), (into, beta), (imiss, muaB), (imiss, beta)]]
                self.IDS_fixden = [[(tot, gamma), (tot, mub), (tot, beta)],
                                     [(tot, mua), (tot, gamma), (tot, mub), (tot,  mud), (imiss, muaB), (tot, beta), (tot, alpha)]]
                self.IDS_varden = [[(into, alpha), (into, mua), (into, mud), (imiss, mua), (imiss, mud)],
                                     [(into, delta), (into, mubB), (into, muaB)]]

                self.IDS_out = [[(out, alpha), (imiss, alpha), (out, mua), (tot, delta), (tot, mubB), (out, mud), (tot, muaB)],
                                  [(out, delta), (imiss, delta), (out, mubB), (imiss,mubB), (out,muaB)]]
                self.IDS_cont = [[(out, alpha)],
                                   [(into, beta), (into, mub)]]
                self.IDS_nsupp = [[(into, alpha), (into, mua), (into, gamma), (into, mub), (into, mud)],
                                    [(tot, alpha), (tot, gamma), (tot, mua), (into, mub), (into, beta), (into, delta), (into, mubB), (into, mud), (into, muaB)]]

                #### TO COMPUTE ACCURACY after building
                self.IDS_diff = [alpha, beta]
                self.IDS_dL = [alpha]
                self.IDS_dR = [beta]
                self.IDS_inter = [gamma, mub, mua, mud]
                self.IDS_uncovered = [delta, mubB, muaB]


            ##############################################################
            #### PESSIMISTIC
            ##############################################################

            elif type_parts == "pessimistic":

                ##### TO COMPUTE ADVANCE while building, INDEXED BY OPERATOR (0: AND, 1: OR)
                self.IDS_fixnum = [[],
                                     [(tot, gamma)]]
                self.IDS_varnum = [[(into, gamma)] ,
                                     [(into, beta), (into, mub)]]
                self.IDS_fixden = [[(imiss, alpha), (tot, mua), (tot, gamma), (tot, mub), (tot, beta), (imiss, mubB), (tot, mud), (tot, muaB)],
                                     [(tot, gamma), (tot, alpha), (tot, beta), (tot, mua), (tot, muaB), (tot, mub), (tot, mubB), (tot, mud)]]
                self.IDS_varden = [[(into, alpha), (into, mubB)],
                                     [(into, delta), (imiss, delta)]]

                self.IDS_out = [[(out, alpha), (out, mubB), (tot, delta)],
                                  [(out, delta)]]
                self.IDS_cont = [[(out, alpha)],
                                   [(into, beta), (into, mub)]]
                self.IDS_nsupp = [[(into, alpha), (into, gamma), (into, mua)],
                                    [(tot, alpha), (tot, gamma), (tot, mua), (into, mub), (into, beta), (into, delta), (into, mubB), (into, mud)]]

                #### TO COMPUTE ACCURACY after building
                self.IDS_diff = [alpha, beta, mub, mua, mubB, muaB, mud]
                self.IDS_dL = [alpha, mua, mubB]
                self.IDS_dR = [beta, mub, muaB, mud]
                self.IDS_inter =  [gamma]
                self.IDS_uncovered = [delta]

            ##############################################################

            ### TO COMPUTE SUPPORTS, no index
            self.IDS_supp = (gamma, alpha, mua)
            self.IDS_miss = (mub, mubB, mud)
            ### indexes swaping when negating one side (0: negating A, 1: negating B)
            self.IDS_negated = [(delta, gamma, beta, alpha, muaB, mub, mua, mubB, mud), \
                           (gamma, delta, alpha, beta, mua, mubB, muaB, mub, mud)]

         #### END WITH MISSING VALUES
         ############################################################################

    ### return part label
    def getLabels(self):
        return self.labels
    
    def getLabel(self, id):
        return self.labels[id]

    # return the index corresponding to part_id when looking from given side 
    def partId(self, part_id, side=0):
        return self.side_index[side][part_id]

    # return the index corresponding to part_id when negating given side 
    def negatedPartId(self, part_id, side=0):
        return self.IDS_negated[side][part_id]

    
    # return the index corresponding to inout and possible negation
    def inOutId(self, inout_id, neg=0):
        return self.neg_index[neg][inout_id]


    # sums the values in parts that correspond to part_id indexes given in parts_id
    ## parts_id can be
    ##  * a list of pairs (inout, part_id), inout are then ignored 
    ##  * a list of values part_id
    def sumPartsId(self, side, parts_id, parts):
        if type(parts) == list  and len(parts_id) > 0:
            if type(parts_id[0]) == int:
                 ids = parts_id    
            elif len(parts_id[0]) == 2:
                (inout, ids) = zip(*parts_id)
            else:
                ids = []
            return sum([parts[self.partId(part_id, side)] for part_id in set(ids)])
        elif type(parts) == int :
            return 1*(parts in [self.partId(part_id[1], side) for part_id in parts_id])
        return 0

    def suppPartRange(self):
        return range(self.bottom, self.top+1)

    # sums the values in parts that correspond to inout and part_id indexes given in parts_id
    ## parts_id must be
    ##  * a list of pairs (inout, part_id)
    def sumPartsIdInOut(self, side, neg, parts_id, parts):
        return sum([parts[self.inOutId(part_id[0], neg)][self.partId(part_id[1], side)] for part_id in parts_id])


    # return parts reordered to match the new indexes of parts corresponding to negation of given side
    def negateParts(self, side, parts):
        return [parts[self.negatedPartId(p, side)] for p in range(len(parts))]

    # compute the ratio of BLUE/RED parts depending on intersection with X
    def advRatioVar(self, side, op, parts):
        den = self.sumPartsId(side, self.IDS_varden[op], parts)
        if den != 0:
            return float(self.sumPartsId(side, self.IDS_varnum[op], parts))/den
        else:
            return float('Inf')

    # compute the accuracy resulting of appending X on given side with given operator and negation
    # from intersections of X with parts (clp)
    def advAcc(self, side, op, neg, lparts, lmiss, lin):
        lout = [lparts[i] - lmiss[i] - lin[i] for i in range(len(lparts))]
        clp = (lin, lout, lparts, lmiss)
        return float(self.sumPartsIdInOut(side, neg, self.IDS_varnum[op] + self.IDS_fixnum[op], clp))/ \
               self.sumPartsIdInOut(side, neg, self.IDS_varden[op] + self.IDS_fixden[op], clp)


    # sets the method to compute p-values
    def setMethodPVal(self, methodpVal='Marg'):
        try:
            self.methodpVal = methodpVal.capitalize()
            eval('self.pVal%sQueryCand' % (self.methodpVal))
            eval('self.pVal%sRedCand' % (self.methodpVal))
            # self.pValQueryCand = eval('self.pVal%sQueryCand' % (self.methodpVal))
            # self.pValRedCand = eval('self.pVal%sRedCand' % (self.methodpVal))
        except AttributeError:
            raise Exception('Oups method to compute the p-value does not exist !')


    def pValRedCand(self, side, op, neg, lParts, N, prs = None, method=""):
        meth = eval('self.pVal%sRedCand' % (self.methodpVal))
        return meth(side, op, neg, lParts, N, prs)

    def pValQueryCand(self, side, op, neg, lParts, N, prs = None):
        meth = eval('self.pVal%sQueryCand' % (self.methodpVal))
        return meth(side, op, neg, lParts, N, prs)
        # return 0 # self.pValSuppQueryCand(side, op, neg, lParts, N, prs)

    
    # query p-value using support probabilities (binomial), for candidates
    def pValSuppQueryCand(self, side, op, neg, lParts, N, prs = None):
        if prs is None:
            return 0
        else:
            lInter = self.sumPartsId(side, self.IDS_supp, lParts[self.inOutId(self.into, neg)])
            lX = float(sum(lParts[self.inOutId(self.into, neg)]))     
            if op:
                return 1-tool_pValSupp(N, lInter, prs[side] + lX/N - prs[side]*lX/N)
            else: 
                return tool_pValSupp(N, lInter, prs[side]*lX/N)


    # query p-value using marginals (binomial), for candidates
    def pValMargQueryCand(self, side, op, neg, lParts, N, prs = None):
        if prs is None:
            return 0
        else:
            lInter = self.sumPartsId(side, self.IDS_supp, lParts[self.inOutId(self.into, neg)])
            lsupp = self.sumPartsId(side, self.IDS_supp, lParts[self.inOutId(self.tot, neg)])
            lX = float(sum(lParts[self.inOutId(self.into, neg)]))     
            if op:
                return 1-tool_pValSupp(N, lInter, lsupp*lX/(N*N))
            else: 
                return tool_pValSupp(N, lInter, lsupp*lX/(N*N))


    # query p-value using support sizes (hypergeom), for candidates
    def pValOverQueryCand(self, side, op, neg, lParts, N, prs = None):
        if prs is None:
            return 0
        else:
            lInter = self.sumPartsId(side, self.IDS_supp, lParts[self.inOutId(self.into, neg)])
            lsupp = self.sumPartsId(side, self.IDS_supp, lParts[self.inOutId(self.tot, neg)])
            lX = float(sum(lParts[self.inOutId(self.into, neg)]))     
            if op:
                return 1-tool_pValOver(lInter, N, lsupp, lX)
            else: 
                return tool_pValOver(lInter, N, lsupp, lX)

        
    # redescription p-value using support probabilities (binomial), for candidates
    def pValSuppRedCand(self, side, op, neg, lParts, N, prs = None):
        lInter = self.sumPartsIdInOut(side, neg, self.IDS_fixnum[op] + self.IDS_varnum[op], lParts)
        lX = float(sum(lParts[self.inOutId(self.into, neg)]))     
        if prs is None :
            lO = self.sumPartsId(1-side, self.IDS_supp, lParts[self.inOutId(self.tot, neg)])
            return tool_pValSupp(N, lInter, float(lO*lX)/(N*N))
        elif op:
            return tool_pValSupp(N, lInter, prs[1-side]*(prs[side] + lX/N - prs[side]*lX/N))
        else: 
            return tool_pValSupp(N, lInter, prs[1-side]*(prs[side] * lX/N))


    # redescription p-value using marginals (binomial), for candidates
    def pValMargRedCand(self, side, op, neg, lParts, N, prs = None):
        lInter = self.sumPartsIdInOut(side, neg, self.IDS_fixnum[op] + self.IDS_varnum[op], lParts)
        lO = self.sumPartsId(1-side, self.IDS_supp, lParts[self.inOutId(self.tot, neg)])
        lS = self.sumPartsIdInOut(side, neg, self.IDS_nsupp[op], lParts)
        return tool_pValSupp(N, lInter, float(lO*lS)/(N*N))

    
    # redescription p-value using support sizes (hypergeom), for candidates
    def pValOverRedCand(self, op, neg, lParts, N, prs = None):
        lInter = self.sumPartsIdInOut(side, neg, self.IDS_fixnum[op] + self.IDS_varnum[op], lParts)
        lO = self.sumPartsId(1-side, self.IDS_supp, lParts[self.inOutId(self.tot, neg)])
        lS = self.sumPartsIdInOut(side, neg, self.IDS_nsupp[op], lParts)
        return tool_pValOver(lInter, N, lO, lS)


    # initialize parts counts
    # default count for every part is zero
    # pairs contains a list of (part_id, value)
    # if value is non negative, the count of part_id is set to that value
    # if value is negative, the count of part_id is set to - value - sum of the other parts set so far
    def makeLParts(self, pairs=[], side=0):
        lp = [0 for i in range(self.top+1)]
        for (part_id, val) in pairs:
            if self.partId(part_id, side) < len(lp):
                if val < 0:
                    tmp = sum(lp)
                    lp[self.partId(part_id, side)] = -val- tmp
                else:
                    lp[self.partId(part_id, side)] = val
            else:
                if val > 0:
                    raise Exception("Some missing data where there should not be any!")
        return lp
    

    # adds to parts counts
    # lpartsY can be a part_id in wich case the result of the addition
    # is lpartsX where that part in incremented by one
    def addition(self, lpartsX, lpartsY):
        if type(lpartsY) == list:
            lp = [lpartsX[i]+lpartsY[i] for i in range(len(lpartsX))]    
        else:
            lp = list(lpartsX)
            if type(lpartsY) == int :
                lp[lpartsY] += 1
        return lp

class SParts(object):

    infos = {"acc": "self.acc()", "pval": "self.pVal()"}
    print_delta_fields = [ "delta", "card_delta"]
    print_finfo = infos.keys()
    print_iinfo = ["card_"+ label for label in SSetts.labels]
    print_sinfo = list(SSetts.labels)

    def __init__(self, ssetts, N, supports, prs = [1,1]):
        #### init from dict_info
        self.ssetts = ssetts
        if type(N) == dict:
            self.missing = False
            self.sParts = [set() for i in range(len(self.ssetts.getLabels()))]
            self.prs = [-1, -1]
            self.N = 0
            supp_keys = sdict.keys()
            for i, supp_key in enumerate(self.ssetts.getLabels()):
                if supp_key in sdict:
                    if i > 3 and len(sdict[supp_key]) > 0:
                        self.missing = True
                    self.sParts[i] = set(sdict.pop(supp_key))

            if 'pr_0' in sdict:
                self.prs[0] = sdict.pop('pr_0')
            if 'pr_1' in sdict:
                self.prs[1] = sdict.pop('pr_1')
            if 'N' in sdict:
                self.N = sdict.pop('N')
            if not self.missing:
                del self.sParts[4:]
        else:
            if type(N) is set:
                self.N = len(N)
                bk = N
            else:
                self.N = N
                bk = None
            self.prs = prs
            self.vect = None
            ### if include all empty missing parts, remove 
            if type(supports) == list and len(supports) == 4 and len(supports[2]) + len(supports[3]) == 0 :
                supports = supports[0:2]
            elif type(supports) == list and len(supports) == 9 and len(supports[8]) + len(supports[7]) + len(supports[6]) + len(supports[5]) + len(supports[4]) == 0 :
                supports = supports[0:3]

            ### sParts is a partition of the rows (delta is not explicitely stored when there are no missing values)
            ## two supports: interpreted as (suppL, suppR)
            if type(supports) == list and len(supports) == 2 :
                (suppL, suppR) = supports
                self.missing = False
                self.sParts = [ set(suppL - suppR), \
                           set(suppR - suppL), \
                           set(suppL & suppR)]
            ## three supports: interpreted as (alpha, beta, gamma)
            elif type(supports) == list and len(supports) == 3:
                self.missing = False
                self.sParts = [ set(supports[0]), set(supports[1]), set(supports[2])]
            ## four supports: interpreted as (suppL, suppR, missL, missR)
            elif type(supports) == list and len(supports) == 4:
                self.missing = True
                (suppL, suppR, missL, missR) = supports
                self.sParts = [ set(suppL - suppR - missR), \
                           set(suppR - suppL - missL), \
                           set(suppL & suppR), \
                           set(range(self.N)) - suppL -suppR - missL - missR, \
                           set(suppL & missR), \
                           set(suppR & missL), \
                           set(missR - suppL - missL), \
                           set(missL - suppR - missR), \
                           set(missL & missR) ]
            ## nine supports: interpreted as (alpha, beta, gamma, delta, mua, mub, muaB, mubB, mud)
            elif type(supports) == list and len(supports) == 9:
                self.missing = True
                self.sParts = [set(support) for support in supports]
            ## else: set all empty
            else:
                self.missing = False
                self.sParts = [set(), set(), set(), set(), set(), set(), set(), set(), set()]
                bk = None
            if bk is not None:
                if len(self.sParts) == 3:
                    self.sParts.append(set(bk))
                else:
                    self.sParts[self.ssetts.delta] = set(bk)
                for si, sp in enumerate(self.sParts):
                    if si != self.ssetts.delta:
                        self.sParts[self.ssetts.delta] -= sp

    # def __eq__(self, other):
    #     print "Calling EQ"
    #     if isinstance(other, SParts) and len(other.sParts) == len(self.sParts):
    #         for i, p in enumerate(self.sParts):
    #             if other.sParts[i] != p:                    
    #                 return False
    #         return True
    #     return False

    def __cmp__(self, other):
        if isinstance(other, SParts) and len(other.sParts) == len(self.sParts):
            lps = [len(p) for p in self.sParts]
            lpo = [len(p) for p in other.sParts]
            if lps == lpo:
                for i, p in enumerate(self.sParts):
                    if other.sParts[i] != p:                    
                        return cmp(p, other.sParts[i])
                return 0
            return cmp(lps, lpo)
        return -1

    def pVal(self):
        try:
            return eval('self.pVal%s()' % (self.ssetts.methodpVal))
        except AttributeError:
              raise Exception('Oups method to compute the p-value does not exist !')

    def getSSetts(self):
        return self.ssetts

    def nbRows(self):
        return self.N

    def toDict(self, with_delta=False):
        sdict = {}
        for i in range(len(self.sParts)):
                 sdict[self.ssetts.getLabel(i)] = self.part(i)
                 sdict["card_" + self.ssetts.getLabel(i)] = self.lpart(i)
        if with_delta:
                 sdict[self.ssetts.getLabel(SSetts.delta)] = self.part(SSetts.delta)
                 sdict["card_" + self.ssetts.getLabel(SSetts.delta)] = self.lpart(SSetts.delta)
        for side in [0, 1]:
                 if self.prs[side] != -1:
                     sdict["pr_" + str(side)] = self.prs[side]
        sdict["N"] = self.N
        for info_key, info_meth in SParts.infos.items():
            sdict[info_key] = eval(info_meth)
        return sdict
            
    # contains missing values
    def hasMissing(self):
        return self.missing

    # return copy of the probas
    def probas(self):
        return list(self.prs)

    # return support (used to create new instance of SParts)
    def supparts(self):
        return self.sParts

    # return new instance of SParts corresponding to negating given side
    def negate(self, side=0):
        if self.missing:
            return SParts(self.ssetts, self.N, self.ssetts.negateParts(side, self.sParts))
        else:
            self.sParts.append(self.part(self.ssetts.delta))
            n = self.ssetts.negateParts(side, self.sParts)
            return SParts(self.ssetts, self.N, n[0:-1])

    def part(self, part_id, side=0):
        pid = self.ssetts.partId(part_id, side)
        if pid < len(self.sParts):
            return self.sParts[pid]
        elif part_id == self.ssetts.delta:
            return set(range(self.N)) - self.sParts[0] - self.sParts[1] - self.sParts[2]
        else:
            return set()
        
    def lpart(self, part_id, side=0):
        pid = self.ssetts.partId(part_id, side)
        if pid < len(self.sParts):
            return len(self.sParts[pid])
        elif part_id == self.ssetts.delta:
            return self.N - len(self.sParts[0]) - len(self.sParts[1]) - len(self.sParts[2])
        else:
            return 0

    def parts(self, side=0):
        return [self.part(i, side) for i in range(self.ssetts.top+1)]

    def parts4M(self, side=0):
        if self.missing:
            return [self.part(i, side) for i in range(self.ssetts.delta+1)]+[set().union(*[self.part(i, side) for i in range(self.ssetts.delta+1, self.ssetts.top+1)])]
        else:
            return self.parts(side)
            
    def lparts(self, side=0):
        return [self.lpart(i, side) for i in range(self.ssetts.top+1)]
    
    def partInterX(self, suppX, part_id, side=0):
        pid = self.ssetts.partId(part_id, side)
        if pid < len(self.sParts):
            return set(suppX & self.sParts[pid])
        elif part_id == self.ssetts.delta:
            return set(suppX - self.sParts[0] - self.sParts[1] - self.sParts[2])
        else:
            return set()
        
    def lpartInterX(self, suppX, part_id, side=0):
        pid = self.ssetts.partId(part_id, side)
        if pid < len(self.sParts):
            return len(suppX & self.sParts[pid])
        elif part_id == self.ssetts.delta:
            return len(suppX - self.sParts[0] - self.sParts[1] - self.sParts[2])
        else:
            return 0

    def partsInterX(self, suppX, side=0):
        return [self.partInterX(suppX, i, side) for i in range(self.ssetts.top+1)]
    
    def lpartsInterX(self, suppX, side=0):
        if self.missing:
            return [self.lpartInterX(suppX, i, side) for i in range(self.ssetts.top+1)]
        else:
            la = self.lpartInterX(suppX, self.ssetts.alpha, side)
            lb = self.lpartInterX(suppX, self.ssetts.beta, side)
            lc = self.lpartInterX(suppX, self.ssetts.gamma, side)
            tmp = [la, lb, lc, len(suppX) - la - lb - lc]
            for i in range(len(tmp), self.ssetts.top+1):
                tmp.append(0)
            return tmp

    def nbParts(self):
        return self.ssetts.top+1
        
    def lparts_union(self, ids, side=0):
        return sum([self.lpart(i, side) for i in ids])

    def part_union(self, ids, side=0):
        union = set()
        for i in ids:
            union |= self.part(i, side)
        return union

    def supp(self, side=0):
        return self.part_union(self.ssetts.IDS_supp, side)
    def nonSupp(self, side=0):
        if not self.missing:
            return set(range(self.N)) - self.supp(side)
        else:
            return self.part_union(set(range(self.ssetts.top+1)) - set(self.ssetts.IDS_supp + self.ssetts.IDS_miss), side)
    def miss(self, side=0):
        if not self.missing:
            return set()
        else:
            return self.part_union(self.ssetts.IDS_miss, side)

    def lenSupp(self, side=0):
        return self.lparts_union(self.ssetts.IDS_supp, side)
    def lenNonSupp(self, side=0):
        return self.N - self.lenSupp(side) - self.lenMiss(side)
    def lenMiss(self, side=0):
        if not self.missing:
            return 0
        else:
            return self.lparts_union(self.ssetts.miss_ids, side)

    ### SUPPORTS
    def suppSide(self, side):
        if side == 0:
            return self.part_union(self.ssetts.IDS_dL+self.ssetts.IDS_inter, 0)
        else:
            return self.part_union(self.ssetts.IDS_dR+self.ssetts.IDS_inter, 0)
    def suppD(self, side=0):
        return self.part_union(self.ssetts.IDS_diff, side)
    
    def suppI(self, side=0):
        return self.part_union(self.ssetts.IDS_inter, side)
    def suppU(self, side=0):
        return self.part_union(self.ssetts.IDS_inter+self.ssetts.IDS_diff, side)
    def suppL(self, side=0):
        return self.suppSide(0)
    def suppR(self, side=0):
        return self.suppSide(1)
    def suppO(self, side=0):
        return self.part_union(self.ssetts.IDS_uncovered, side)
    def suppT(self, side=0):
        if len(self.sParts) == 4:
            return self.part_union(range(4), side)
        else:
            return set(range(self.N))
    def suppA(self, side=0):
        return self.part_union(self.ssetts.IDS_dL, side)
    def suppB(self, side=0):
        return self.part_union(self.ssetts.IDS_dR, side)

    ### LENGHTS
    def lenSide(self, side):
        if side == 0:
            return self.lparts_union(self.ssetts.IDS_dL+self.ssetts.IDS_inter, 0)
        else:
            return self.lparts_union(self.ssetts.IDS_dR+self.ssetts.IDS_inter, 0)
    # def lenD(self, side=0):
    #     return self.lparts_union(self.ssetts.IDS_diff, side)
    
    # def lenI(self, side=0):
    #     return self.lparts_union(self.ssetts.IDS_inter, side)
    # def lenU(self, side=0):
    #     return self.lparts_union(self.ssetts.IDS_inter+self.ssetts.IDS_diff, side)
    #     return self.suppI(side) | self.suppD(side)
    # def lenL(self, side=0):
    #     return self.lenSide(0)
    # def lenR(self, side=0):
    #     return self.lenSide(1)
    # def lenO(self, side=0):
    #     return self.lparts_union(self.ssetts.IDS_uncovered, side)
    def lenT(self, side=0):
        if len(self.sParts) == 4:
            return self.lparts_union(range(4), side)
        else:
            return self.N
    def lenA(self, side=0):
        return self.lparts_union(self.ssetts.IDS_dL, side)
    def lenB(self, side=0):
        return self.lparts_union(self.ssetts.IDS_dR, side)


    ## corresponding lengths
    def lenD(self, side=0):
        return self.lparts_union(self.ssetts.IDS_diff, side)
    def lenI(self, side=0):
        return self.lparts_union(self.ssetts.IDS_inter, side)
    def lenO(self, side=0):
        return self.lparts_union(self.ssetts.IDS_uncovered, side)
    def lenU(self, side=0):
        return self.lenD(side)+self.lenI(side)
    def lenL(self, side=0):
        return self.lparts_union(self.ssetts.IDS_dL, side)
    def lenR(self, side=0):
        return self.lparts_union(self.ssetts.IDS_dR, side)

    # accuracy
    def acc(self, side=0):
        lenI = self.lenI(side)
        if lenI == 0:
            return 0
        else:
            return lenI/float(lenI+self.lenD(side))

    # redescription p-value using support probabilities (binomial), for redescriptions
    def pValSupp(self):
        if self.prs == [-1,-1] or self.N == -1:
            return -1
        elif self.lenSupp(0)*self.lenSupp(1) == 0:
            return 0
        else:
            return tool_pValSupp(self.N, self.lenI(), self.prs[0]*self.prs[1]) 

    # redescription p-value using marginals (binomial), for redescriptions
    def pValMarg(self):
        if self.N == -1:
            return -1
        elif self.lenSupp(0)*self.lenSupp(1) == 0:
            return 0
        else:
            return tool_pValSupp(self.N, self.lenI(), float(self.lenSupp(0)*self.lenSupp(1))/(self.N*self.N)) 

    # redescription p-value using support sizes (hypergeom), for redescriptions
    def pValOver(self):
        if self.N == -1:
            return -1
        elif self.lenSupp(0)*self.lenSupp(1) == 0:
            return 0
        else:
            return tool_pValOver(self.lenI(), self.N, self.lenSupp(0) ,self.lenSupp(1))

    # moves the instersection of supp with part with index id_from to part with index id_to
    def moveInter(self, side, id_from, id_to, supp):
        self.sParts[self.ssetts.partId(id_to, side)] |= (self.sParts[self.ssetts.partId(id_from,side)] & supp)
        self.sParts[self.ssetts.partId(id_from,side)] -= supp

    # update support probabilities
    def updateProba(prA, prB, OR):
        if type(prA) == int and prA == -1:
            return prB
        elif OR :
            return prA + prB - prA*prB
        else :
            return prA*prB
    updateProba = staticmethod(updateProba)

    # update support probabilities
    def updateProbaMass(prs, OR):
        if len(prs) == 1:
            return prs[0]
        elif OR :
            return reduce(lambda x, y: x+y-x*y, prs)
        else :
            return numpy.prod(prs)
    updateProbaMass = staticmethod(updateProbaMass)

    # update supports and probabilities resulting from appending X to given side with given operator
    def update(self, side, OR, suppX, missX):
        self.vect = None
        union = None
        self.prs[side] = SParts.updateProba(self.prs[side], len(suppX)/float(self.N), OR)
            
        if not self.missing and (type(missX) == set and len(missX) > 0):
            self.missing = True
            if len(self.sParts) == 3:
                self.sParts.append(set(range(self.N)) - self.sParts[0] - self.sParts[1] -self.sParts[2])
            else:
                union = set(self.sParts[0] | self.sParts[1] | self.sParts[2] | self.sParts[3])
            self.sParts.extend( [set(), set(), set(), set(), set() ])
            
        if self.missing and self.ssetts.top > self.ssetts.delta:
            if OR : ## OR
                ids_from_to_supp = [(self.ssetts.beta, self.ssetts.gamma ), (self.ssetts.delta, self.ssetts.alpha ),
                                    (self.ssetts.mub, self.ssetts.gamma ), (self.ssetts.mubB, self.ssetts.alpha ),
                                    (self.ssetts.muaB, self.ssetts.mua ), (self.ssetts.mud, self.ssetts.mua )]
                for (id_from, id_to) in ids_from_to_supp:
                    self.moveInter(side, id_from, id_to, suppX)

                if (type(missX) == set and len(missX) > 0):
                    ids_from_to_miss = [(self.ssetts.beta, self.ssetts.mub ), (self.ssetts.delta, self.ssetts.mubB ),
                                        (self.ssetts.muaB, self.ssetts.mud )]
                    for (id_from, id_to) in ids_from_to_miss:
                        self.moveInter(side, id_from, id_to, missX)
            
            else: ## AND
                if (type(missX) == set and len(missX) > 0):
                    suppXB  = set(range(self.N)) - suppX - missX
                else:
                    suppXB  = set(range(self.N)) - suppX
                ids_from_to_suppB = [(self.ssetts.alpha, self.ssetts.delta ), (self.ssetts.gamma, self.ssetts.beta ),
                                    (self.ssetts.mua, self.ssetts.muaB ), (self.ssetts.mub, self.ssetts.beta ),
                                    (self.ssetts.mubB, self.ssetts.delta ), (self.ssetts.mud, self.ssetts.muaB )]
                for (id_from, id_to) in ids_from_to_suppB:
                    self.moveInter(side, id_from, id_to, suppXB)
                
                if (type(missX) == set and len(missX) > 0):
                    ids_from_to_miss = [(self.ssetts.alpha, self.ssetts.mubB ), (self.ssetts.gamma, self.ssetts.mub ),
                                        (self.ssetts.mua, self.ssetts.mud )]
                    for (id_from, id_to) in ids_from_to_miss:
                        self.moveInter(side, id_from, id_to, missX)
                
        else :
            if OR : ## OR
                self.sParts[self.ssetts.partId(self.ssetts.alpha,side)] |= (suppX
                                                                       - self.sParts[self.ssetts.partId(self.ssetts.beta, side)]
                                                                       - self.sParts[self.ssetts.partId(self.ssetts.gamma, side)])
                self.sParts[self.ssetts.partId(self.ssetts.gamma,side)] |= (suppX
                                                                       & self.sParts[self.ssetts.partId(self.ssetts.beta, side)])
                self.sParts[self.ssetts.partId(self.ssetts.beta,side)] -= suppX
            
            else: ## AND
                self.sParts[self.ssetts.partId(self.ssetts.beta,side)] |= (self.sParts[self.ssetts.partId(self.ssetts.gamma, side)]
                                                                       - suppX )
                self.sParts[self.ssetts.partId(self.ssetts.gamma,side)] &= suppX
                self.sParts[self.ssetts.partId(self.ssetts.alpha,side)] &= suppX
        if union is not None:
            self.sParts[self.ssetts.delta] = union - self.sParts[self.ssetts.gamma] - self.sParts[self.ssetts.beta] - self.sParts[self.ssetts.alpha]
        
    # computes vector ABCD (vector containg for each row the index of the part it belongs to)
    def makeVectorABCD(self, force_list=False):
        if self.vect is None or (force_list and type(self.vect) is not list):
            if len(self.sParts) == 4 and not force_list:
                # svect = {}
                self.vect = {}
                for partId in range(len(self.sParts)):
                    for i in self.sParts[partId]:
                        self.vect[i] = partId
            else:
                self.vect = [self.ssetts.delta for i in range(self.N)]
                for partId in range(len(self.sParts)):
                    for i in self.sParts[partId]:
                        self.vect[i] = partId
                        
                        
    def getVectorABCD(self, force_list=False):
        self.makeVectorABCD(force_list)
        if type(self.vect) is dict:
            return None
        return list(self.vect)

    # returns the index of the part the given row belongs to, vectorABCD need to have been computed 
    def partRow(self, row):
        return self.vect[row]

    # return the index of the part the given row belongs to
    # or the intersection of the mode of X with the different parts if row == -1, vectorABCD need to have been computed 
    def lpartsRow(self, row, X=None):
        lp = None
        if row == -1 and X is not None :
            if self.missing:
                lp = [len(X.interMode(self.sParts[i])) for i in range(self.ssetts.top+1)]
            else:
                lp = [0 for i in range(self.nbParts())]
                lp[0] = len(X.interMode(self.sParts[0]))
                lp[1] = len(X.interMode(self.sParts[1]))
                lp[2] = len(X.interMode(self.sParts[2]))
                lp[3] = X.lenMode() - lp[0] - lp[1] - lp[2]
        elif row is not None:
            lp = self.vect[row]
        return lp

############## PRINTING
##############
    # def __str__(self):
#         s = '|'
#         r = '||\n|'
#         if self.missing: up_to = self.ssetts.mud
#         else: up_to = self.ssetts.delta
#         for i in range(up_to+1):
#             s += '|%s' % (3*self.ssetts.getLabel(i))
#             r += '| % 4i ' % self.lpart(i,0)
#         return s+r+'||'

    def dispSupp(self):
        supportStr = ''
        for i in sorted(self.supp(0)): supportStr += "%i "%i
        supportStr +="\t"
        for i in sorted(self.supp(1)): supportStr += "%i "%i
        if self.missing:
            supportStr +="\t"
            for i in sorted(self.miss(0)): supportStr += "%i "%i
            supportStr +="\t"
            for i in sorted(self.miss(1)): supportStr += "%i "%i
        return supportStr

    # compute the resulting support and missing when combining X and Y with given operator
    def partsSuppMiss(OR, XSuppMiss, YSuppMiss):
        if XSuppMiss is None:
            return YSuppMiss
        elif YSuppMiss is None:
            return XSuppMiss
        elif OR:
            supp = set(XSuppMiss[0] | YSuppMiss[0])
            miss = set(XSuppMiss[1] | YSuppMiss[1]) - supp
        else:
            miss = set((XSuppMiss[1] & YSuppMiss[1]) | (XSuppMiss[1] & YSuppMiss[0]) | (YSuppMiss[1] & XSuppMiss[0]))
            supp = set(XSuppMiss[0] & YSuppMiss[0])
        return (supp, miss)
    partsSuppMiss = staticmethod(partsSuppMiss)

    def partsSuppMissMass(OR, SuppMisses):
        if len(SuppMisses) == 1:
            return SuppMisses[0]
        elif len(SuppMisses) > 1:
            if OR:
                supp = reduce(set.union, [X[0] for X in SuppMisses])
                miss = reduce(set.union, [X[1] for X in SuppMisses]) - supp
            else:
                supp = reduce(set.intersection, [X[0] for X in SuppMisses])
                miss = reduce(set.intersection, [X[0].union(X[1]) for X in SuppMisses]) - supp
            return (supp, miss)
    partsSuppMissMass = staticmethod(partsSuppMissMass)

        # Make binary out of supp set
    def suppVect(self, N, supp, val=1):
        vect = None
        if 2*len(supp) < N:
            st = supp
            v = val
            if val == 1:
                vect = numpy.zeros(N)
            else:
                vect = numpy.ones(N)
        else:
            st = set(range(N)) - supp
            v = 1-val
            if val == 0:
                vect = numpy.zeros(N)
            else:
                vect = numpy.ones(N)
        for i in st:
            vect[i] = v
        return vect
    suppVect = staticmethod(suppVect)

    def parseSupport(stringSupp, N, ssetts):
        partsSupp = stringSupp.rsplit('\t')
        if len(partsSupp) == 2:
            return SParts(ssetts, N, [SParts.parseSupportPart(partsSupp[0]), SParts.parseSupportPart(partsSupp[1])])
        elif len(partsSupp) == 4:
            return SParts(ssetts, N, [SParts.parseSupportPart(partsSupp[0]), SParts.parseSupportPart(partsSupp[1]), \
                          SParts.parseSupportPart(partsSupp[2]), SParts.parseSupportPart(partsSupp[3])])
        return None
    parseSupport = staticmethod(parseSupport)

    def parseSupportPart(string):
        nsupp = set()
        for i in string.strip().rsplit():
            try:
                nsupp.add(int(i))
            except TypeError, detail:
                raise Exception('Unexpected element in the support: %s\n' %i)
        return nsupp
    parseSupportPart = staticmethod(parseSupportPart)

    def __str__(self):
        return "SUPPORT:" + (" ".join(["card_" + self.ssetts.getLabel(i)+":" + str(len(self.sParts[i]))         for i in range(len(self.sParts))]))
