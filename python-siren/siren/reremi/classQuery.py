import re, random, operator, itertools, codecs, numpy, copy
from classSParts import  SParts
from redquery_parser import RedQueryParser
import scipy.spatial.distance
from grako.exceptions import * # @UnusedWildImport
import pdb

VARIABLE_MARK = 'v'

def foldRowsTT(tt):
    changed = False
    tts = numpy.argsort(numpy.abs(0.5*tt.shape[0] - tt.sum(axis=0)))
    for i in tts:
        cols = [j for j in range(tt.shape[1]) if j != i]
        idL = numpy.where(tt[:,i]==1)[0]
        idR = numpy.where(tt[:,i]==0)[0]
        L = tt[idL,:]
        R = tt[idR,:]
        ps = zip(*numpy.where(scipy.spatial.distance.cdist(L[:,cols], R[:,cols], 'hamming')==0))
        keep = numpy.ones(tt.shape[0], dtype = numpy.bool)
        for p in ps:
            changed = True
            tt[idL[p[0]], i] = -1
            keep[idR[p[1]]] = False
        tt = tt[keep,:]
    return tt, changed

def foldColsTT(tt):
    # org = tt.copy()
    idsO = []
    # idsM = []
    ps = zip(*numpy.where(scipy.spatial.distance.squareform((scipy.spatial.distance.pdist(tt, 'hamming')*tt.shape[1] == 2))))
    # while(len(ps)) > 0:
    for rows in ps:
        # rows = ps[0]
        cols = numpy.where(tt[rows[0],:] != tt[rows[1],:])[0]
        block = tt[rows,:][:,cols]
        pr, pc  = numpy.where(block ==-1)
        if len(pr) == 1 and pr[0] ==1:
            changed = True
            if pc[0] == 1:
                # tt[rows[0], cols[0]] = -1
                idsO.append((rows[0], cols[0]))
                # idsM.append((rows[1], cols[1]))
            else:
                # tt[rows[0], cols[1]] = -1
                idsO.append((rows[0], cols[1]))
                # idsM.append((rows[1], cols[0]))
    if len(idsO) > 0:
        tt[zip(*idsO)] = -1
    return tt, len(idsO) > 0

def subsRowsTT(tt):
    tts = numpy.argsort(-numpy.sum(tt==-1, axis=1))
    keep = numpy.ones(tt.shape[0], dtype = numpy.bool)
    for row in tts:
        if keep[row]:
            cmask = tt[row, :] != -1
            ps = numpy.where(scipy.spatial.distance.cdist(tt[:,cmask], [tt[row,cmask]], 'hamming')==0)[0]
            for p in ps:
                if p != row:
                    keep[p] = False
    return tt[keep,:], numpy.sum(~keep) > 0

def triplesRowsTT(tt):
    tts = numpy.argsort(-numpy.sum(tt==-1, axis=1))
    keep = numpy.ones(tt.shape[0], dtype = numpy.bool)
    pivots = []
    pairs = []
    for row in tts:
        # if row == 2:
        #     print tt
        #     pdb.set_trace()
        cmask = tt[row, :] == -1
        ps = zip(*numpy.where(scipy.spatial.distance.squareform((scipy.spatial.distance.pdist(tt[:,cmask]==-1, 'hamming') == 0))))
        for p in ps:
            if p[0] < p[1]:
                matches = tt[p[0],:] == tt[p[1],:]
                ### MATCHING CONDITIONS:
                ### a) where row == -1:
                ###    i) all -1 match, ii, there are non -1, ii) in all of them p[0] and p[1] are complements 
                ### b) where row != -1:
                ###    i) one value is -1 (if rows don't match), ii) the other (or both if match) is the value in row 
                if ( numpy.sum(cmask * matches) == 0 or numpy.max(tt[p,:][:, cmask * matches]) == -1 )  and \
                   numpy.sum(cmask * ~matches) > 0 and \
                   numpy.all(tt[p[0], cmask * ~matches] == (1-tt[p[1], cmask * ~matches])) and \
                   numpy.all(numpy.min(tt[p,:][:, ~cmask * ~matches], axis=0) == -1) and \
                   numpy.all(numpy.max(tt[p,:][:, ~cmask], axis=0) == tt[row, ~cmask]) :
                    pivots.append(row)
                    pairs.append(p)
                                          
            # for p in ps:
            #     if p[0] < p[1]:
            #         matches = tt[p[0],:] == tt[p[1],:]
            #         if numpy.max(numpy.min(tt[p,:][:, ~(cmask + matches)],axis=0)) == -1 \
            #                and (numpy.sum(matches) == 0 or numpy.min(tt[p[0], matches]) > -1):
            #             pivots.append(row)
            #             pairs.append(p)

    if len(pivots) > 0:
        if len(pivots) > 1:
            print "More than one pivot", pivots, pairs
            pdb.set_trace()
        keep[pivots] = False
        # print "Found triple"
    return tt[keep,:], numpy.sum(~keep)>0


def simplerTT(tt):
    # nbrows = tt.shape[0]
    # nbnn = numpy.sum(tt>-1)
    # ttchanged = 0
    if tt.shape[0] > 2:
        changed = [True, True, True, True]
        while sum(changed) > 0:
            tt, changed[0] = foldRowsTT(tt)
            tt, changed[1] = foldColsTT(tt)
            tt, changed[2] = subsRowsTT(tt)
            tt, changed[3] = triplesRowsTT(tt)
    #         ttchanged += sum(changed)
    # if ttchanged > 0:
    #     print "SIMPLIFY FROM (%d, %d) TO (%d, %d)" % (nbrows, nbnn, tt.shape[0], numpy.sum(tt>-1))
    #     # print tt
    return tt

def recurse_numeric(b, function, args={}):
    if type(b) is list:
        out = 0
        for bi, bb in enumerate(b):
            nargs = dict(args)
            if "trace" in args:
                nargs["trace"] = [bi]+args["trace"]
            out += recurse_numeric(bb, function, nargs)
        return out
    else:
        return function(b, **args)

### WARNING THIS DOES NOT RECURSE ON NEGATIONS
def recurse_list(b, function, args={}):
    if type(b) is list:
        out = []
        for bi, bb in enumerate(b):
            nargs = dict(args)
            if "trace" in args:
                nargs["trace"] = [bi]+args["trace"]
            tou = recurse_list(bb, function, nargs)
            if type(tou) is list:
                out.extend(tou)
            elif tou is not None:
                out.append(tou)
        return out
    elif isinstance(b, Literal):
        return function(b, **args)

def recurse_deep(b, function, args={}):
    if type(b) is list:
        out = []
        for bi, bb in enumerate(b):
            nargs = dict(args)
            if "trace" in args:
                nargs["trace"] = [bi]+args["trace"]
            tmp = recurse_deep(bb, function, nargs)
            if tmp is not None:
                out.append(tmp)
        return out
    else:
        return function(b, **args)



class SYM(object):

    SYMU_OR = ur'\u2228'
    SYMU_AND = ur'\u2227'
    SYMU_NOT = ur'\u00ac '
    SYMU_LEQ = ur'\u2264'
    SYMU_EIN = ur'\u2208'
    SYMU_NIN = ur'\u2209'
    SYMU_NEQ = ur'\u2260'

    SYMU_ALPHA=u"\u2081\u2080"
    SYMU_BETA=u"\u2080\u2081"
    SYMU_GAMMA=u"\u2081\u2081"
    SYMU_DELTA=u"\u2080\u2080"
    SYMU_SETMIN=u"\u2216"

    SYMU_ARRTOP=u"\u2191"
    SYMU_ARRBOT=u"\u2193"
    # SYMU_LEARN = ur'\u25e9'
    # SYMU_TEST = ur'\u25ea'
    # SYMU_LEARN = ur'\u25d6'
    # SYMU_TEST = ur'\u25d7'
    # SYMU_LEARN = ur'\u25d0'
    # SYMU_TEST = ur'\u25d1'
    SYMU_LEARN = ur'\u25d5'
    SYMU_TEST = ur'\u25d4'
    SYMU_RATIO = ur'\u2298'
    # SYMU_CROSS = ur'\u274c'
    SYMU_CROSS = ur'\u2715'
    SYMU_INOUT = ur'\u21d7'
    SYMU_OUTIN = ur'\u21d8'
    
    
    SYMO_OR = 'OR'
    SYMO_AND = 'AND'
    SYMO_NOT = 'NOT '
    SYMO_LEQ = '<'
    SYMO_EIN = 'IN'
    SYMO_NIN = 'NOT IN'
    SYMO_NEQ = '~'

    SYMO_ALPHA="_10"
    SYMO_BETA="_01"
    SYMO_GAMMA="_11"
    SYMO_DELTA="_00"
    SYMO_SETMIN="\\"

    SYMO_ARRTOP="^"
    SYMO_ARRBOT="v"
    SYMO_LEARN = '[l]'
    SYMO_TEST = '[t]'
    SYMO_RATIO = '[r]'
    SYMO_CROSS = 'X'
    SYMO_INOUT = '>>'
    SYMO_OUTIN = '<<'


    ## WITH UNICODE
    SYM_OR = SYMU_OR
    SYM_AND = SYMU_AND
    SYM_NOT = SYMU_NOT
    SYM_LEQ = SYMU_LEQ
    SYM_EIN = SYMU_EIN
    SYM_NIN = SYMU_NIN
    SYM_NEQ = SYMU_NEQ

    SYM_ALPHA=SYMU_ALPHA
    SYM_BETA=SYMU_BETA
    SYM_GAMMA=SYMU_GAMMA
    SYM_DELTA=SYMU_DELTA
    SYM_SETMIN=SYMU_SETMIN

    SYM_ARRTOP=SYMU_ARRTOP
    SYM_ARRBOT=SYMU_ARRBOT
    SYM_LEARN = SYMU_LEARN
    SYM_TEST = SYMU_TEST
    SYM_RATIO = SYMU_RATIO
    SYM_CROSS = SYMU_CROSS
    SYM_INOUT = SYMU_INOUT
    SYM_OUTIN = SYMU_OUTIN

    ## WITHOUT UNICODE
    # SYM_OR = SYMO_OR
    # SYM_AND = SYMO_AND
    # SYM_NOT = SYMO_NOT
    # SYM_LEQ = SYMO_LEQ
    # SYM_EIN = SYMO_EIN
    # SYM_NIN = SYMO_NIN
    # SYM_NEQ = SYMO_NEQ

    # SYM_ALPHA=SYMO_ALPHA
    # SYM_BETA=SYMO_BETA
    # SYM_GAMMA=SYMO_GAMMA
    # SYM_DELTA=SYMO_DELTA
    # SYM_SETMIN=SYMO_SETMIN

    # SYM_ARRTOP=SYMO_ARRTOP
    # SYM_ARRBOT=SYMO_ARRBOT
    # SYM_LEARN = SYMO_LEARN
    # SYM_TEST = SYMO_TEST
    # SYM_RATIO = SYMO_RATIO
    # SYM_CROSS = SYMO_CROSS
    # SYM_INOUT = SYMO_INOUT
    # SYM_OUTIN = SYMO_OUTIN


