import multiprocessing, time, socket, uuid, re
from multiprocessing.managers import SyncManager
import Queue

from classWorkInactive import WorkInactive

import pdb

IP = '127.0.0.1'
PORTNUM = 55444
AUTHKEY = 'sesame'

def make_client_manager(ip, port, authkey):
    class ServerQueueManager(SyncManager):
        pass

    ServerQueueManager.register('get_job_q')
    ServerQueueManager.register('get_ids_d')

    manager = ServerQueueManager(address=(ip, port), authkey=authkey)
    manager.connect()
    return manager

def make_hc_manager(ip, port, authkey):

    class HCQueueManager(SyncManager):
        pass

    HCQueueManager.register('get_job_q', callable=lambda: job_q)
    HCQueueManager.register('get_result_q', callable=lambda: result_q)

    manager = HCQueueManager(address=(ip, port), authkey=authkey)
    manager.connect()
    return manager

class WorkClient(WorkInactive):

    type_messages = {'log': "self.updateLog", 'result': None, 'progress': "self.updateProgress",
                     'status': "self.updateStatus", 'error': "self.updateError"}

    def __init__(self, ip=IP, portnum=PORTNUM, authkey=AUTHKEY):
        self.hid = None
        self.work_server = (ip, portnum, authkey)
        self.shared_job_q = None
        self.ids_q = None
        self.shared_result_q = None
        self.next_workerid = 0
        self.workers = {}
        self.off = {}
        self.retired = {}

    def isActive(self):
        return True

    def getParametersD(self):
        return {"workserver_ip": self.work_server[0],
                "workserver_port": self.work_server[1],
                "workserver_authkey": self.work_server[2]}
    
    def __del__(self):
        if self.hid is not None:
            # print "delete"
            self.shared_job_q.put({"hid": self.hid, "task": "layoff"})

    def testConnect(self):
        try:
            manager = make_client_manager(self.work_server[0], self.work_server[1], self.work_server[2])
            return True
        except socket.error:
            return False

    def getDetailedInfos(self):
        counter = 10
        info = "KO"
        if self.hid is None:
            try:
                manager = make_client_manager(self.work_server[0], self.work_server[1], self.work_server[2])
            except (socket.error, IOError, EOFError):
                self.onServerDeath()
                info =  "KO\tMaybe the server died, in any case, it did not respond..."
                counter = 0
            else:
                self.shared_job_q = manager.get_job_q()
                self.ids_d = manager.get_ids_d()
        uid = uuid.uuid4()
        if counter > 0:
            try:
                self.shared_job_q.put({"task": "info", "cid": uid})
            except (socket.error, IOError, EOFError):
                self.onServerDeath()
                info =  "KO\tMaybe the server died, in any case, it did not respond..."
                counter = 0
            
        while counter > 0 and not self.ids_d.has_key(uid):
            time.sleep(1)
            counter -= 1
        if counter > 0 and self.ids_d.has_key(uid):
            tmp = self.ids_d.pop(uid)
            parts = tmp.strip().split()
            if len(parts) == 0:
                info = "OK\tDoes not have any clients."
            else:
                tasks = 0
                pending = 0
                for p in parts:
                    tmp = re.match("^(?P<cid>[a-zA-Z0-9]*):(?P<run>[0-9]*)\+(?P<pend>[0-9]*)$", p)
                    if tmp is not None:
                        tasks += int(tmp.group("run"))
                        pending += int(tmp.group("pend")) 
                if len(parts) == 1:
                    info = "OK\tHas one client, in total %d tasks, of which %d currently running." % (tasks+pending, tasks)
                else:
                    info =  "OK\tHas %d clients, in total %d tasks, of which %d currently running." % (len(parts), tasks+pending, tasks)
        return info

    def infoStr(self):
        return "Server %s:%d" % (self.work_server[0], self.work_server[1])

    def resetHS(self, ip=None, numport=None, authkey=None):
        if self.hid is not None and self.nbWorkers() == 0:
            ## check results before calling this
            self.shared_job_q.put({"hid": self.hid, "task": "layoff"})
            self.shared_job_q = None
            self.shared_result_q= None
            self.hid = None
            
        if self.hid is None:
            if ip is not None:
                self.work_server = (ip, nunmport, authkey)
            manager = make_client_manager(self.work_server[0], self.work_server[1], self.work_server[2])
            self.shared_job_q = manager.get_job_q()
            self.ids_d = manager.get_ids_d()
            uid = uuid.uuid4()
            self.shared_job_q.put({"task": "startup", "cid": uid})
            counter = 10
            while not self.ids_d.has_key(uid) and counter > 0:
                time.sleep(1)
                counter -= 1
            if self.ids_d.has_key(uid):
                self.hid = self.ids_d.pop(uid)
                hc_manager = make_hc_manager(self.work_server[0], self.hid, self.work_server[2])
                self.shared_result_q = hc_manager.get_result_q()
                return self.hid
                
    def getOutQueue(self):
        return None
    def getResultsQueue(self):
        return self.shared_result_q
    def getJobsQueue(self):
        return self.shared_job_q

    def addWorker(self, wtype, boss, more=None, details={}):
        if self.hid is None:
            self.resetHS()

        if self.hid is not None:
            self.next_workerid += 1
            self.workers[self.next_workerid] = {"wtyp": wtype,
                                                "work_progress":0,
                                                "work_estimate":0}
            self.workers[self.next_workerid].update(details)
            job = {"hid": self.hid, "wid":self.next_workerid, "task": wtype, "more": more, "data": boss.getData(), "preferences": boss.getPreferences()}
            try:
                self.getJobsQueue().put(job)
            except (socket.error, IOError, EOFError):
                self.onServerDeath(boss)
 
    def cleanUpResults(self):
        if self.getResultsQueue() is None:
            return
        while self.getResultsQueue() is not None:
            try:
                # self.getResultsQueue().get_nowait()
                self.getResultsQueue().get(False, 1)
            except Queue.Empty:
                break
            except (socket.error, IOError, EOFError):
                self.onServerDeath()

    def closeDown(self, parent):
        for wid in self.workers.keys():
            self.layOff(wid)
        self.checkResults(parent)
        self.cleanUpResults()

    def layOff(self, wid):
        if self.getJobsQueue() is None:
            return
        if wid is not None and wid in self.workers:
            job = {"hid": self.hid, "wid": wid, "task": "layoff"}
            self.getJobsQueue().put(job)
            # self.off[wid] = self.workers.pop(wid)
            return wid
        return None

    def retire(self, wid):
        if wid in self.off:
            self.retired[wid] = self.off.pop(wid)
        elif wid in self.workers and self.getJobsQueue() is not None:
            job = {"hid": self.hid, "wid": wid, "task": "retire"}
            self.getJobsQueue().put(job)            
            self.retired[wid] = self.workers.pop(wid)
        return None

    def monitorResults(self, parent):
        updates = {}
        if self.getJobsQueue() is not None:
            while self.nbWorking() > 0:
                try:
                    piece_result = self.getResultsQueue().get(False, 1)
                    if piece_result is not None:
                        self.handlePieceResult(piece_result, updates, parent)
                        if "status"in updates:
                            print updates["status"]
                except (socket.error, IOError, EOFError):
                    self.onServerDeath(parent)

        return updates

    def checkResults(self, parent):
        updates = {}
        if self.getJobsQueue() is not None:
            while self.nbWorking() > 0:
                try:
                    # piece_result = self.getResultsQueue().get_nowait()
                    piece_result = self.getResultsQueue().get(False, 1)
                    if piece_result is not None:
                        self.handlePieceResult(piece_result, updates, parent)
                except Queue.Empty:
                    break
                except (IOError, EOFError, socket.error):
                    self.onServerDeath(updates, parent)
        return updates

    def finishingWki(self, wki, updates=None, parent=None):
        if wki in self.workers:
            if updates is not None:
                if self.workers[wki]["wtyp"] in ["projector"]:
                    parent.readyProj(self.workers[wki]["vid"], None)
            self.retired[wki] = self.workers.pop(wki)

    def onServerDeath(self, updates=None, parent=None):
        wkis = self.workers.keys()
        for wki in wkis:
            self.finishingWki(wki, updates, parent)
        self.shared_job_q = None
        self.shared_result_q = None
        self.hid = None
        if updates is not None:
            self.updateStatus("WP", "Work server died!", updates)
            self.updateError("WP", "Work server died!", updates)
            updates["menu"] = True
            updates["progress"] = True
