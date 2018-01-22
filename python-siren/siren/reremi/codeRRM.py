#!/usr/bin/python
import numpy, re, datetime, itertools
import pickle
import pdb
from classQuery import Term, BoolTerm, CatTerm, NumTerm
from classData import Data
from classRedescription import Redescription

def inex(prs):
    pout = 0
    for i in range(len(prs)):
        for c in itertools.combinations(prs, i+1):
            pout += (-1)**i * numpy.prod(c)
    return pout

def pr2cl(pr):
    if pr > 0:
        return -numpy.log2(pr)
    else:
        return float("inf")

def inter2nb(lowb, ub, prec):
    if lowb == ub:
        return 1
    else:
        return (ub-lowb)*10**prec


class ProbD:
    def getPr(self, v):
        return 0

    def copy(self):
        return ProbD()

class ProbDFix(ProbD):
    def __init__(self, v):
        self.v = v

    def __str__(self):
        return "ProbDFix v=%f" % (self.v)


    def copy(self):
        return ProbDFix(self.v)
        
    def getPr(self, v):
        if v == self.v:
            return 1
        return 0

    def scaledCopy(self, rnge):
        if rnge is not None and rnge == self.v:
            return ProbDFix(self.v)
        return None


class ProbDBinomial(ProbD):
    def __init__(self, p):
        self.p = p

    def __str__(self):
        return "ProbDBinomial p=%f" % (self.p)

    def copy(self):
        return ProbDBinomial(self.p)
        
    def getPr(self, v):
        if v:
            return self.p
        return 1-self.p

    def scaledCopy(self, rnge):
        if rnge is not None:
            return ProbDFix(rnge)
        return None

class ProbDDiscrete(ProbD):
    def __init__(self, ps):
        t = float(sum(ps.values()))
        self.ps = dict([(v,p/t) for (v,p) in ps.items()])

    def __str__(self):
        return "ProbDDiscrete ps=%s" % (self.ps)

    def copy(self):
        return ProbDDiscrete(self.ps)
        
    def getPr(self, v):
        return self.ps.get(v, 0)

    def scaledCopy(self, rnge):
        if rnge is not None:
            t = dict([(v,self.ps.get(v, 0)) for v in rnge])
            return ProbDDiscrete(t)
        return None

class ProbDCounts(ProbD):
    def __init__(self, ps):
        self.nb, self.nnz, self.zv, self.lv, self.uv = float(ps["nb"]), ps["nnz"], ps["zv"], int(ps["lv"]), int(ps["uv"]) 
        nbv = self.uv - self.lv
        if self.zv is None:
            self.Zpr = 0
            self.Opr = 1.0/(nbv+1)
        else:
            if self.zv < self.lv or self.zv > self.uv:
                nbv +=1
            if nbv > 0:
                self.Zpr = (self.nb-self.nnz)/self.nb
                self.Opr = self.nnz/(self.nb*nbv)
            else:
                self.Zpr = 1
                self.Opr = 0
        
    def __str__(self):
        return "ProbDCounts %d/%d zv=%s rnge=[%d,%d]" % (self.nnz, self.nb, self.zv, self.lv, self.uv)

    def copy(self):
        return ProbDCounts({"nb":self.nb, "nnz":self.nnz, "zv":self.zv, "lv":self.lv, "uv":self.uv})
        
    def getPr(self, v):
        if v == self.zv:
            return self.Zpr
        elif v >= self.lv and v <= self.uv:            
            return self.Opr
        return 0

    def scaledCopy(self, rnge):
        if rnge is not None:
            lb = max(rnge[0], self.lv)
            ub = min(rnge[1], self.uv)
            if self.zv < lb or self.zv > ub:
                zv = None
                nb = self.nnz
            else:
                zv = self.zv
                nb = self.nb
            return ProbDCounts({"nb":nb, "nnz":self.nnz, "zv":zv, "lv":lb, "uv":ub})
        return None

class ProbDContinuous(ProbD):
    def __init__(self, lb, ub, prec=1):
        self.bounds = (lb, ub)
        self.l = float(ub-lb)
        ## if numpy.isinf(self.l):
        ##    pdb.set_trace()
        ##    print self.l, ub, lb
        self.prec = float(prec)

    def __str__(self):
        # return "ProbDContinuous r=[%f,%f], prec=%f, v=%f" % (self.bounds[0], self.bounds[1], self.prec, self.getPr(self.bounds[0])*10**5)
        return "ProbDContinuous r=[%f,%f], prec=%f" % (self.bounds[0], self.bounds[1], self.prec)

    def copy(self):
        return ProbDContinuous(self.bounds[0], self.bounds[1], self.prec)
        
    def getPr(self, v):
        if type(v) in [float, int, numpy.float64]:
            if v <= self.bounds[1] and v >= self.bounds[0]:
                return 1/(10**self.prec*self.l +1)
            return 0
        elif len(v) == 2 and v[1] > v[0] and v[1] <= self.bounds[1] and v[0] >= self.bounds[0]:
            return (v[1]-v[0])/self.l
        return 0

    def scaledCopy(self, rnge):
        if rnge is not None:
            lb = max(rnge[0], self.bounds[0])
            ub = min(rnge[1], self.bounds[1])
            return ProbDContinuous(lb, ub, self.prec)
        return None