class Op(object):
    
    ops = {0: 'X', 1: '|', -1: '&'}
    opsTex = {0: 'X', 1: '$\lor$', -1: '$\land$'}
    opsU = {0: 'X', 1: SYM.SYM_OR, -1: SYM.SYM_AND}

    def __init__(self, nval=0):
        if type(nval) == bool :
            if nval:
                self.val = 1
            else:
                self.val = -1
        elif nval in Op.ops:
            self.val = nval
        elif isinstance(nval, Op):
            self.val = nval.val
        else:
            raise Exception('Uninterpretable operator: %s !' % nval)
                
    def isSet(self):
        return self.val != 0

    def flip(self):
        self.val *= -1

    def copy(self):
        return Op(self.val)
    
    def other(self):
        return Op(-self.val)
    
    def __int__(self):
        return self.val
    
    def isOr(self):
        return self.val == 1

    def isAnd(self):
        return self.val == -1

    def __str__(self):
        return self.disp()

    def disp(self):
        return Op.ops[self.val]

    def dispTex(self):
        return Op.opsTex[self.val]

    def dispU(self):
        return Op.opsU[self.val]

    def __cmp__(self, other):
        if other is None:
            return 1
        else:
            return cmp(self.val, other.val)

    def __hash__(self):
        return self.val
       
class Neg(object):
    symb = ['', '! ']
    symbTex = ['', '$\\neg$ ']
    symbU = ['', SYM.SYM_NOT]

    ################# START FOR BACKWARD COMPATIBILITY WITH XML
    patt = '(?P<neg>'+symb[1].strip()+')'
    ################# END FOR BACKWARD COMPATIBILITY WITH XML

    def __init__(self, nNeg=False):
        if nNeg == True or nNeg < 0:
            self.neg = -1
        else:
            self.neg = 1

    def copy(self):
        return Neg(self.neg)

    def boolVal(self):
        return self.neg < 0

    def flip(self):
        self.neg *= -1
    
    def __int__(self):
        return self.neg
    
    def __cmp__(self, other):
        if other is None:
            return 1
        else:
            return cmp(self.neg, other.neg)

    def __hash__(self):
        return self.neg

    def __str__(self):
        return self.disp()

    def disp(self):
        return Neg.symb[self.boolVal()]

    def dispTex(self):
        return Neg.symbTex[self.boolVal()]

    def dispU(self):
        return Neg.symbU[self.boolVal()]

class Term(object):
    
    pattVName = VARIABLE_MARK+"%d"
    type_id = 0

    ################# START FOR BACKWARD COMPATIBILITY WITH XML
    patt = '(?P<col>[^\\=<>'+ SYM.SYMU_LEQ + SYM.SYMU_EIN + SYM.SYMU_NIN +']+)'
    ################# END FOR BACKWARD COMPATIBILITY WITH XML
    
    def __init__(self, ncol):
        self.col = ncol

    def valRange(self):
        return [None, None]

    def setRange(self, newR):
        pass

    def getComplement(self):
        return None

    def isComplement(self, term):
        return False

#     def simple(self, neg):
#         return neg

    def copy(self):
        return Term(self.col)

    def cmpType(self, other):
        if other is None:
            return 1
        else:
            return cmp(self.typeId(), other.typeId())
    
    def colId(self):
        return self.col

    def typeId(self):
        return self.type_id
    
    def cmpCol(self, other):
        if other is None:
            return 1
        else:
            return cmp(self.col, other.col)
    
    def __str__(self):
        return (Term.pattVName + ' ') % self.col
    
class BoolTerm(Term):
    type_id = 1

    def valRange(self):
        return [True, True]
        
    def copy(self):
        return BoolTerm(self.col)
    
    def __cmp__(self, other):
        if self.cmpCol(other) == 0:
            return self.cmpType(other)
        else:
            return self.cmpCol(other)
        
    def __hash__(self):
        return self.col
    
    def __str__(self):
        return self.disp()

    def truthEval(self, variableV):
        return variableV

    def disp(self, neg=None, names = None, lenIndex=0):
        if type(neg) == bool:
            neg = Neg(neg)

        if neg is None:
            strneg = ''
        else:
            strneg = neg.disp()
        if lenIndex > 0 :
            lenIndex = max(lenIndex-1,3)
            slenIndex = str(lenIndex)
        else:
            slenIndex = ''
        if type(names) == list  and len(names) > 0:
            lab = ('%s%'+slenIndex+'s') % (strneg, names[self.col])
            if len(lab) > lenIndex & lenIndex > 0:
                lab = lab[:lenIndex]
            return lab + ' '
        else:
            return ('%s'+Term.pattVName) % (strneg, self.col)

    def dispTex(self, neg, names = None):
        if type(neg) == bool:
            neg = Neg(neg)

        if type(names) == list  and len(names) > 0:
            return '%s%s' % ( neg.dispTex(), names[self.col])
        else:
            return ('%s$'+Term.pattVName+'$') % ( neg.dispTex(), self.col)

    def dispU(self, neg, names = None):
        if type(neg) == bool:
            neg = Neg(neg)

        if type(names) == list  and len(names) > 0:
            return u'%s%s' % ( neg.dispU(), names[self.col])
        else:
            return (u'%s'+Term.pattVName) % ( neg.dispU(), self.col)

    ################# START FOR BACKWARD COMPATIBILITY WITH XML
    patt = ['^\s*'+Neg.patt+'?\s*'+Term.patt+'\s*$']
    def parse(partsU):
        ncol = None
        if partsU is not None:
            neg = (partsU.group('neg') is not None)
            tmpcol = partsU.group('col').strip()
            try:
                ncol = int(tmpcol)
            except ValueError, detail:
                ncol = None
                raise Warning('In boolean term %s, column is not convertible to int (%s)\n'%(tmpcol, detail))
        if ncol is not None :
            return (neg, BoolTerm(ncol))
        return (None, None)
    parse = staticmethod(parse)
    ################# END FOR BACKWARD COMPATIBILITY WITH XML
    
