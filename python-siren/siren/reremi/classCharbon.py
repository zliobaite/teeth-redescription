from classQuery import Literal
import pdb

class Charbon(object):
    name = "-"
    def getAlgoName(self):
        return self.name

    def __init__(self, constraints):
        ### For use with no missing values
        self.constraints = constraints



class CharbonGreedy(Charbon):

    name = "G"

    def isTreeBased(self):
        return False
    def handlesMiss(self):
        return False


class CharbonTree(Charbon):

    name = "T"
    def isTreeBased(self):
        return True
    def handlesMiss(self):
        return False

    ### def getTreeCandidates(self, side, data, red)

    def computeInitTerm(self, colL):
        tmp = [(Literal(False,t),v) for (t,v) in colL.getInitTerms(self.constraints.getCstr("min_itm_in"), self.constraints.getCstr("min_itm_out"))]
        # tmp = [(Literal(False,t),v) for (t,v) in colL.getInitTerms(self.constraints.getCstr("min_itm_in")/4., self.constraints.getCstr("min_itm_out")/4.)]
        # if len(tmp) > 0:
        #     pdb.set_trace()
        #     print colL.getId(), len(tmp), "\t", self.constraints.getCstr("min_itm_in")/4., self.constraints.getCstr("min_itm_out")/4.
        return tmp