class ProbDGaussian(ProbD):
    def __init__(self, mu, sigma):
        self.mu = float(mu) 
        self.sigma = float(sigma)

    def __str__(self):
        return "ProbDGaussian mu=%f sigma=%s" % (self.mu, self.sigma)

    def copy(self):
        return ProbDGaussian(self.mu, self.sigma)
        
    def getPr(self, v):
        return numpy.exp(-v**2/2)/numpy.sqrt(2*numpy.pi)

class ColFactory:
    CT = { BoolTerm.type_id: "Bool",
           CatTerm.type_id: "Cat",
           NumTerm.type_id: "Num"}
    
    def getCol(side, ci, data, typeC, details={}):
        try:
            method_col =  eval("ColD" + typeC + ColFactory.CT.get(data.cols[side][ci].typeId(), "-"))
        except AttributeError:
            raise Exception('No ColD for this type (%s - %s)!'  %  (typeC, data.cols[side][ci].typeId()))
        c = method_col(side, ci, data, details)
        return c, c.getClsSum(data.cols[side][ci].getVector())
    getCol = staticmethod(getCol)

class ColD:
    def __init__(self, side, ci, data, details = {}):
        self.side = side
        self.ci = ci
        self.d = None

    def __str__(self):
        return "%s %d %d dist=%s" % (self.__class__.__name__, self.side, self.ci, self.d)

    def getD(self):
        return self.d

    def getPr(self, v, i):
        return 0

    def getLL(self, lit):
        return 0

    def getCl(self, v, i):
        p = self.getPr(v, i)
        # if p > 1:
        #     pdb.set_trace()
        if p > 0:
            return -numpy.log2(p)
        else:
            return float("inf")
        
    def getPrs(self, vs, ids=None):
        if ids is None:
            return [self.getPr(v, i) for i,v in enumerate(vs)]
        return [self.getPr(vs[i], i) for i in ids]
    def getPrsSum(self, vs, ids=None):
        return sum(self.getPrs(vs, ids))
    def getCls(self, vs, ids=None):
        if ids is None:
            return [self.getCl(v, i) for i,v in enumerate(vs)]
        return [self.getCl(vs[i], i) for i in ids]
    def getClsSum(self, vs, ids=None):
        return sum(self.getCls(vs, ids))


class ColDFull(ColD):
    def getPr(self, v, i):
        if self.d is not None:
            return self.d.getPr(v)
        return 0

class ColDFullBool(ColDFull):
    def __init__(self, side, ci, data, details = {}):
        ColDFull.__init__(self, side, ci, data, details)
        self.d = ProbDBinomial(float(data.cols[self.side][self.ci].sumCol())/data.cols[self.side][self.ci].nbRows())

    def getLL(self, lit):
        return pr2cl(self.getPr(not lit.isNeg(), None))

    def getPrsSum(self, vs, ids=None):
        if ids is None:
            c1 = sum(vs)
            c0 = len(vs) - c1
        else:
            c1 = sum([vs[i] for i in ids])
            c0 = len(ids) - c1
        return c1*self.getPr(True, None) + c0*self.getPr(False, None)

    def getClsSum(self, vs, ids=None):
        if ids is None:
            c1 = sum(vs)
            c0 = len(vs) - c1
        else:
            c1 = sum([vs[i] for i in ids])
            c0 = len(ids) - c1
        if c1 == 0:
            return c0*self.getCl(False, None)
        elif c0 == 0:
            return c1*self.getCl(False, None)
        else:
            return c1*self.getCl(True, None) + c0*self.getCl(False, None)

class ColDFullCat(ColDFull):
    def __init__(self, side, ci, data, details = {}):
        ColDFull.__init__(self, side, ci, data, details)
        self.d = ProbDDiscrete(dict([(c, len(data.cols[self.side][self.ci].suppCat(c))) for c in data.cols[self.side][self.ci].cats()]))

    def getLL(self, lit):
        return pr2cl(self.getPr(lit.getTerm().getCat(), None))