class CatTerm(Term):
    type_id = 2
    basis_cat = "c?"
    
    def __init__(self, ncol, ncat):
        self.col = ncol
        self.cat = ncat

    def getCat(self):
        return self.cat
    
    def valRange(self):
        if self.cat == self.basis_cat:
            return ["#LOW#", "#HIGH#"]
        return [self.getCat(), self.getCat()]

    def setRange(self, cat):
        self.cat = cat #codecs.encode(cat, 'utf-8','replace')
            
    def copy(self):
        return CatTerm(self.col, self.cat)
            
    def __cmp__(self, other):
        if self.cmpCol(other) == 0:
            if self.cmpType(other) == 0:
                return cmp(self.cat, other.cat)
            else:
                return self.cmpType(other)
        else:
            return self.cmpCol(other)

    def truthEval(self, variableV):
        return variableV == self.cat
    
    def __hash__(self):
        return self.col*hash(self.cat)+(self.col-1)*(hash(self.cat)+1)

    def __str__(self):
        return self.disp()
    
    def disp(self, neg=None, names = None, lenIndex=0):
        if type(neg) == bool:
            neg = Neg(neg)

        if neg is None:
            strneg = ''
        else:
            strneg = neg.disp()
        strcat = '=%s' % self.cat
        if lenIndex > 0 :
            lenIndex = max(lenIndex-len(strcat),3)
            slenIndex = str(lenIndex)
        else:
            slenIndex = ''
        if type(names) == list  and len(names) > 0:
            lab = ('%s%'+slenIndex+'s') % (strneg, names[self.col])
            if len(lab) > lenIndex & lenIndex > 0:
                lab = lab[:lenIndex]
            return lab + strcat
        else:
            return (('%s'+Term.pattVName) % (strneg, self.col)) + strcat

    def dispTex(self, neg, names = None):
        if type(neg) == bool:
            neg = Neg(neg)
        if neg.boolVal():
            symbIn = '\\in'
        else:
            symbIn = '\\not\\in'
        
        if type(names) == list  and len(names) > 0:
            return '%s $%s$ %s' % (names[self.col], symbIn, self.cat)
        else:
            return ('$'+Term.pattVName+' %s$ %s') % (self.col, symbIn, self.cat)

    def dispU(self, neg, names = None):
        if type(neg) == bool:
            neg = Neg(neg)

        if neg.boolVal():
            symbIn = SYM.SYM_NEQ
        else:
            symbIn = '='
        if type(names) == list  and len(names) > 0:
            try:
                return ('[%s '+symbIn+' %s]') % (names[self.col], self.getCat())
            except UnicodeDecodeError:
                pdb.set_trace()
                self.getCat()
        else:
            return ('['+Term.pattVName+' '+symbIn+' %s]') % (self.col, self.getCat())

    ################# START FOR BACKWARD COMPATIBILITY WITH XML
    patt = ['^\s*'+Neg.patt+'?\s*'+Term.patt+'\s*\=\s*(?P<cat>\S*)\s*$']
    def parse(partsU):
        ncol = None
        if partsU is not None:
            neg = (partsU.group('neg') is not None)
            tmpcol = partsU.group('col').strip()
            try:
                ncol = int(tmpcol)
            except ValueError, detail:
                ncol = None
                raise Warning('In categorical term %s, column is not convertible to int (%s)\n'%(tmpcol, detail))
            try:
                cat = partsU.group('cat')
            except ValueError, detail:
                ncol = None
                raise Warning('In categorical term %s, category is not convertible to int (%s)\n'%(partsU.group('cat'), detail))
        if ncol is not None :
            return (neg, CatTerm(ncol, cat))
        return (None, None)
    parse = staticmethod(parse)
    ################# END FOR BACKWARD COMPATIBILITY WITH XML
    
class NumTerm(Term):
    type_id = 3
    
    def __init__(self, ncol, nlowb, nupb):
        if numpy.isinf(nlowb) and numpy.isinf(nupb) or nlowb > nupb:
            raise Warning('Unbounded numerical term !')
        self.col = ncol
        self.lowb = nlowb
        self.upb = nupb

    def getComplement(self):
        if numpy.isinf(self.lowb):
            return NumTerm(self.col, self.upb, float("Inf"))
        elif numpy.isinf(self.upb):
            return NumTerm(self.col, float("-Inf"), self.lowb)
        return None

    def isComplement(self, term):
        if term.type_id == self.type_id:
            return (numpy.isinf(self.lowb) and numpy.isinf(term.upb) and term.lowb == self.upb) or \
                   (numpy.isinf(term.lowb) and numpy.isinf(self.upb) and self.lowb == term.upb)
        else:
            return False
#     def simple(self, neg):
#         if neg:
#             if self.lowb == float('-Inf'):
#                 self.lowb = self.upb
#                 self.upb = float('-Inf')
#                 neg = False
#             elif self.upb == float('-Inf'):
#                 self.upb = self.lowb
#                 self.lowb = float('-Inf')
#                 neg = False
#         return neg

    def valRange(self):
        return [self.lowb, self.upb]

    def setRange(self, bounds):
        if numpy.isinf(bounds[0]) and numpy.isinf(bounds[1]) or bounds[0] > bounds[1]:
            raise Warning('Unbounded numerical term !')
        self.lowb = bounds[0]
        self.upb = bounds[1]
            
    def copy(self):
        return NumTerm(self.col, self.lowb, self.upb)

    def getUpb(self):
        return self.upb
    def getLowb(self):
        return self.lowb
    def isUpbounded(self):
        return not numpy.isinf(self.upb)
    def isLowbounded(self):
        return not numpy.isinf(self.lowb)
    
    def truthEval(self, variableV):
        return self.lowb <= variableV and variableV <= self.upb
                        
    def __cmp__(self, other):
        if self.cmpCol(other) == 0:
            if self.cmpType(other) == 0:
                if cmp(self.lowb, other.lowb) == 0:
                    return cmp(self.upb, other.upb)
                else:
                    return cmp(self.lowb, other.lowb)
            else:
                return self.cmpType(other)
        else:
            return self.cmpCol(other)
        
        if other is None:
            return 1
        elif cmp(self.col, other.col) == 0:
            if cmp(self.lowb, other.lowb) == 0:
                return cmp(self.upb, other.upb)
            else:
                return cmp(self.lowb, other.lowb)
        else:
            return cmp(self.col, other.col)
        
    def __hash__(self):
        return int(self.col+hash(self.lowb)+hash(self.upb))
    
    def __str__(self):
        return self.disp()

    def disp(self, neg=None, names = None, lenIndex=0):
        if type(neg) == bool:
            neg = Neg(neg)

        if neg is None:
            strneg = ''
        else:
            strneg = neg.disp()
            ### force float to make sure we have dots in the output
        if self.lowb > float('-Inf'):
            lb = '%s<' % float(self.lowb)
        else:
            lb = ''
        if self.upb < float('Inf'):
            ub = '<%s' % float(self.upb)
        else:
            ub = ''
        if lenIndex > 0 :
            lenIndex = max(lenIndex-len(lb)-len(ub),3)
            slenIndex = str(lenIndex)
        else:
            slenIndex = ''
        if type(names) == list  and len(names) > 0:
            lab = ('%'+slenIndex+'s') % names[self.col]
            if len(lab) > lenIndex & lenIndex > 0:
                lab = lab[:lenIndex]
            return lb + lab + ub
        else:
            return strneg+lb+(Term.pattVName % self.col) + ub

    def dispTex(self, neg, names = None, prec=None):            
        # prec = "0.4"
        trimm = False
        if prec is None:
            trimm = True
            prec = ""
        if type(neg) == bool:
            neg = Neg(neg)
            ### force float to make sure we have dots in the output
        if self.lowb > float('-Inf'):
            val = ('%'+prec+'f') % float(self.lowb)
            if trimm:
                val = val.rstrip("0").rstrip(".")
            lb = '$['+val+'\\leq{}'
        else:
            lb = '$['
        if self.upb < float('Inf'):
            val = ('%'+prec+'f') % float(self.upb)
            if trimm:
                val = val.rstrip("0").rstrip(".")
            ub = '\\leq{}'+val+']$'
        else:
            ub = ']$'
        negstr = ' %s' % neg.dispTex()
        if type(names) == list  and len(names) > 0:
            idcol = '$ %s $' % names[self.col]
        else:
            idcol = Term.pattVName % self.col
        return ''+negstr+lb+idcol+ub+''

    def dispU(self, neg, names = None):
        if type(neg) == bool:
            neg = Neg(neg)
            ### force float to make sure we have dots in the output
        if self.lowb > float('-Inf'):
            lb = ('[%s '+ SYM.SYM_LEQ +' ') % float(self.lowb)
        else:
            lb = '['
        if self.upb < float('Inf'):
            ub = (' '+ SYM.SYM_LEQ +' %s]') % float(self.upb)
        else:
            ub = ']'
        negstr = '%s' % neg.dispU()
        if type(names) == list  and len(names) > 0:
            idcol = '%s' % names[self.col]
        else:
            idcol = Term.pattVName % self.col
        try:
            return negstr+lb+idcol+ub
        except UnicodeDecodeError:
            return negstr+lb+"v"+str(self.col)+ub

    ################# START FOR BACKWARD COMPATIBILITY WITH XML
    num_patt = '-?\d+\.\d+'
    patt = ['^\s*'+Neg.patt+'?\s*'+Term.patt+'\s*\>\s*(?P<lowb>'+num_patt+')\s*\<\s*(?P<upb>'+num_patt+')\s*$',
            '^\s*'+Neg.patt+'?\s*'+Term.patt+'\s*\>\s*(?P<lowb>'+num_patt+')\s*$',
            '^\s*'+Neg.patt+'?\s*'+Term.patt+'\s*\<\s*(?P<upb>'+num_patt+')\s*$']
    def parse(partsU):
        ncol=None
        if partsU is not None :
            neg = (partsU.group('neg') is not None)
            lowb = float('-inf')
            upb = float('inf')
            
            tmpcol = partsU.group('col').strip()
            try:
                ncol = int(tmpcol)
            except ValueError, detail:
                ncol = None
                raise Warning('In numerical term %s, column is not convertible to int (%s)\n'%(tmpcol, detail))

            if 'lowb' in partsU.groupdict() and partsU.group('lowb') is not None:
                tmplowbs = partsU.group('lowb')
                try:
                    lowb = float(tmplowbs)
                except ValueError, detail:
                    ncol = None
                    raise Warning('In numerical term %s, lower bound is not convertible to float (%s)\n'%(tmplowbs, detail))

            if 'upb' in partsU.groupdict() and partsU.group('upb') is not None:
                tmpupbs = partsU.group('upb')
                try:
                    upb = float(tmpupbs)
                except ValueError, detail:
                    ncol = None
                    raise Warning('In numerical term %s, upper bound is not convertible to float (%s)\n'%(tmpupbs, detail))
            
        if ncol is not None and (lowb != float('-inf') or upb != float('inf')) and lowb <= upb:
            return (neg, NumTerm(ncol, lowb, upb))
        return (None, None)
    parse = staticmethod(parse)
    ################# END FOR BACKWARD COMPATIBILITY WITH XML

               
