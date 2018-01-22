class WorkInactive:

    def __init__(self):
        self.work_server = (None, None, None)
        self.workers = {}
        self.off = {}
        self.retired = {}

#### DUMMY METHODS START, inactive
    def __trunc__(self):
            return 100000

    def isActive(self):
        return False

    def getParametersD(self):
        return {"workserver_ip": ""}

    def getDetailedInfos(self):
        return "KO"
    def infoStr(self):
        return "Inactive"
    
    def checkResults(self, parent):
        pass
    def getOutQueue(self):
        return None
    def sendMessage(self):
        pass
    def layOff(self, wid):
        pass
    def closeDown(self, parent):
        pass
    def closeDown(self, parent):
        pass
    def addWorker(self, wtype, boss, more=None, details={}):
        pass
#### DUMMY METHODS END

#### SHARED METHODS START
    def getParameters(self):
        return self.work_server

    def getWorkEstimate(self):
        work_estimate = 0
        work_progress = 0
        for worker in self.workers.values():
            work_estimate += worker["work_estimate"]
            work_progress += worker["work_progress"]
        ### progress should not go over estimate, but well...
        work_progress = min(work_progress, work_estimate)
        return work_estimate, work_progress

    def nbWorkers(self):
        return len(self.workers)

    def nbWorking(self):
        return len(self.workers)+len(self.off)

    def findWid(self, fields):
        for wid, worker in sorted(self.workers.items()):
            found = True
            for f,v in fields:
                found &= (worker.get(f, None) == v)
            if found:
                return wid
        return None

    def getWorkersDetails(self):
        details = []
        for wid, worker in sorted(self.workers.items()):
            details.append({"wid": wid, "wtyp": worker["wtyp"]})
        return details

    def handlePieceResult(self, note, updates, parent):
        if note["type_message"] in self.type_messages:
            if note["type_message"] == "result":
                self.sendResult(note["source"], note["message"], updates, parent)
            else:
                method = eval(self.type_messages[note["type_message"]])
                if callable(method):
                    method(note["source"], note["message"], updates)

    def updateLog(self, source, message, updates):
        text = "%s" % message
        header = "@%s:\t" % source
        text = text.replace("\n", "\n"+header)
        if "log" not in updates:
            updates["log"] = ""
        updates["log"] += header+text+"\n"

    def updateError(self, source, message, updates):
        updates["error"] = "@%s:%s" % (source, message) 

    def updateStatus(self, source, message, updates):
        updates["status"] = "@%s:%s" % (source, message) 

    def updateProgress(self, source, message, updates):
        if source in self.workers:
            if message is None:
                self.retire(source)
                updates["menu"] = True
            elif len(message) > 1:
                self.workers[source]["work_progress"] = message[1]
                self.workers[source]["work_estimate"] = message[0]
            updates["progress"] = True
        elif source in self.off and message is None:
            self.retire(source)
            updates["menu"] = True
            updates["progress"] = True
            
    def sendResult(self, source, message, updates, parent):
        if source not in self.workers:
            return
        
        worker_info = self.workers[source]
        if worker_info["wtyp"] in ["expander", "miner"] and  worker_info["batch_type"] in message:
            tap = message[worker_info["batch_type"]]
            nb_tap = len(tap)
            if nb_tap > worker_info["results_track"]:
                tmp = []
                for red in tap[worker_info["results_track"]:nb_tap]:
                    redc = red.copy()
                    #### TRACKING HERE
                    redc.track.insert(0, (source, "W"))
                    tmp.append(redc)
                worker_info["results_track"] = nb_tap
                if parent is None:
                    print "Ready reds [%s] %s %s" % ((source, worker_info["wtyp"]), tmp, worker_info["results_tab"])
                else:
                    parent.readyReds((source, worker_info["wtyp"]), tmp, worker_info["results_tab"])
        elif worker_info["wtyp"] in ["projector"]:
            if parent is None:
                print "Ready proj %s %s %s" % ((source, worker_info["wtyp"]), worker_info["vid"], message)
            else:
                parent.readyProj((source, worker_info["wtyp"]), worker_info["vid"], message)
#### SHARED METHODS END