class ColDFullNum(ColDFull):
    def __init__(self, side, ci, data, details = {}):
        ColDFull.__init__(self, side, ci, data, details)
        tt = data.cols[self.side][self.ci].getVector()
        if type(tt) == dict and data.cols[self.side][self.ci].getPrec() == 0:
            lv, uv, nb = min(tt.values()), max(tt.values()), max(tt.keys())+1.0
            nbmd = nb - len(tt) + len([t for t in tt.values() if t == tt[-1]])
            self.d = ProbDCounts({"nb": nb, "nnz": nb-nbmd, "zv": tt[-1], "lv": lv, "uv":uv})
        else:
            self.d = ProbDContinuous(data.cols[self.side][self.ci].getMin(), data.cols[self.side][self.ci].getMax(), data.cols[self.side][self.ci].getPrec())

    def getLL(self, lit):
        ll = 2
        if lit.getTerm().isLowbounded():
            ll += pr2cl(self.getPr(lit.getTerm().getLowb(), None))
        if lit.getTerm().isUpbounded():
            ll += pr2cl(self.getPr(lit.getTerm().getUpb(), None))
        return ll

    def getPrs(self, vs, ids=None):
        if type(vs) == dict:
            if ids is None:
                ids = range(max(vs.keys())+1)
            return [self.getPr(vs.get(i, vs[-1]), i) for i in ids]
        if ids is None:
            return [self.getPr(v, i) for i,v in enumerate(vs)]
        return [self.getPr(vs[i], i) for i in ids]
    def getPrsSum(self, vs, ids=None):
        if type(vs) == dict and (ids is None or len(set(ids)) == max(vs.keys())):
            d = max(vs.keys())+1-len(vs)
            return sum([self.getPr(v, None) for v in vs.values()]) + d*self.getPr(vs[-1], None)
        else:
            return sum(self.getPrs(vs, ids))

    def getCls(self, vs, ids=None):
        if type(vs) == dict:
            if ids is None:
                ids = range(max(vs.keys())+1)
            return [self.getCl(vs.get(i, vs[-1]), i) for i in ids]
        if ids is None:
            return [self.getCl(v, i) for i,v in enumerate(vs)]
        return [self.getCl(vs[i], i) for i in ids]
    def getClsSum(self, vs, ids=None):
        if type(vs) == dict and (ids is None or len(set(ids)) == max(vs.keys())):
            d = max(vs.keys())+1-len(vs)
            return sum([self.getCl(v, None) for v in vs.values()]) + d*self.getCl(vs[-1], None)
        else:
            return sum(self.getCls(vs, ids))

class ColDDiff(ColD):
    def __init__(self, side, ci, data, details = {}):
        self.flipped = False
        self.side = side
        self.ci = ci
        self.d = None
        self.parent = details.get("parent", None)
        try:
            self.diffto = data.cols[side][self.parent].getVector()
        except IndexError:
            self.parent = None
            self.diffto = [0 for i in data.nbRows()]

    def flip(self, data):
        self.flipped = not self.flipped
        if self.parent is not None:
            self.ci, self.parent = self.parent, self.ci
            self.diffto = data.cols[self.side][self.parent].getVector()

    def getPr(self, v, i):
        if i is None:
            return self.d.getPr(v)
        if self.d is not None and i < len(self.diffto):
            if self.flipped:
                return self.d.getPr(self.diffto[i]-v)
            else:
                return self.d.getPr(v-self.diffto[i])
        return 0

class ColDDiffBool(ColDDiff):
    def __init__(self, side, ci, data, details = {}):
        ColDDiff.__init__(self, side, ci, data, details)
        tmp = [abs(v-self.diffto[i]) for i,v in enumerate(data.cols[self.side][self.ci].getVector())]
        self.d = ProbDBinomial(float(sum(tmp))/data.nbRows())

    def getPrsSum(self, vs, ids=None):
        if ids is None:
            if self.flipped:
                c1 =  sum([self.diffto[i]!=vs[i] for i in range(len(vs))])
            else:
                c1 =  sum([vs[i]!=self.diffto[i] for i in range(len(vs))])
            c0 = len(vs) - c1
        else:
            if self.flipped:
                c1 =  sum([self.diffto[i]!=vs[i] for i in ids])
            else:
                c1 =  sum([vs[i]!=self.diffto[i] for i in ids])
            c0 = len(ids) - c1
        if c1 == 0:
            return c0*self.getPr(False, None)
        elif c0 == 0:
            return c1*self.getPr(True, None)
        else:
            return c1*self.getPr(True, None) + c0*self.getPr(False, None)

    def getClsSum(self, vs, ids=None):
        if ids is None:
            if self.flipped:
                c1 =  sum([self.diffto[i]!=vs[i] for i in range(len(vs))])
            else:
                c1 =  sum([vs[i]!=self.diffto[i] for i in range(len(vs))])
            c0 = len(vs) - c1
        else:
            if self.flipped:
                c1 =  sum([self.diffto[i]!=vs[i] for i in ids])
            else:
                c1 =  sum([vs[i]!=self.diffto[i] for i in ids])
            c0 = len(ids) - c1
        return c1*self.getCl(True, None) + c0*self.getCl(False, None)


class ColDDiffCat(ColDDiff):
    def __init__(self, side, ci, data, details = {}):
        ColDDiff.__init__(self, side, ci, data, details)
        tmp = dict([(c, 0) for c in data.cols[side][ci].cats()])
        tmp[None] = 0
        for i,v in enumerate(data.cols[self.side][self.ci].getVector()):
            if v == self.diffto[i]:
                tmp[None] += 1
            else:
                tmp[v] += 1
        self.d = ProbDDiscrete(tmp)