class Literal(object):

    ### types ordered for parsing
    termTypes = [{'class': NumTerm }, \
                 {'class': CatTerm }, \
                 {'class': BoolTerm }]

    
    def __init__(self, nneg, nterm):
        self.term = nterm ## Already an Term instance
        self.neg = Neg(nneg)

    def copy(self):
        return Literal(self.neg.boolVal(), self.term.copy())

    def valRange(self):
        if self.typeId() == 1:
            return [not self.neg.boolVal(), not self.neg.boolVal()]
        else:
            return self.getTerm().valRange()

    def __str__(self):
        return self.disp()

    def disp(self, names = None, lenIndex=0):
        return self.getTerm().disp(self.neg, names, lenIndex)

    def dispTex(self, names = None):
        return self.getTerm().dispTex(self.neg, names)
    
    def dispU(self, names = None):
        return self.getTerm().dispU(self.neg, names)

    def tInfo(self, names = None):
        return self.getTerm().tInfo(names)

    def __cmp__(self, other):
        if other is None or not isinstance(other, Literal):
            return 1
        elif cmp(self.getTerm(), other.getTerm()) == 0:
            return cmp(self.neg, other.neg)
        elif self.getTerm().isComplement(other.getTerm()) and self.neg != other.neg:
            return 0
        else:
            return cmp(self.getTerm(), other.getTerm())
     
    def __hash__(self):
        return hash(self.getTerm())+hash(self.neg)

    def getTerm(self):
        return self.term

    def colId(self):
        return self.getTerm().colId()

    def typeId(self):
        return self.getTerm().typeId()
    
    def isNeg(self):
        return self.neg.boolVal()

    def setNeg(self, neg):
        self.neg = Neg(neg)

    def flip(self):
        self.neg.flip()

    def cmpFlip(self, term):
        if other is None or not isinstance(other, Literal):
            return 1
        elif cmp(self.getTerm(), other.getTerm()) == 0:
            return 1-cmp(self.neg, other.neg)
        elif self.getTerm().isComplement(other.getTerm()) and self.neg == other.neg:
            return 0
        else:
            return cmp(self.getTerm(), other.getTerm())

    def truthEval(self, variableV):
        if self.isNeg():
            return not self.getTerm().truthEval(variableV)
        else:
            return self.getTerm().truthEval(variableV)
            
    ################# START FOR BACKWARD COMPATIBILITY WITH XML
    def parse(string):
        i = 0
        term = None
        while i < len(Literal.termTypes) and term is None:
            patts = Literal.termTypes[i]['class'].patt
            j = 0
            while j < len(patts) and term is None:
                parts = re.match(patts[j], string)
                if parts is not None:
                    (neg, term) = Literal.termTypes[i]['class'].parse(parts)
                j+=1
            i+=1
        if term is not None:
            return Literal(neg, term)
        else:
            return None
    parse = staticmethod(parse)
    ################# END FOR BACKWARD COMPATIBILITY WITH XML

