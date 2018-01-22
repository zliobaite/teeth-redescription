import re, string, itertools, os.path
from classRedescription import  Redescription
from classQuery import  Query

import pdb

### Popping out from the last
def fifo_sort(pairs_store, pairs_details, drop_set=set()):
    return sorted(drop_set.symmetric_difference(pairs_store.keys()), reverse=True)

def filo_sort(pairs_store, pairs_details, drop_set=set()):
    return sorted(drop_set.symmetric_difference(pairs_store.keys()))

def overall_sort(pairs_store, pairs_details, drop_set=set()):
    return sorted(drop_set.symmetric_difference(pairs_store.keys()), key=lambda x: pairs_details[x].get("score", -1))

def alternate_sort(pairs_store, pairs_details, drop_set=set()):
    best_sides = [{}, {}]
    for k in pairs_store.keys():
        for side in [0,1]:
            col = pairs_details[k].get(side, -1)
            if col >= 0:
                if col in best_sides[side]:
                    best_sides[side][col].append(k)
                else:
                    best_sides[side][col] = [k]

    for side in [0,1]:
        for col in best_sides[side]:
            best_sides[side][col].sort(key=lambda x: pairs_details[x].get("score", -1), reverse=True)
        for c, vs in best_sides[side].items():
            for pp, v in enumerate(vs):
                pairs_details[v]["rank_%d"%side] = pp
    ord_ids = sorted(drop_set.symmetric_difference(pairs_store.keys()), key=lambda x: pairs_details[x].get("score")-max(pairs_details[x].get("rank_0"), pairs_details[x].get("rank_1")))
    return ord_ids

SORT_METHODS= {"overall": overall_sort,
               "alternate": alternate_sort,
               "fifo": fifo_sort,
               "filo": filo_sort}
DEFAULT_METHOD = overall_sort

class InitialPairs(object):

    def __init__(self, sort_meth="overall", max_out=-1, save_filename=None):
        self.max_out = max_out
        self.list_out = []
        self.drop_set = set() 
        self.pairs_store = {}
        self.pairs_details = {}
        self.sorted_ids = None
        self.next_id = 0
        self.setExploreList()
        self.sort_meth = SORT_METHODS.get(sort_meth, DEFAULT_METHOD)
        self.setSaveFilename(save_filename)

    def setSaveFilename(self, save_filename):
        self.save_filename = None
        self.saved = True
        if type(save_filename) is str and len(save_filename) > 0:
            self.save_filename = save_filename 
            self.saved = False
            
    def getSaveFilename(self):
        return self.save_filename

    def saveToFile(self):
        if self.save_filename is not None and not self.saved:
            try:
                with open(self.save_filename, "w") as f:
                    for pi, p in self.pairs_store.items():
                        f.write("%s\t%s\n" % (p[0], p[1]))
                    done =  self.getExploredDone()
                    if done is None:
                        self.saved = True
                    else:
                        f.write("DONE: %s\n" % " ".join(["%d-%d" % d for d in done]))
                return True
            except IOError:
                pass
        return False

    def loadFromFile(self):
        loaded = False
        done = set()
        if self.save_filename is not None and os.path.isfile(self.save_filename):
            with open(self.save_filename) as f:
                done = None
                for line in f:
                    if re.match("DONE:", line):
                        done = set([tuple(map(int, d.split("-"))) for d in line.strip().split(" ")[1:]])
                    else:
                        parts = line.strip().split("\t")
                        if len(parts) == 2:
                            q0 = Query.parse(parts[0])
                            q1 = Query.parse(parts[1])
                            if len(q0) == 1 and len(q1) == 1:
                                l0 = q0.getBukElemAt([0])
                                l1 = q1.getBukElemAt([0])                            
                                self.add(l0, l1, {"score": -1, 0: l0.colId(), 1: l1.colId()})
            loaded = True
        return loaded, done
    
    def reset(self):
        self.list_out = []
        self.drop_set = set()
        self.pairs_store.clear()
        self.pairs_details.clear()
        self.sorted_ids = None
        self.setExploreList()
        self.saved = False

    def __len__(self):
        return len(self.pairs_store)

    def setMaxOut(self, n):
        self.max_out = n

    def getNbOut(self):
        return len(self.list_out)

    def getMaxOut(self):
        return self.max_out

    def getRemainOut(self):
        if self.max_out == -1:
            return self.max_out
        else:
            return self.max_out - self.getNbOut()
        
    def __str__(self):
        return "Initial Pairs %d" % len(self.pairs_store)

    def add(self, literalL, literalR, details=None):
        self.saved = False
        self.pairs_store[self.next_id] = (literalL, literalR)
        if details is not None:
            self.pairs_details[self.next_id] = details
        else:
            self.pairs_details[self.next_id] = self.next_id
        self.next_id += 1
        self.sorted_ids = None

    def _sort(self):
        if self.sorted_ids is None:
            self.sorted_ids = self.sort_meth(self.pairs_store, self.pairs_details, self.drop_set)
        
    def pop(self, cond=None):
        if len(self.pairs_store) > 0 and not self.exhausted():
            self._sort()
            if len(self.sorted_ids):
                nid = self.sorted_ids.pop()
                tt = self.pairs_store[nid]
                dt = self.pairs_details[nid]
                self.drop_set.add(nid)
                if cond is not None:
                    while not cond(tt) and len(self.pairs_store) > 0:
                        nid = self.sorted_ids.pop()
                        tt = self.pairs_store[nid]
                        dt = self.pairs_details[nid]
                        self.drop_set.add(nid)
                    if not cond(tt) and len(self.pairs_store) == 0:
                        return
                self.list_out.append(nid)
                return tt

    def get(self, data, cond=None):
        pair = self.pop(cond)
        if pair is not None:
            return Redescription.fromInitialPair(pair, data)

    def exhausted(self):
        return (self.max_out > -1) and (self.getNbOut()  >= self.max_out)

    def setExploreList(self, explore_list=[], pointer=-1, batch_size=0, done=set()):
        if done is None:
            done = set()
        self.explore_pairs = {"list": explore_list, "pointer": pointer, "batch_size": batch_size, "done": done}
    def addExploredPair(self, pair):
        if self.explore_pairs["done"] is not None:
            self.explore_pairs["done"].add(pair)
    def getExploreList(self):
        return self.explore_pairs["list"]
    def getExploredDone(self):
        return self.explore_pairs["done"]
    def setExploredDone(self):
        self.explore_pairs["done"] = None
        self.explore_pairs["pointer"] = -1
    def getExplorePointer(self):
        return self.explore_pairs["pointer"]
    def setExplorePointer(self, pointer=-1):
        self.explore_pairs["pointer"] = pointer
    def incrementExplorePointer(self):
        self.explore_pairs["pointer"] += 1
    def getExploreNextBatch(self, pointer=None, bsize=None):
        if pointer is None:
            pointer = self.explore_pairs["pointer"]
        if bsize is None:
            bsize = self.explore_pairs["batch_size"]
        return self.explore_pairs["list"][pointer*bsize:(pointer+1)*bsize]