class ColDDiffNum(ColDDiff):
    def __init__(self, side, ci, data, details = {}):
        ColDDiff.__init__(self, side, ci, data, details)
        vs = data.cols[self.side][self.ci].getVector()
        if type(self.diffto) == dict and type(vs) == dict:
            inters = set(self.diffto.keys()) & set(vs.keys())
            inters.remove(-1)
            tmp = [vs[k] - self.diffto[k] for k in inters]
            tmp.extend([vs[-1] - self.diffto[k] for k in set(self.diffto.keys()) - inters])
            tmp.extend([vs[k] - self.diffto[-1] for k in set(vs.keys()) - inters])
            if len(self.diffto)-1 + len(vs)-1 -len(inters) < max(vs.keys()):
                tmp.append(vs[-1]-self.diffto[-1])
        elif type(self.diffto) == dict:
            tmp = [v-self.diffto.get(i, self.diffto[-1]) for i,v in enumerate(vs)]
        elif type(vs) == dict:
            tmp = [vs.get(i, vs[-1])-dv for i,dv in enumerate(self.diffto)]
        else:
            tmp = [v-self.diffto[i] for i,v in enumerate(vs)]
        prec = data.cols[self.side][self.ci].getPrec()
        if self.parent is not None and data.cols[side][self.parent].getPrec() > prec:
            prec = data.cols[side][self.parent].getPrec()
        self.d = ProbDContinuous(min(tmp), max(tmp), prec)

    def getPr(self, v, i):
        if self.d is not None:
            if type(self.diffto) == dict:
                if i in self.diffto:
                    dv = self.diffto[i]
                else:
                    dv = self.diffto[-1]
            elif i < len(self.diffto):
                dv = self.diffto[i]
            else:
                return 0
            if self.flipped:
                return self.d.getPr(dv-v)
            else:
                return self.d.getPr(v-dv)
        return 0

    def getPrs(self, vs, ids=None):
        if type(vs) == dict:
            if ids is None:
                ids = range(max(vs.keys())+1)
            return [self.getPr(vs.get(i, vs[-1]), i) for i in ids]
        if ids is None:
            return [self.getPr(v, i) for i,v in enumerate(vs)]
        return [self.getPr(vs[i], i) for i in ids]
    def getPrsSum(self, vs, ids=None):
        return sum(self.getPrs(vs, ids))

    def getCls(self, vs, ids=None):
        if type(vs) == dict:
            if ids is None:
                ids = range(max(vs.keys())+1)
            return [self.getCl(vs.get(i, vs[-1]), i) for i in ids]
        if ids is None:
            return [self.getCl(v, i) for i,v in enumerate(vs)]
        return [self.getCl(vs[i], i) for i in ids]
    def getClsSum(self, vs, ids=None):
        return sum(self.getCls(vs, ids))


class LitFactory:
    CT = { BoolTerm.type_id: "Bool",
           CatTerm.type_id: "Cat",
           NumTerm.type_id: "Num"}
    
    def getLit(side, ci, data, supp, bkp, lit, rid=-1):
        try:
            method_col =  eval("LitD" + LitFactory.CT.get(data.cols[side][ci].typeId(), "-"))
        except AttributeError:
            raise Exception('No LitD for this type (%s)!'  %  data.cols[side][ci].typeId())
        c = method_col(side, ci, data, supp, bkp, {rid:lit})
        return c
    getLit = staticmethod(getLit)

class LitD:
    def __init__(self, side, ci=None, data=None, supp=None, bkp=None, lits={}, details=None):
        if ci is None: ### Copy
            self.side, self.ci = side.side, side.ci
            self.lits = dict(side.lits)
            self.suppI = set(side.suppI)
            self.rnge = side.rnge
            self.suppF = set(side.suppF)
            self.d = side.d.copy()
        else:
            self.side = side
            self.ci = ci
            self.lits = lits
            if details is not None:
                self.suppI = details["suppI"] & supp
                self.rnge = details["rnge"]
            else:
                self.suppI = self.interSupp(data, lits, supp)
                self.rnge = self.interRnge(data, lits)
            self.d = self.prepareD(self.rnge, bkp)
            self.suppF = set(supp - self.suppI)

    def __str__(self):
        return "%s %d %d range=%s, supp=%d/%d, d=%s" % (self.__class__.__name__, self.side, self.ci, str(self.rnge), len(self.suppI), len(self.suppF), self.d)

    def hasRid(self, rid):
        return rid in self.lits

    def copy(self):
        return LitD(self)
        
    def shrinkCopy(self, supp):
        t = self.copy()
        t.suppI &= supp
        t.suppF &= supp  
        return t

    def getSupp(self):
        return self.suppI 

    def getFallback(self):
        return self.suppF 

    def getD(self):
        return self.d

    def getPr(self, v, i):
        return self.d.getPr(v)

    def getCl(self, v, i):
        p = self.getPr(v, i)
        if p > 1:
#            pdb.set_trace()
            return 0
        if p > 0:
            return -numpy.log2(p)
        else:
#            pdb.set_trace()
            return float("inf")
        
    def getPrs(self, vs, ids=None):
        if type(vs) == dict:
            if ids is None:
                ids = range(max(vs.keys())+1)
            return [self.getPr(vs.get(i, vs[-1]), i) for i in ids]
        if ids is None:
            return [self.getPr(v, i) for i,v in enumerate(vs)]
        return [self.getPr(vs[i], i) for i in ids]
    def getPrsSum(self, vs, ids):
        if type(vs) == dict and (ids is None or len(set(ids)) == max(vs.keys())):
            d = max(vs.keys())+1-len(vs)
            return sum([self.getPr(v, None) for v in vs.values()]) + d*self.getPr(vs[-1], None)
        return sum(self.getPrs(vs, ids))

    def getCls(self, vs, ids=None):
        if type(vs) == dict:
            if ids is None:
                ids = range(max(vs.keys())+1)
            return [self.getCl(vs.get(i, vs[-1]), i) for i in ids]
        if ids is None:
            return [self.getCl(v, i) for i,v in enumerate(vs)]
        return [self.getCl(vs[i], i) for i in ids]
    def getClsSum(self, vs, ids):
        if type(vs) == dict and (ids is None or len(set(ids)) == max(vs.keys())):
            d = max(vs.keys())+1-len(vs)
            return sum([self.getCl(v, None) for v in vs.values()]) + d*self.getCl(vs[-1], None)
        return sum(self.getCls(vs, ids))

    def interSupp(self, data, lits, supp=None):
        if supp is None:
            suppI = set(range(data.nbRows()))
        else:
            suppI = set(supp)
        if lits is not None and len(lits) > 0:
            for lc in lits.values():
                suppI &= data.supp(self.side, lc)
        return suppI
    def interRnge(self, data, lits):
        return None
    def prepareD(self, rnge, bkp):
        if rnge is not None:
            return bkp.scaledCopy(rnge)
        return bkp.copy()

    def shiftedLits(self, lit, rid=-1):
        if rid == -1 and -1 in self.lits:
            tmp = {}
            for k,v in self.lits.items(): 
                if k < 0:
                    k-=1
                tmp[k] = v
        else:
            tmp = dict(self.lits)
        tmp[rid] = lit
        return tmp

    def delLits(self, rid):
        tmp = dict(self.lits)
        if rid in tmp:
            del tmp[rid]
        return tmp


class LitDBool(LitD):
    def copy(self):
        return LitDBool(self)

    def upRnge(self, rnge, lit):
        if rnge is None or lit.isNeg() == rnge:
            return None
        else:
            return rnge

    def interRnge(self, data, lits):
        if lits is not None and len(lits) > 0:
            v = lits.values()[0].isNeg()
            if len([o for o in lits.values() if o.isNeg() != v]) == 0:
                return not v
        return None


    def getPrsSum(self, vs, ids=None):
        if ids is None:
            c1 = sum(vs)
            c0 = len(vs) - c1
        else:
            c1 = sum([vs[i] for i in ids])
            c0 = len(ids) - c1
        return c1*self.getPr(True, None) + c0*self.getPr(False, None)

    def addCopy(self, lit, supp, data, rid=-1):
        ### supp relates to the support of the whole redescription
        ### suppI to the support of the literal
        details = {"suppI": self.suppI & data.supp(self.side, lit),
                   "rnge": self.upRnge(self.rnge, lit)}
        return LitDBool(self.side, self.ci, data, supp, self.d, self.shiftedLits(lit, rid), details)

    def removeCopy(self, rid, supp, bkp, data):
        return LitDBool(self.side, self.ci, data, supp, bkp, self.delLits(rid))


class LitDCat(LitD):
    def copy(self):
        t = LitDCat(self)
        if self.rnge is not None:
            self.rnge = set(self.rnge)
        return t
    
    def upRnge(self, rnge, lit):
        if rnge is not None:
            rnge = set(rnge)
            if lit.isNeg():
                rnge.discard(lit.getTerm().getCat())
            else:
                rnge &= set([lit.getTerm().getCat()])
        return rnge

    def interRnge(self, data, lits):
        if lits is not None and len(lits) > 0:
            cats = set(data.cols[self.side][self.ci].cats())
            tmp = lits.values()
            while len(tmp) > 0 and len(cats) > 0:
                lc = tmp.pop()
                cats = self.upRnge(cats, lc)
            return cats
        return set()

    def addCopy(self, lit, supp, data, rid=-1):
        ### supp relates to the support of the whole redescription
        ### suppI to the support of the literal
        details = {"suppI": self.suppI & data.supp(self.side, lit),
                   "rnge": self.upRnge(self.rnge, lit)}
        return LitDCat(self.side, self.ci, data, supp, self.d, self.shiftedLits(lit, rid), details)

    def removeCopy(self, rid, supp, bkp, data):
        return LitDCat(self.side, self.ci, data, supp, bkp, self.delLits(rid))


class LitDNum(LitD):
    def copy(self):
        t = LitDNum(self)
        if self.rnge is not None:
            self.rnge = list(self.rnge)
        return t
    
    def upRnge(self, rnge, lit):
        if lit.isNeg():
            ### DOES NOT WORK WITH NEGATIONS
            return rnge # [float("Inf"), float("-Inf")]
        elif rnge is None:
            rnge = lit.getTerm().valRange()
        else:
            rnge = list(rnge)
            if lit.getTerm().getLowb() > rnge[0]:
                rnge[0] = lit.getTerm().getLowb() 
            if lit.getTerm().getUpb() < rnge[1]:
                rnge[1] = lit.getTerm().getUpb()
        return rnge

    def interRnge(self, data, lits):
        if lits is not None and len(lits) > 0:
            rnge = [data.cols[self.side][self.ci].getMin(), data.cols[self.side][self.ci].getMax()]
            tmp = lits.values()
            while len(tmp) > 0 and rnge[0] <= rnge[1]:
                lc = tmp.pop()
                rnge = self.upRnge(rnge, lc)
            return rnge
        return None

    def addCopy(self, lit, supp, data, rid=-1):
        ### supp relates to the support of the whole redescription
        ### suppI to the support of the literal
        details = {"suppI": self.suppI & data.supp(self.side, lit),
                   "rnge": self.upRnge(self.rnge, lit)}
        return LitDNum(self.side, self.ci, data, supp, self.d, self.shiftedLits(lit, rid), details)

    def removeCopy(self, rid, supp, bkp, data):
        return LitDNum(self.side, self.ci, data, supp, bkp, self.delLits(rid))