class QTree(object):

    branchN, branchY  = (0, 1)
    
    def __init__(self, root_id=None, branches=None, fill=False, broken=False):
        self.root_id = root_id
        self.tree = {root_id: {"children": [[],[]], "depth": 0}}
        self.leaves = set()
        self.supps = None
        self.Ys = None
        self.Xs = None
        self.max_depth = 0
        self.broken = broken
        if branches is not None:
            self.build(branches)
            if fill:
                self.fill()

    def copy(self):
        cp = QTree(root_id=self.root_id)
        cp.tree = copy.deepcopy(self.tree)
        cp.leaves = set(self.leaves)
        cp.supps = copy.deepcopy(self.supps)
        cp.Ys = copy.deepcopy(self.Ys)
        cp.Xs = copy.deepcopy(self.Xs)
        cp.max_depth = self.max_depth
        return cp
            
    def __str__(self):
        return self.dispNode(self.root_id)

    def isBroken(self):
        return self.broken
    
    def dispNode(self, nid):
        if self.isBroken():
            return "Broken Tree"
        strn = ""
        if "split" in self.tree[nid]:
            if self.supps is not None:
                sc = self.supps.get(nid, [])
                st = sum(sc)
                suppsn = " + ".join(map(str, self.supps.get(nid, []))) + ( " = %d" % st )
            else:
                suppsn = ""
            if self.Ys is not None:
                yn = str(self.Ys.get(nid, ""))
            else:
                yn = ""
            strn += "%s'-- (%d) %d:N %s%s[%s]\t%s\n" % ("\t" * self.tree[nid]["depth"], nid,
                                                    self.tree[nid]["ynb"], self.tree[nid]["split"],
                                                    "\t" * self.max_depth, suppsn, yn)
        if "children" in self.tree[nid]:
            for ynb in [0,1]:
                for node in self.tree[nid]["children"][ynb]:
                    strn += self.dispNode(node)
        else:
            if self.supps is not None:
                sc = [len(s) for s in self.supps.get((nid, "L"), [])]
                st = sum(sc)
                suppsn = " + ".join(map(str, self.supps.get(nid, []))) + ( " = %d" % st )
            else:
                suppsn = ""
            if self.Ys is not None:
                yn = str(self.Ys.get(nid, "")) + "---" + str(self.Ys.get((nid, "L"), ""))
            else:
                yn = ""
            strn += "%s'-- (%d) %d:L %s%s[%s]\t%s\n" % ("\t" * self.tree[nid]["depth"], nid,
                                                    self.tree[nid]["ynb"], self.tree[nid]["leaf"],
                                                    "\t" * self.max_depth, suppsn, yn)
        return strn

    def hasNode(self, node):
        return node in self.tree
    def isRootNode(self, node):
        return node == self.root_id
    def isLeafNode(self, node):
        return node in self.tree and "leaf" in self.tree[node]
    def isLeafInNode(self, node):
        return node in self.tree and self.tree[node].get("leaf", None) >= 0
    def isLeafOutNode(self, node):
        return node in self.tree and self.tree[node].get("leaf", None) == -1
    def isSplitNode(self, node):
        return node in self.tree and "split" in self.tree[node]
    def isParentNode(self, node):
        return node in self.tree and "children" in self.tree[node]

    def getMaxDepth(self):
        return self.max_depth
    def getLeaves(self):
        return self.leaves

    def getNodeSplit(self, node):
        return self.tree[node]["split"]
    def getNodeBranch(self, node):
        return self.tree[node]["ynb"]
    def getNodeLeaf(self, node):
        return self.tree[node]["leaf"]
    def getNodeParent(self, node):
        return self.tree[node]["parent"]
    def getNodeChildren(self, node, ynb):
        return self.tree[node]["children"][ynb]
    def nbNodeChildren(self, node, ynb):
        return len(self.tree[node]["children"][ynb])
    def trimNodeChildren(self, node, ynb):
        while len(self.tree[node]["children"][ynb]) > 0:
            c = self.tree[node]["children"][ynb].pop()
            if self.isParentNode(c):
                self.trimNodeChildren(c, 0)
                self.trimNodeChildren(c, 1)
            else:
                self.leaves.discard(c)

    def getNodeXY(self, node):
        if self.Ys is not None and self.Xs is not None:
            return (self.Xs[self.tree[node]["depth"]], self.Ys[node])
        return (None, None)

    def getBranchQuery(self, node):
        cn = node
        buk = []
        while self.getNodeParent(cn) is not None:
            prt = self.getNodeParent(cn)
            neg = cn in self.getNodeChildren(prt, self.branchN)
            tmp = self.getNodeSplit(prt)
            if neg and tmp.type_id == NumTerm.type_id and tmp.getComplement() is not None:
                buk.insert(0, Literal(not neg, tmp.getComplement()))
                ## print neg, tmp, "=>", buk[0]
            else:
                buk.insert(0, Literal(neg, tmp))
                ## print neg, tmp, "->", buk[0]
            cn = prt
        return buk

    def getQuery(self):
        buks = []
        for node in self.leaves:
            if self.isLeafInNode(node):
                buks.append((node, self.getBranchQuery(node)))
        buks.sort(key=lambda x: (self.getNodeLeaf(x[0]), x[0]))
        qu = Query()
        if len(buks) == 1:
            if len(buks[0][1]) == 1:
                qu.op = Op(0)
            else:
                qu.op = Op(-1)
            qu.buk = buks[0][1]
        else:
            qu.op = Op(1)
            qu.buk = []
            for x in buks:
                if len(x[1]) ==1:
                    qu.buk.append(x[1][0])
                else:
                    qu.buk.append(x[1])
        return qu
        
    def getSimpleQuery(self):
        cp = self.copy()
        cp.recSimply(cp.root_id)
        return cp.getQuery().toTree().getQuery()

    def recSimply(self, node):
        if self.isLeafNode(node):
            if self.isLeafInNode(node):
                return 1
            else:
                return -1

        else:
            pr = [None, None]
            for ynb in [0,1]:
                if ynb == QTree.branchY or not self.isRootNode(node):
                    chlds = self.getNodeChildren(node, ynb)
                    if len(chlds) > 0:
                        tmppr = set([self.recSimply(c) for c in chlds])
                        pr[ynb] = max(tmppr)
                        if pr[ynb] == 1:
                            self.trimNodeChildren(node, ynb)
                            self.addLeafNode(node, ynb, 1)
            if pr[0] == pr[1]:
                return pr[0]
            else:
                return 0
    
    def getBottomX(self):
        if self.Xs is not None:
            return self.Xs[-1]
        return None

    def getNodeSupps(self, node):
        if self.supps is not None:
            return self.supps[node]
        return None
    def getNodeSuppSets(self, node):
        if self.supps is not None and self.isLeafNode(node):
            return self.supps[(node, "L")]
        return None

    def setNodeLeaf(self, node, bid):
        if node in self.tree and "leaf" in self.tree[node]:
            self.tree[node]["leaf"] = bid

    def setNodeLeaf(self, node, bid):
        if node in self.tree and "leaf" in self.tree[node]:
            self.tree[node]["leaf"] = bid

    def addSplitNode(self, pid, ynb, split):
        if pid in self.tree:
            tid = len(self.tree)
            self.tree[tid] = {"split": split, "children": [[],[]], "parent": pid,
                              "depth": self.tree[pid]["depth"]+1, "ynb": ynb}
            self.tree[pid]["children"][ynb].append(tid)
            if self.tree[tid]["depth"] > self.max_depth:
                self.max_depth = self.tree[tid]["depth"]
            return tid

    def addLeafNode(self, pid, ynb, bid):
        if pid in self.tree:
            tid = len(self.tree)
            self.tree[tid] = {"leaf": bid, "parent": pid,
                              "depth": self.tree[pid]["depth"]+1, "ynb": ynb}
            self.tree[pid]["children"][ynb].append(tid)
            self.leaves.add(tid)
            if self.tree[tid]["depth"] > self.max_depth:
                self.max_depth = self.tree[tid]["depth"]
            return tid

    def build(self, branches):
        if len(branches) > 0:
            commons = {}                    
            for bi, branch in enumerate(branches):
                for li, l in enumerate(branch):
                    if l.getTerm() in commons:
                        key = l.getTerm()
                        cpm = False 
                    else:
                        key = l.getTerm().getComplement()
                        cpm = True
                        if key is None or key not in commons:
                            key = l.getTerm()
                            cpm = False 
                            commons[key] = [[],[]]
                    ## is it the yes or no branch?
                    if (not cpm and not l.isNeg()) or (cpm and l.isNeg()):
                        commons[key][self.branchY].append((bi, li))
                    else:
                        commons[key][self.branchN].append((bi, li))
            self.recTree(range(len(branches)), commons, pid=None, fynb=QTree.branchY)

    def recTree(self, bids, commons, pid, fynb):
        mc = max([len(vs[0])+len(vs[1]) for vs in commons.values()])
        kks = [k for (k, vs) in commons.items() if len(vs[0])+len(vs[1])==mc]
        ### TODO choose the split
        # if len(kks) > 1:
        #     pdb.set_trace()
        # pdb.set_trace()
        pick = sorted(kks)[0]

        split_commons = [{},{},{}]
        to_ynbs = [[v[0] for v in commons[pick][0]], [v[0] for v in commons[pick][1]]]
        to_ynbs.append([bid for bid in bids if bid not in to_ynbs[0] and bid not in to_ynbs[1]])
        for k, vs in commons.items():
            vvs = [[[],[]],[[],[]],[[],[]]]
            if k != pick:
                for yn_org in [0,1]:
                    for v in vs[yn_org]:
                        if v[0] in to_ynbs[0]:
                            vvs[0][yn_org].append(v)
                        elif v[0] in to_ynbs[1]:
                            vvs[1][yn_org].append(v)
                        else:
                            vvs[2][yn_org].append(v)
            for ynb in [0,1,2]:
                if len(vvs[ynb][0])+len(vvs[ynb][1]) > 0:
                    split_commons[ynb][k]=vvs[ynb]

        tid = self.addSplitNode(pid, fynb, pick)
        for ynb in [0,1]:
            if len(split_commons[ynb]) > 0:
                self.recTree(to_ynbs[ynb], split_commons[ynb], tid, ynb)
            elif len(to_ynbs[ynb]) > 0:
                if len(to_ynbs[ynb]) == 1:
                    bid = to_ynbs[ynb][0]
                else:
                    print "Not exactly one branch ending in %d: %s!" % (tid, to_ynbs[ynb])
                    bid = None
                self.addLeafNode(tid, ynb, bid)

        if len(split_commons[2]) > 0:
            self.recTree(to_ynbs[2], split_commons[2], pid, fynb)
        elif len(to_ynbs[2]) > 0:
            print "Unexpected something"
            # pdb.set_trace()

    def fill(self):
        basic_nodes = self.tree.keys()
        for ni in basic_nodes:
            if "children" in self.tree[ni] and ni != self.root_id:
                for ynb in [0,1]:
                    if len(self.tree[ni]["children"][ynb]) == 0:
                        self.addLeafNode(ni, ynb, -1)

    def computeSupps(self, side, data, subsets=None):
        self.supps = {}
        if subsets is None:
            subsets = [data.rows()]
        self.recSupps(side, data, self.root_id, subsets)
        # print "SUPPORT %d" % side
        # print [(n, s) for (n, s) in self.supps.items() if type(n) is int]
        # pdb.set_trace()

    def recSupps(self, side, data, node, subsets):
        self.supps[node] = [len(s) for s in subsets]
        if self.isLeafNode(node):
            self.supps[(node, "L")] = subsets
        else:
            supps_node = [None, None, None] 
            if self.isSplitNode(node):
                supp, miss = data.literalSuppMiss(side, self.tree[node]["split"])
                supps_node[QTree.branchY] = [supp & s for s in subsets]
                supps_node[QTree.branchN] = [(s - supp) - miss  for s in subsets]
                supps_node[-1] = [s & miss for s in subsets]

            else:
                supps_node[QTree.branchY] = subsets
                supps_node[QTree.branchN] = [set() for s in subsets]
                supps_node[-1] = [set() for s in subsets]

            if self.isParentNode(node):
                for ynb in [0,1]:
                    # cs = tree[node]["children"][ynb]
                    # if len(cs) == 0 and node is not None:
                    #     supps[(node, "X%d" % ynb)] = supps_node[ynb]

                    for child in self.getNodeChildren(node, ynb):
                        self.recSupps(side, data, child, supps_node[ynb])
        
    def positionTree(self, side, all_width=1.0, height_inter=[1., 2.]):
        mdepth = self.getMaxDepth()
        width = all_width/(mdepth+1)
        self.Xs = [-2*(0.5-side)*(i+2)*width for i in range(mdepth+2)][::-1]
        leaves = []
        self.getLeavesYs(side, None, [0., 1.], leaves)
        leaves.sort(key=lambda x: x[-1])
        if len(leaves) < 2:
            width = 0
        else:
            width = (height_inter[1]-height_inter[0])/(len(leaves)-1)
        self.Ys = {}
        for li, leaf in enumerate(leaves):
            self.Ys[leaf[0]] = height_inter[0] + li*width
        self.setYs(side, None)

    def getLeavesYs(self, side, node, interval, leaves):
        if self.isLeafNode(node):
            leaves.append((node, (interval[1]+interval[0])/2.))
        elif self.isParentNode(node):
            eps = (interval[1]-interval[0])/10.
            mid = (interval[1]+interval[0])/2.
            for ynb, subint in [(QTree.branchN, (interval[0]+eps, mid)), (QTree.branchY, (mid, interval[1]-eps))]:
                if self.nbNodeChildren(node, ynb) > 0:
                    width = (subint[1]-subint[0])/self.nbNodeChildren(node, ynb)
                    for ci, child in enumerate(self.getNodeChildren(node, ynb)):
                        self.getLeavesYs(side, child, [subint[0]+ci*width, subint[0]+(ci+1)*width], leaves)

    def setYs(self, side, node):
        if self.isLeafNode(node):
            return self.Ys[node]

        elif self.isParentNode(node):
            ext_p = [[],[]]
            for ynb in [0,1]:
                for ci, child in enumerate(self.getNodeChildren(node, ynb)):
                    ext_p[ynb].append(self.setYs(side, child))
            if node is not None:
                self.Ys[node] = (numpy.max(ext_p[0]) + numpy.min(ext_p[1]))/2.01
            else:
                if len(ext_p[0])+len(ext_p[1]) > 0:
                    self.Ys[node] = numpy.mean(ext_p[0]+ext_p[1])
                else:
                    self.Ys[node] = 1.5 
        return self.Ys[node]
            
