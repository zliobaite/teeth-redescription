from classBasisView import BasisView

import pdb


class LView(BasisView):

    
    TID = "L"
    SDESC = "LViz"
    ordN = 0
    title_str = "List View"
    geo = False
    typesI = "r"

    
    @classmethod
    def suitableView(tcl, geo=False, what=None, tabT=None):
        return tabT is None or tabT in tcl.typesI

    def __init__(self, parent, vid, more=None):
        self.initVars(parent, vid, more)
        self.reds = {}
        self.srids = []
        self.initView()
        
    def getReds(self):
        ### the actual queries, not copies, to test, etc. not for modifications
        return self.reds

    def refresh(self):
        self.autoShowSplitsBoxes()
        self.updateMap()
        if self.isIntab():
            self._SetSize()

    def setCurrent(self, reds_map):
        self.reds = dict(reds_map)
        self.srids = [rid for (rid, red) in reds_map]
        pass
     