class RedModel:
    def __init__(self, data, dm=None, filename=None):
        if dm is None:
            self.dm = DataModel(data, filename)
        else:
            self.dm = dm
        self.stdcl = {"cols": [pr2cl(1.0/data.nbCols(0)),pr2cl(1.0/data.nbCols(1))], "row": pr2cl(1.0/data.nbRows()), "FBp": 1}
        self.reds = {}
        self.crid = 0
        self.subs = {(): {"supp": set(range(data.nbRows())), "lits": [{},{}]}}

    def fillCopy(self, data, reds=[]):
        tmp = RedModel(data, self.dm)
        for red in reds:
            top = self.getTopDeltaRed(red, data)
            if top[0] < 0:
                tmp.addRed(red, data, top[1])
        return tmp
    
    def getReds(self):
        return [self.reds[i] for i in sorted(self.reds.keys())]

    def __str__(self):
        st = ("-- RedModel (x%d)" % len(self.reds))
        for sbi, sb in self.subs.items():
            st += ("\n* part %s, supp=%d" % ("".join([str(s) for s in sbi]), len(sb["supp"])))
            for side in [0,1]:
                for ci, lit in sb["lits"][side].items(): 
                    st += ("\n\t%s" % lit)
        return st
                     
    def addSubLits(self, red, lits, supp, data, sideAdd=None, rid=-1):
        nlits = [{},{}]
        for side in [0,1]:
            if sideAdd is None or sideAdd == side:            
                for lit in red.invLiteralsSide(side):
                    if lit.colId() in lits[side]:
                        nlits[side][lit.colId()] = lits[side][lit.colId()].addCopy(lit, supp, data, rid)
                    else:
                        nlits[side][lit.colId()] = LitFactory.getLit(side, lit.colId(), data, supp, self.dm.getD(side, lit.colId(), "Full"), lit, rid)
                    
            for li, l in lits[side].items():
                if li not in nlits[side]:
                    nlits[side][li] = l.shrinkCopy(supp)
        return nlits

    def removeSubLits(self, rid, lits, supp, data):
        nlits = [{},{}]
        for side in [0,1]:
            for li, l in lits[side].items():
                if l.hasRid(rid):
                    nlits[side][li] = l.removeCopy(rid, supp, self.dm.getD(side, li, "Full"), data)
                else:
                    nlits[side][li] = l.copy()
        return nlits

    def shrinkSubLits(self, lits, supp, suppO):
        if len(suppO) == 0:
            return lits
        else:
            tsp = supp - suppO
            nlits = [{},{}]
            for side in [0,1]:
                for li, lit in lits[side].items():
                    nlits[side][li] = lit.shrinkCopy(tsp)
            return nlits
        
    def addRed(self, red, data, sideAdd=None):
        suppn = red.getSuppI()
        tmp_subs = {}
        rid = self.crid
        self.crid += 1
        for sbi, sb in self.subs.items():
            suppt = sb["supp"] & suppn
            if len(suppt) > 0:
                tmp_subs[sbi+tuple([1])] = {"supp":  set(suppt), "lits": self.addSubLits(red, sb["lits"], suppt, data, sideAdd, rid)}
            if len(sb["supp"] - suppt) > 0:
                tmp_subs[sbi+tuple([0])] = {"supp":  set(sb["supp"] - suppt), "lits": self.shrinkSubLits(sb["lits"], sb["supp"], suppt)}
        self.subs = tmp_subs
        self.reds[rid] = (sideAdd, red)

    def removeRed(self, rid, data):
        tmp_subs = {}
        for sbi, sb in self.subs.items():
            supp = set(sb["supp"])
            tmp_subs[sbi] = {"supp":  supp, "lits": self.removeSubLits(rid, sb["lits"], supp, data)}
        self.subs = tmp_subs
        del self.reds[rid]

    def deltaDLRed(self, red, data):
        suppn = red.getSuppI()
        cFallB = [0,0]
        totS = [0,0]
        for sbi, sb in self.subs.items():
            suppt = sb["supp"] & suppn
            if len(suppt) > 0:
                for side in [0, 1]:
                    for lit in red.invLiteralsSide(side):

                        try:
                            vals = data.cols[side][lit.colId()].getVector()
                        except AttributeError:
                            pdb.set_trace()
                            print lit
                        if lit.colId() in sb["lits"][side]:
                            lt = sb["lits"][side][lit.colId()].addCopy(lit, suppt, data, -1)
                            lC = sb["lits"][side][lit.colId()]
                            sI = lt.getSupp()
                            sO = list(suppt & (lC.getSupp() - sI))
                            sI = list(sI)
                            lB = self.dm.getColD(side, lit.colId())
                            nFB = len(sO)
                        else:
                            lt = LitFactory.getLit(side, lit.colId(), data, suppt, self.dm.getD(side, lit.colId(), "Full"), lit, -1)
                            sI = list(lt.getSupp())
                            sO = list([])
                            lC = self.dm.getColD(side, lit.colId())
                            lB = lC
                            nFB = len(suppt) - len(sI)

                        cFallB[side] += nFB
                        try:
                            totS[side] += sum([pr2cl(pc/pn) for (pn,pc) in \
                                               zip(lt.getPrs(vals, sI), lC.getPrs(vals, sI))])
                        except ZeroDivisionError:
                            pdb.set_trace()
                            lt.getPrs(vals, sI)

                        if len(sO) > 0:
                            totS[side] += sum([pr2cl(pc/pn) for (pc,pn) in \
                                               zip(lC.getPrs(vals, sO), lB.getPrs(vals, sO))])

        return totS, cFallB

    def checkDelDLRid(self, rid, data):
        sideAdd, red = self.reds[rid]
        if sideAdd is None:
            sides = [0,1]
        else:
            sides = [sideAdd]
        cFallB = [0,0]
        totS = [0,0]
        for sbi, sb in self.subs.items():
            suppt = set(sb["supp"])
            for side in sides:
                for lit in red.invLiteralsSide(side):                 
                    if lit.colId() in sb["lits"][side] and sb["lits"][side][lit.colId()].hasRid(rid):
                        vals = data.cols[side][lit.colId()].getVector()

                        lt = sb["lits"][side][lit.colId()].removeCopy(rid, suppt, self.dm.getD(side, lit.colId(), "Full"), data)
                        lC = sb["lits"][side][lit.colId()]
                        sI = lC.getSupp()
                        sO = list(suppt & (lt.getSupp() - sI))
                        sI = list(sI)
                        lB = self.dm.getColD(side, lit.colId())
                        nFB = len(sO)

                        cFallB[side] += nFB
                        totS[side] += sum([pr2cl(pc/pn) for (pn,pc) in \
                                           zip(lt.getPrs(vals, sI), lC.getPrs(vals, sI))])

                        if len(sO) > 0:
                            totS[side] += sum([pr2cl(pc/pn) for (pc,pn) in \
                                               zip(lB.getPrs(vals, sO), lt.getPrs(vals, sO))])

        tot = 0
        for side in [0,1]:
            ### LENGTH OF QUERY DESCRIPTION, BOTH SIDES
            for lit in red.invLiteralsSide(side):
                tot -= self.stdcl["cols"][side]+2
                tot -= self.dm.getColD(side, lit.colId(), "Full").getLL(lit)
        for side in sides:
            ### LENGTH OF SUPPORT DESCRIPTION, OPPOSITE SIDE
            tot -= pr2cl(1.0/len(red.supp(1-side)))*(len(red.supp(1-side))-red.getLenI())
            ### LENGTH OF DATA
            tot -= totS[side] + self.stdcl["FBp"]*cFallB[side]
        return tot

    def checkClean(self, data):
        popids = []
        for rid in sorted(self.reds.keys())[:-1]:
        #for rid in sorted(self.reds.keys()):
            if self.checkDelDLRid(rid, data) < 0:
                popids.append(rid)
        return popids

    def cleanUp(self, data):
        popids = self.checkClean(data)
        for rid in popids:
            self.removeRed(rid, data)
        return popids
    
    def getQLRed(self, red):
        ql = [0,0]
        for side in [0,1]:
            for lit in red.invLiteralsSide(side):
                ql[side] += self.stdcl["cols"][side]+2
                ql[side] += self.dm.getColD(side, lit.colId(), "Full").getLL(lit)
        return ql

    def getSLRed(self, red):
        lL = [len(red.supp(0)), len(red.supp(1)), red.getLenI()]
        return [pr2cl(1.0/lL[0])*(lL[0]-lL[2]), pr2cl(1.0/lL[1])*(lL[1]-lL[2])]


    def getDeltaRed(self, red, data):
        totDelta, nFB = self.deltaDLRed(red, data)
        ql = self.getQLRed(red)
        sl = self.getSLRed(red)
        tot = []
        for side in [0,1]:
            tot.append(-totDelta[side] + self.stdcl["FBp"]*nFB[side] + sl[1-side])
        tot.append(sum(ql))
        return tot

    def getDeltaRed(self, red, data):
        totDelta, nFB = self.deltaDLRed(red, data)
        ql = self.getQLRed(red)
        sl = self.getSLRed(red)
        tot = []
        for side in [0,1]:
            tot.append(-totDelta[side] + self.stdcl["FBp"]*nFB[side] + sl[1-side])
        tot.append(sum(ql))
        return tot

    def getTopDeltaRed(self, red, data, tcs=None):
        scs = self.getDeltaRed(red, data)
        best = (float("Inf"), None)
        confs = {None:(0,1,2), 0:(0,2), 1:(1,2)}
        if tcs is None:
            tcs = confs.keys()

        for code in tcs:
            sc = sum([scs[si] for si in confs[code]])
            if sc < best[0]:
                best = (sc, code)
        return best

    def getDL(self, data, sbs=None):
        ticE = datetime.datetime.now()
        cFallB = [0,0]
        totS = [0,0]
        if sbs is None:
            sbs = self.subs
        for side in [0, 1]:
            for col in data.cols[side]:
                ci = col.getId()
                vals = col.getVector()
                uncovered = set(range(data.nbRows()))

                for sbi, sb in sbs.items():
                    if ci in sb["lits"][side]:
                        sS = sb["lits"][side][ci].getSupp()
                        cFallB[side] += len(sb["lits"][side][ci].getFallback())
                        totS[side] += sb["lits"][side][ci].getClsSum(vals, sS)
                        uncovered -= sS

                totS[side] += self.dm.getColD(side, ci).getClsSum(vals, uncovered)
        return totS, cFallB

    def getEncodedLength(self, data):
        totDL, nFB = self.getDL(data)
        sl, ql = [[0,0], [0,0]]
        for sideAdd, red in self.reds.values():
            tq = self.getQLRed(red)
            ts = self.getSLRed(red)
            for side in [0,1]:
                ql[side] += tq[side]
                if sideAdd is None or sideAdd == 1-side:
                    sl[side] += ts[side]
        tot = []
        for side in [0,1]:
            tot.append(totDL[side] + self.stdcl["FBp"]*nFB[side] + sl[1-side])
        tot.append(sum(ql))
        return tot

    def filterReds(self, reds, data, clean=True, logger=None):
        while len(reds) > 0:
            keep = []
            best = (0, None, None)
            for ri, red in enumerate(reds):
                top = self.getTopDeltaRed(red, data)
                if top[0] < best[0]:
                    best = (top[0], ri, top[1])
                elif top[0] < 0:
                    keep.append(ri)
            if best[2] is not None:
                if logger is not None:
                    logger.printL(2, "Adding %f\t%s\t%s..." % (best[0], reds[best[1]], reds[best[1]].dispQueries()), "log")
                self.addRed(reds[best[1]], data, best[2])
                if clean:
                    popids = self.cleanUp(data)
                    if logger is not None and len(popids) > 0:
                        logger.printL(2, "Cleaned up %d..." % len(popids), "log")
            reds = [reds[i] for i in keep]
        return reds