class Query(object):
    diff_literals, diff_cols, diff_op, diff_balance, diff_length = range(1,6)
    side = 0
    def __init__(self, OR=True, buk=None):
        self.op = Op(OR)
        if buk is not None:
            self.buk = buk
        else:
            self.buk = []

    def __len__(self):
        if len(self.buk) == 0:
            return 0
        return recurse_numeric(self.buk, function =lambda x: int(isinstance(x, Literal)))

    def __hash__(self):
        if len(self) == 0:
            return 0
        return hash(self.op) + recurse_numeric(self.buk, function =lambda x, trace: hash(t)+sum(trace), args = {"trace": []})

    def max_depth(self): # Does the query involve some disjunction?
        if len(self) == 0:
            return 0
        return max(recurse_list(self.buk, function =lambda x, trace: len(trace), args = {"trace":[]}))

    def usesOr(self): # Does the query involve some disjunction?
        max_d = self.max_depth()
        return max_d > 1 or ( len(self) > 1  and self.op.isOr() )
    
    def opBuk(self, nb): # get operator for bucket nb (need not exist yet).
        if nb % 2 == 0: # even bucket: query operator, else other
            return self.op.copy()
        else: 
            return self.op.other()

    def getBukElemAtR(self, path, buk=None, i=None):
        if i is None:
            i = len(path)-1
        if buk is None:
            buk = self.buk
        if path[i] < len(buk):
            if i == 0:
                return buk[path[i]]
            else:
                return self.getBukElemAt(path, buk[path[i]], i-1)
        return None
    def getBukElemAt(self, path, buk=None, i=None):
        if i is None:
            i = 0
        if buk is None:
            buk = self.buk
        if type(buk) is list and path[i] < len(buk):
            if i == len(path)-1:
                return buk[path[i]]
            else:
                return self.getBukElemAt(path, buk[path[i]], i+1)
        return None
        
    def copy(self):
        c = Query()
        c.op = self.op.copy()
        c.buk = recurse_deep(self.buk, function =lambda x: x.copy())
        return c

    def push_negation(self):
        def evl(b, flip=False):
            if isinstance(b, Literal):
                if flip:
                    b.flip()
                return (False, b) 
            else:
                now_flip = False
                neg = [bb for bb in b if isinstance(bb, Neg)]
                if len(neg) == 1:
                    b.remove(neg[0])
                    now_flip = True
                vs = []
                for bb in b:
                    sfliped, res = evl(bb, now_flip ^ flip)
                    if sfliped:
                        vs.extend(res)
                    else:
                        vs.append(res)
                return (now_flip, vs)
        if len(self) == 0:
            return
        sfliped, res =  evl(self.buk, False)
        self.buk = res
        if sfliped:
            self.op.flip()
        # print self
        # pdb.set_trace()
        # print "-------"

    def negate(self):
        if len(self) == 0:
            return
        neg = [bb for bb in self.buk if isinstance(bb, Neg)]
        if len(neg) == 1:
            self.buk.remove(neg[0])
        else:
            self.buk.insert(0, Neg(True))
        self.push_negation()
        # self.op.flip()
        # recurse_list(self.buk, function =lambda x: x.flip())
            
    def __cmp__(self, y):
        return self.compare(y)
            
    def compare(self, y): 
        if y is None:
            return 1
        try:
            if self.op == y.op and self.buk == y.buk:
                return 0
        except AttributeError:
            ### Such error means the buckets are not identical...
            pass
        
        if len(self) < len(y): ## nb of literals in the query, shorter better
            return Query.diff_length
        elif len(self) == len(y):
            if len(self.buk)  < len(y.buk) : ## nb of buckets in the query, shorter better
                return Query.diff_balance
            elif len(self.buk) == len(y.buk) :
                if self.op > y.op : ## operator
                    return Query.diff_op
                elif self.op == y.op :
                    if self.invCols() > y.invCols(): ## literals in the query
                        return Query.diff_cols
                    elif self.invCols() == y.invCols():
                        return Query.diff_literals
                    else:
                        return -Query.diff_cols
                else:
                    return -Query.diff_op
            else:
                return -Query.diff_balance
        else:
            return -Query.diff_length
    
    def comparePair(x0, x1, y0, y1): ## combined compare for pair
        if ( x0.op == y0.op and x0.buk == y0.buk and x1.op == y1.op and x1.buk == y1.buk ):
            return 0

        if len(x0) + len(x1) < len(y0) + len(y1): ## nb of terms in the query, shorter better
            return Query.diff_length
        
        elif len(x0) + len(x1) == len(y0) + len(y1):
            if len(x0.buk) + len(x1.buk) < len(y0.buk) + len(y1.buk): ## nb of sets of terms in the query, shorter better
                return Query.diff_balance
            elif len(x0.buk) + len(x1.buk) == len(y0.buk) + len(y1.buk):
                if max(len(x0), len(x1)) < max(len(y0), len(y1)): ## balance of the nb of terms in the query, more balanced is better
                    return Query.diff_balance
                elif max(len(x0), len(x1)) == max(len(y0), len(y1)):
                    if max(len(x0.buk), len(x1.buk) ) < max(len(y0.buk), len(y1.buk)): ## balance of the nb of sets of terms in the query, more balanced is better
                        return Query.diff_balance
                    
                    elif max(len(x0.buk), len(x1.buk) ) == max(len(y0.buk), len(y1.buk)):
                        if x0.op > y0.op : ## operator on the left
                            return Query.diff_op
                        elif x0.op == y0.op:
                            if x1.op > y1.op : ## operator on the right
                                return Query.diff_op
                            elif x1.op == y1.op:
                                if x0.invCols() > y0.invCols() :
                                    return Query.diff_cols
                                elif x0.invCols() == y0.invCols() :
                                    if x1.invCols() > y1.invCols() :
                                        return Query.diff_cols
                                    elif x1.invCols() == y1.invCols() :
                                        return Query.diff_literals
                                return -Query.diff_cols
                        return -Query.diff_op
            return -Query.diff_balance
        return -Query.diff_length
    comparePair = staticmethod(comparePair)
    
    def invCols(self):
        return set(recurse_list(self.buk, function =lambda term: term.colId()))
    
    def invLiterals(self):
        return set(recurse_list(self.buk, function =lambda term: term))

    def replace(self, depth_ind, replacement):
        if len(depth_ind) == 0:
            return replacement
        inr = depth_ind.pop()
        src = self.buk
        for i in depth_ind:
            src = src[i]
        tmp = [l for l in src]
        if replacement is None or (type(replacement) is list and len(replacement) == 0):
            tmp.pop(inr)
        else:
            tmp[inr] = replacement
        return self.replace(depth_ind, tmp)

    def minusOneRec(self, depth_ind, current_el):
        results = []
        if type(current_el) is list:
            for ni,next_el in enumerate(current_el):
                results.extend(self.minusOneRec(depth_ind+[ni], next_el))
        elif isinstance(current_el, Literal):
            qq = Query(self.op.isOr(), self.replace(list(depth_ind), None))
            qq.unfold()
            results.append((tuple(depth_ind), qq))
        return results
    
    def minusOneLiteral(self):
        return self.minusOneRec([], self.buk)

    def unfoldRec(self, buk):
        if isinstance(buk, Literal):
            return buk, False
        tmp = []
        for bi, bb in enumerate(buk):
            tpb, fl = self.unfoldRec(bb)
            if fl:
                tmp.extend(tpb)
            else:
                tmp.append(tpb)
        if type(tmp) is list and len(tmp) == 1:
            return tmp[0], not isinstance(tmp[0], Literal)
        return tmp, False

    def unfold(self):
        new_buk, opflip = self.unfoldRec(self.buk)
        if isinstance(new_buk, Literal):
            self.buk = [new_buk]
        else:
            self.buk = new_buk 
        if len(self.buk) < 2:
            self.op = Op()
        elif opflip:
            self.op.flip()
        
    def makeIndexesNew(self, format_str):
        if len(self) == 0:
            return ""
        return recurse_list(self.reorderedLits()[1], function =lambda term, trace: format_str % {'col': term.colId(), 'buk': ".".join(map(str,trace))}, args = {"trace":[]})
    
    def makeIndexes(self, format_str):
        if len(self) == 0:
            return ""
        return recurse_list(self.reorderedLits()[1], function =lambda term, trace: format_str % {'col': term.colId(), 'buk': len(trace)}, args = {"trace":[]})

    def isTreeCompatible(self):
        ### a DNF with several conjunctions
        ### or a single disjunction
        ### or a single conjunction
        ### or a single literal
        return (self.max_depth() == 2 and self.op.isOr()) or \
               (self.max_depth() == 1 and self.op.isOr()) or \
               (self.max_depth() == 1 and not self.op.isOr()) or \
               (len(self.buk) == 1 and isinstance(self.buk[0], Literal)) 
            
    def toTree(self, fill=False):
        broken = False
        branches = []
        if self.max_depth() == 2 and self.op.isOr():
            for buk in self.buk:
                if type(buk) is list:
                    branches.append(list(buk))
                else:
                    branches.append([buk])
        elif self.max_depth() == 1 and self.op.isOr():
            for buk in self.buk:
                branches.append([buk])
        elif (self.max_depth() == 1 and not self.op.isOr()) or \
                 (len(self.buk) == 1 and isinstance(self.buk[0], Literal)):
            branches.append(list(self.buk))
        else:
            print "Not a tree form!", self.disp(), self.buk
            broken = True
            #raise Warning("Not tree form!")

        return QTree(branches=branches, fill=True, broken=broken)

    
    ## return the truth value associated to a configuration
    def truthEval(self, config = {}):
        def evl(b, op, config = {}):
            if isinstance(b, Literal):
                return b.colId() in config and b.truthEval(config[b.colId()])                
            else:
                vs = [evl(bb, op.other(), config) for bb in b]
                if op.isOr():
                    return  sum(vs) > 0
                else:
                    return reduce(operator.mul, vs) > 0
        if len(self) == 0:
            return True
        cp = self.copy()
        cp.push_negation()
        return evl(cp.buk, cp.op, config)
    
    ## return the support associated to a query
    def recompute(self, side, data=None, restrict=None):
        def evl(b, op, side, data):
            if isinstance(b, Literal):
                return data.literalSuppMiss(side, b)
            else:
                vs = [evl(bb, op.other(), side, data) for bb in b]
                return SParts.partsSuppMissMass(op.isOr(), vs) 

        if len(self) == 0 or data==None:
            return (set(), set())
        else:
            cp = self.copy()
            cp.push_negation()
            sm = evl(cp.buk, cp.op, side, data) 
            if restrict is None:
                return sm
            else:
                return sm[0] & restrict, sm[1] & restrict

    def proba(self, side, data= None, restrict=None):
        def evl(b, op, side, data, restrict=None):
            if isinstance(b, Literal):
                if restrict is None:
                    return len(data.supp(side, b))/float(data.nbRows())
                else:
                    return len(data.supp(side, b) & restrict)/float(len(restrict))
            else:
                vs = [evl(bb, op.other(), side, data, restrict) for bb in b]
                return SParts.updateProbaMass(vs, op.isOr()) 

        if data is None:
            pr = -1
        elif len(self) == 0 :
            pr = 1
        else:
            cp = self.copy()
            cp.push_negation()
            pr = evl(cp.buk, cp.op, side, data, restrict)
        return pr

    def probaME(self, dbPr=None, side=None, epsilon=0):
        def evl(b, op, dbPr, side, epsilon):
            if isinstance(b, Literal):
                return dbPr.pointPrLiteral(side, literal, epsilon)                
            else:
                vs = [evl(bb, op.other(), dbPr, side, epsilon) for bb in b]
                return SParts.updateProbaMass(vs, op.isOr()) 

        if dbPr is None:
            pr = -1
        elif len(self) == 0 :
            pr = 1
        else:
            cp = self.copy()
            cp.push_negation()
            pr = evl(cp.buk, cp.op, dbPr, side, epsilon)
        return pr

    #### RESORT TODO FOR DEBUGGING
    def extend(self, op, literal, resort = True):
        if len(self) == 0:
            self.buk.append(literal)
        elif len(self) == 1:
            self.buk.append(literal)
            self.op = op
        elif op == self.op:
            self.buk.append(literal)
        else:
            self.op = self.op.other()
            self.buk = [self.buk, literal]
        if resort:
            self.doSort()

    def appendBuk(self, buk, op=None, resort=False):
        bid = None
        if op is None:
            op = Op(1)
        if len(self) == 0:
            bid = len(self.buk)
            self.buk.extend(buk)
            self.op = op.other()
        elif len(self) == 1 and self.buk != buk:
            bid = 1
            self.buk = [self.buk, buk]
            self.op = op
        elif self.op == op:
            if buk not in self.buk:
                bid = len(self.buk)
                self.buk.append(buk)
        else:
            if self.buk != buk:
                bid = 1
                self.op = self.op.other()
                self.buk = [self.buk, buk]
        if resort:
            self.doSort()
            bid = None
        return bid

    def doSort(self):
        def soK(x):
            if type(x) is list:
                return -1
            else:
                return x.colId()
        self.buk.sort(key=lambda x: soK(x))

    def listLiterals(self):
        def evl(b, lits):
            for bb in b:
                if isinstance(bb, Literal):
                    lits.append(bb)
                elif not isinstance(bb, Neg):
                    evl(bb, lits)
        lits = []
        if len(self) > 0:
            evl(self.buk, lits)
        return lits

    def listLiteralsDetails(self):
        def evl(b, lits, path):
            for bi, l in enumerate(b):
                if isinstance(l, Literal):
                    if l.getTerm() in lits:
                        key = l.getTerm()
                        cpm = False 
                    else:
                        key = l.getTerm().getComplement()
                        cpm = True
                        if key is None or key not in lits:
                            key = l.getTerm()
                            cpm = False 
                            lits[key] = []
                    lits[key].append((tuple(path+[bi]), cpm, not l.isNeg()))
                elif not isinstance(l, Neg):
                    evl(l, lits, path+[bi])
        lits = {}
        path = []
        if len(self) > 0:
            evl(self.buk, lits, path)
        return lits

    def isBasis(self, side, data):
        if len(self) == 1:
            ll = self.listLiterals()
            return data.literalIsBasis(side, ll[0])
        return False
        
    def __str__(self):
        return self.disp()    

    def reorderedLits(self, b=None):
        if b is None:
            b = self.buk
        if isinstance(b, Literal):
            return ((b.colId(), b.isNeg(), b.valRange()), b)
        elif isinstance(b, Neg):
            return (-1, b)
        else:
            if len(b) == 0:
                return ()
            vs = [self.reorderedLits(bb) for bb in b]
            vs.sort(key=lambda x: x[0])
            return (vs[0][0], [v[1] for v in vs])

    def reorderLits(self):
        if len(self) > 0:
            self.buk = self.reorderedLits()[1]

    def disp(self, names = None, lenIndex=0, style=""):
        def evl(b, op, names, lenIndex, style):
            if isinstance(b, Literal):
                return b.__getattribute__("disp"+style)(names)
            if isinstance(b, Neg):
                return "!NEG!"
            else:
                vs = [evl(bb, op.other(), names, lenIndex, style) for bb in b]
                if len(vs) == 1:
                    return vs[0]
                else:
                    jstr = " %s " % op.__getattribute__("disp"+style)()
                    if style == "Tex":
                        if re.search("[\(\)]", "".join(vs)):
                            pref = "$\\big($ "
                            suff = " $\\big)$"
                        else:
                            pref = "$($ "
                            suff = " $)$"
                    else:
                        pref = "( "
                        suff = " )"
                    if "!NEG!" in vs:
                        vs.remove("!NEG!")
                        pref = Neg(True).__getattribute__("disp"+style)() + pref
                    return pref + jstr.join(vs) + suff

        if len(self) == 0 :
            if style == "":
                return '[]'
            else:
                return ""
        else:
            vs = [evl(bb, self.op.other(), names, lenIndex, style) for bb in self.buk]
            if len(vs) == 1:
                return vs[0]
            else:
                jstr = " %s " % self.op.__getattribute__("disp"+style)()
                pref = ""
                suff = ""
                if "!NEG!" in vs:
                    vs.remove("!NEG!")
                    pref = Neg(True).__getattribute__("disp"+style)() + "( "
                    suff = " )"
                tmp = pref + jstr.join(vs) + suff
                if style == "Tex":
                    tmp = re.sub("\$\s+\$", " ", tmp)
                return tmp
            #### old code to write the query justified in length lenField
            #### string.ljust(qstr, lenField)[:lenField]

    def algExp(self):
        def evl(b, op, tmap):
            if isinstance(b, Literal):
                if b.getTerm() not in tmap:
                    key = b.getTerm().getComplement()
                    if b.isNeg():
                        return "t[%s]" % tmap[key]
                    else:
                        return "(not t[%s])" % tmap[key]
                elif b.isNeg():
                    return "(not t[%s])" % tmap[b.getTerm()]
                else:
                    return "t[%s]" % tmap[b.getTerm()]
            if isinstance(b, Neg):
                return "!NEG!"
            else:
                vs = [evl(bb, op.other(), tmap) for bb in b]
                if len(vs) == 1:
                    return vs[0]
                else:
                    if op.isOr():
                        jstr = " or "
                    else:
                        jstr = " and "
                    if "!NEG!" in vs:
                        vs.remove("!NEG!")
                        pref = "( not ("
                        suff = "))"
                    else:
                        pref = "( "
                        suff = " )"
                    return pref + jstr.join(vs) + suff

        if len(self) == 0 :
            return 'False', {}
        else:
            tmap = dict([(v,i) for (i,v) in enumerate(sorted(self.listLiteralsDetails().keys()))])
            vs = [evl(bb, self.op.other(), tmap) for bb in self.buk]
            if len(vs) == 1:
                return vs[0], tmap
            else:
                if self.op.isOr():
                    jstr = " or "
                else:
                    jstr = " and "
                if "!NEG!" in vs:
                    vs.remove("!NEG!")
                    pref = "( not ("
                    suff = "))"
                else:
                    pref = "( "
                    suff = " )"
                return pref + jstr.join(vs) + suff, tmap

    def truthTable(self):
        def recTT(lstr, vlist, nbvar):
            if nbvar == 0:
                if eval(lstr, {}, {"t": vlist}) == 1 :
                    return [vlist]
                else:
                    return []
            else:
                ####
                return recTT(lstr, [False]+vlist, nbvar-1)+recTT(lstr, [True]+vlist, nbvar-1)

        lstr, tmap = self.algExp()
        tb = recTT(lstr, [], len(tmap))
        return numpy.array(tb, dtype=numpy.int), tmap

    def algNormalized(self):
        tmp = Query()
        if len(self) > 0:
            tt, tmap = self.truthTable()
            stt = tt.copy()
            stt = simplerTT(stt)
            tlist = sorted(tmap.keys(), key=lambda x: tmap[x])
            branches = []
            for bi in range(stt.shape[0]):
                branches.append([Literal(1-stt[bi,ti], tlist[ti]) for ti in range(stt.shape[1]) if stt[bi,ti] != -1])
            if len(branches) > 0:
                # for b in branches:
                #     print [t.disp() for t in b]
                #pdb.set_trace()
                qt = QTree(branches=branches)
                tmp = qt.getQuery()
                tto, tmapo = tmp.truthTable()
                idsc = [tmap[l] for l in tmapo.keys()]
                dropC = [i for (l,i) in tmap.items() if l not in tmapo]
                ctt = tt
                if len(dropC) > 0:
                    keep_rows = numpy.all(tt[:, dropC]==1, axis=1)
                    ctt = tt[keep_rows,:][:,idsc]
                if numpy.sum(ctt != tto) >0:
                    print "----- SOMETHING WENT WRONG !"
                    pdb.set_trace()
        if len(self) == 0 and len(tmp) == 0:
            return tmp, False
        else:
            tmp.reorderLits()
            comp = self.reorderedLits()[1]
            if comp == tmp.buk and self.op == tmp.op:
                return tmp, False
            else:
                return tmp, True

        
    ################# START FOR BACKWARD COMPATIBILITY WITH XML
    def parseApd(string):
        bannchar = Op.ops[-1]+Op.ops[1]
        pattAny = '(?P<op>['+Op.ops[-1]+']|['+Op.ops[1]+'])'
        pattrn = '^(?P<pattIn>[^\\'+bannchar+']*)'+pattAny+'?(?P<pattOut>(?(op).*))$'
        op = None; r = None
        parts = re.match(pattrn, string)
        if parts is not None:
            r = Query()
        while parts is not None:
            t = Literal.parse(parts.group('pattIn'))
            if t is not None:
                r.extend(op, t, resort=False)
                if parts.group('op') is not None:
                    op = Op(parts.group('op')==Op.ops[1])
                    parts = re.match(pattrn, parts.group('pattOut'))
                else:
                    parts = None
            else:
                ## stop
                parts = None
                r = None
        if r is not None and len(r) == 0:
            r = Query()
        return r 
    parseApd = staticmethod(parseApd)
    ################# END FOR BACKWARD COMPATIBILITY WITH XML

    def parse(part, names = None, ids_map=None):
        if len(part.strip()) == 0 or part.strip() == "[]":
            return Query()
        qs = QuerySemantics(names, ids_map)
        parser = RedQueryParser(parseinfo=False, variable_mark=VARIABLE_MARK)
        try:
            tmp = parser.parse(part, "query", semantics=qs)
        except FailedParse as e:
            tmp = Query()
            raise Exception("Failed parsing query %s!\n\t%s" % (part, e))
        return tmp
    parse = staticmethod(parse)

# GENERATE PARSER:
#     python -m grako -m RedQuery -o redquery_parser.py redquery.ebnf (!!! REMOVE ABSOLUTE_IMPORT FROM GENERATED FILE)
# RUN:
#     python redquery_parser.py queries.txt QUERIES
class QuerySemantics(object):

    def __init__(self, names=None, ids_map=None):
        self.names = names
        self.ids_map = ids_map

    def query(self, ast):
        buk = []
        OR = 0
        if "conjunction" in ast:
            buk = ast["conjunction"]
            OR = False
        elif "disjunction" in ast:
            buk = ast["disjunction"]
            OR = True
        elif "literal" in ast:
            buk = ast["literal"].values()[0]
        if "mass_neg" in ast:
            buk.insert(0,Neg(True))
        return Query(OR, buk)

    def conjunction(self, ast):
        tmp = []
        for e in ast:
            if len(e) == 1:
                tmp.extend(e)
            else:
                tmp.append(e)
        return tmp

    def disjunction(self, ast):
        tmp = []
        for e in ast:
            if len(e) == 1:
                tmp.extend(e)
            else:
                tmp.append(e)
        return tmp

    def conj_item(self, ast):
        if "mass_neg" in ast.keys():
            del ast["mass_neg"]
            return [Neg(True)]+ast.values()[0]
        return ast.values()[0]

    def disj_item(self, ast):
        if "mass_neg" in ast.keys():
            del ast["mass_neg"]
            return [Neg(True)]+ast.values()[0]
        return ast.values()[0]

    def categorical_literal(self, ast):
        return [Literal(("neg" in ast) ^ ("cat_false" in ast.get("cat_test", {})),
                        CatTerm(self.parse_vname(ast.get("variable_name")), ast.get("category")))]

    def realvalued_literal(self, ast):
        return [Literal("neg" in ast, NumTerm(self.parse_vname(ast.get("variable_name")),
                                              float(ast.get("lower_bound", "-inf")),
                                              float(ast.get("upper_bound", "inf"))))]

    def boolean_literal(self, ast):
        return [Literal("neg" in ast, BoolTerm(self.parse_vname(ast.get("variable_name"))))]

    def variable_name(self, ast):
        return ast

    def category(self, ast):
        return ast

    def parse_vname(self, vname):
        tmp = re.match(VARIABLE_MARK+"(?P<id>\d+)$", vname)
        if tmp is not None:
            vv = int(tmp.group("id"))
            if self.ids_map is not None:
                return self.ids_map.get(vv, vv)
            return vv
        elif self.names is not None:
            if type(vname) is str and type(self.names[0]) is unicode:
                vname = codecs.decode(v, 'utf-8','replace')
            if vname in self.names:
                return self.names.index(vname)
            #print "No match"
            raise Exception("No matching variable")
        else:
            print vname
            # pdb.set_trace()
            raise Exception("No variables names provided when needed!")