class DataModel:
    SIDE_DIFF = []
    def fromPicDM(self, filename):
        fp = open(filename)
        self.details, self.colsG, self.mapG = pickle.load(fp)
        fp.close()

    def toPicDM(self, filename):
        fp = open(filename, "w")
        pickle.dump((self.details, self.colsG, self.mapG), fp)
        fp.close()


    def __init__(self,data, filename=None):
        if filename is not None:
            self.fromPicDM(filename)
            return
        
        self.details = [{},{}]
        self.colsG = [[],[]]
        self.mapG = {}
        for side in [0, 1]:
            self.colsG[side].append({"basis": data.cols[side][0].getId(), "cols": []})
            for col in data.cols[side]:
                d = False
                ci = col.getId()
                self.details[side][(ci, "Full")] = ColFactory.getCol(side, ci, data, "Full")
                if len(self.colsG[side][-1]["cols"]) > 0 and side in DataModel.SIDE_DIFF:
                    self.details[side][(ci, "Diff")] = ColFactory.getCol(side, ci, data, "Diff", details={"parent": ci-1})
                    if self.details[side][(ci, "Full")][1] > self.details[side][(ci, "Diff")][1]:
                        d = True

                if not d: ## end of group, determine basis and update info
                    if len(self.colsG[side][-1]["cols"]) > 0:
                        self.colsG[side][-1]["basis"] = min(self.colsG[side][-1]["cols"], key=lambda x: self.details[side][(x, "Full")][1])
                        for i in range(self.colsG[side][-1]["cols"][0], self.colsG[side][-1]["basis"]):
                            self.details[side][(i, "Diff")] = self.details[side][(i+1, "Diff")]
                            self.details[side][(i, "Diff")][0].flip(data)
                            
                    self.colsG[side].append({"basis": ci, "cols": []})
                self.colsG[side][-1]["cols"].append(ci)
                self.mapG[(side, ci)] = len(self.colsG[side])-1
        
    def totDL(self):
        tot = 0
        for side in [0,1]:
            for g in self.colsG[side]:
                for c in g["cols"]:
                    if c == g["basis"]:
                        tot += self.details[side][(c, "Full")][1]
                    else:
                        tot += self.details[side][(c, "Diff")][1]
        return tot

    def getColD(self, side, ci, typeC=None):
        g = self.mapG[(side, ci)]
        if typeC is None:
            if self.colsG[side][g]["basis"] == ci:
                typeC = "Full"
            else:
                typeC = "Diff"
        return self.details[side][(ci, typeC)][0]

    def getD(self, side, ci, typeC=None):
        return self.getColD(side, ci, typeC).getD()