if __name__ == '__main__':
    import codecs
    from classData import Data
    import sys
    rep = "/home/galbrun/TKTL/redescriptors/data/vaalikone/"
    data = Data([rep+"vaalikone_profiles_all.csv", rep+"vaalikone_questions_all.csv", {}, "Na"], "csv")
    qsLHS = QuerySemantics(data.getNames(0))
    qsRHS = QuerySemantics(data.getNames(1))
    parser = RedQueryParser(parseinfo=False)

    with open("../../runs/vaalikone_new/vaali_named.csv") as f:
        header = None
        for line in f:
            if header is None:
                header = line.strip().split("\t")
            elif len(line.strip().split("\t")) >= 2:
                resLHS = parser.parse(line.strip().split("\t")[0], "query", semantics=qsLHS)
                resRHS = parser.parse(line.strip().split("\t")[1], "query", semantics=qsRHS)
                pdb.set_trace()
                print "----------"
                print line.strip()
                print "ORG   :", resLHS, "---", resRHS
                print len(resLHS.recompute(0, data)[0])
                print len(resRHS.recompute(1, data)[0])

                # cp = resLHS.copy()
                # resLHS.push_negation()
                # print "COPY  :", cp
                # print "PUSHED:", resLHS
                # cp.negate()
                # print "NEG   :", cp
                # print resLHS.recompute(0, data)
                # print resRHS.recompute(1, data)
                # pdb.set_trace()
                # print len(resLHS)
                # print resLHS.listLiterals()
                # tmp = resLHS.copy()
                # print tmp
                # tmp.negate()
                # print tmp
                # print resLHS.disp(style="U", names=data.getNames(0)), "\t", resRHS.disp(style="U")
                # print resLHS.makeIndexesNew('%(buk)s:%(col)i:')
                # resLHS.reorderLits()
                # print resLHS.disp(style="U", names=data.getNames(0)), "\t", resRHS.disp(style="U")
