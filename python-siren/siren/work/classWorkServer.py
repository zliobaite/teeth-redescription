import multiprocessing, time, sys, os
import getopt
from multiprocessing.managers import SyncManager
from ..reremi.classMiner import instMiner
from ..reremi.toolLog import Log

import pdb

PORTNUM = 55444
AUTHKEY = 'sesame'
MAXK = 4

def sendMessage(output, message, type_message, source):
    output.put({"message": message, "type_message": type_message, "source": source})


class WorkerProcess(multiprocessing.Process):
    def __init__(self, pid, data, preferences, queue_in, result_q, cust_params={}):
        multiprocessing.Process.__init__(self)
        logger = Log({"*": preferences.get("verbosity", 0), "error":1, "progress":2, "result":1}, result_q, sendMessage)
        self.miner = instMiner(data, preferences, logger, pid, qin=queue_in, cust_params=cust_params)
        self.cust_params = cust_params
        self.start()

    def run(self):
        pass

class MinerProcess(WorkerProcess):
    def run(self):
        self.miner.full_run(self.cust_params)

class ExpanderProcess(WorkerProcess):
    def run(self):
        self.miner.part_run(self.cust_params)

class ProjectorProcess(multiprocessing.Process):
    def __init__(self, pid, data, preferences, queue_in, result_q, proj={}):
        multiprocessing.Process.__init__(self)
        self.id = pid
        self.logger = Log({"*": preferences.get("verbosity", 0), "error":1, "progress":2, "result":1}, result_q, sendMessage)
        if proj is not None:
            self.proj = proj
            self.start()

    def stop(self):
        self.proj.stop()
        self.logger.printL(1, self.proj, "result", self.id)
        self.logger.printL(1, None, "progress", self.id)
        self.terminate()

    def run(self):
        try:
            self.proj.do()
        except Exception as e:
            self.proj.clearCoords()
            self.logger.printL(1, "Projection Failed!\n[ %s ]" % e, "error", self.id)
        finally:
            self.logger.printL(1, self.proj, "result", self.id)
            self.logger.printL(1, None, "progress", self.id)
        
def make_server_manager(port, authkey):
    job_q = multiprocessing.Queue()
    ids_d = dict()
    
    class JobQueueManager(SyncManager):
        pass

    JobQueueManager.register('get_job_q', callable=lambda: job_q)
    JobQueueManager.register('get_ids_d', callable=lambda: ids_d)

    manager = JobQueueManager(address=("", port), authkey=authkey)
    manager.start()
    print 'Central server started at port %s' % port
    return manager

class WorkServer(object):

    def __init__(self, portnum=PORTNUM, authkey=AUTHKEY, max_k=MAXK):
        print "PID", os.getpid()
        self.manager = make_server_manager(portnum, authkey)
        self.shared_job_q = self.manager.get_job_q()
        self.shared_ids_d = self.manager.get_ids_d()
        self.authkey = authkey
        self.nextHandlerId = 0
        self.handlers = {}
        
#        try:
        if True:
            while True:
                ## read tasks from queue
                job = self.getJobsQueue().get()
                if type(job) is dict:
                    print "HANDLING", job["task"], job.get("hid"), job.get("wid")
                    if job.get("task") == "startup":
                        ## create new handler
                        self.nextHandlerId += 1
                        hid = portnum + self.nextHandlerId
                        self.handlers[hid] = WorkHandler(self, hid, self.authkey)
                        self.shared_ids_d.update({job.get("cid"): hid})
                        print "new HID %s -> %s" % (job.get("cid"), hid) 

                    if job.get("task") == "info":
                        ## create new handler
                        hid = portnum + self.nextHandlerId
                        self.shared_ids_d.update({job.get("cid"): self.getLoadStr()})
                        print "sent INFO %s" % job.get("cid") 

                    ## if retire: move from working to retired 
                    elif job.get("hid") in self.handlers:
                        self.handlers[job.get("hid")].handleJob(job)
        # except:
        #     print "Central stop..."
        #     return

    def getLoadStr(self):
        return " ".join([hd.getLoadStr() for (hdid, hd) in self.handlers.items()])
                        
    def __del__(self):
        hids = self.handlers.keys()
        for hid in hids:
            self.handlers[hid].shutDown()
        self.manager.shutdown()

    def unregister(self, hid):
        ### shutdown handler
        if hid in self.handlers:
            del self.handlers[hid]
        
    def getJobsQueue(self):
        return self.shared_job_q
    def getIdsDict(self):
        return self.shared_ids_d


def make_hs_manager(port, authkey):
    job_q = multiprocessing.Queue()
    result_q = multiprocessing.Queue()

    class HSQueueManager(SyncManager):
        pass

    HSQueueManager.register('get_job_q', callable=lambda: job_q)
    HSQueueManager.register('get_result_q', callable=lambda: result_q)

    manager = HSQueueManager(address=("", port), authkey=authkey)
    manager.start()
    print 'Work server started at port %s' % port
    return manager


class WorkHandler(object):

    type_workers = {"expander": {"launch": ExpanderProcess, "stop": "message"},
                    "miner": {"launch": MinerProcess, "stop": "message"},
                    "projector": {"launch": ProjectorProcess, "stop": "terminate"}}

    def __init__(self, parent_ws, portnum, authkey, max_k=MAXK):
        self.manager = make_hs_manager(portnum, authkey)
        self.shared_result_q = self.manager.get_result_q()
        self.parent = parent_ws
        self.id = portnum
        self.max_K = max_k
        self.pending = {}
        self.working = {}
        self.retired = {}

    def getResultsQueue(self):
        return self.shared_result_q

    def getLoadStr(self):
        return "%d:%d+%d" % (self.id, len(self.working), len(self.pending))


    def handleJob(self, job):
        print "HANDLING JOB", job.get("task")
        ### if acceptable task: launch work if there are free processes, else add job to pending 
        if job.get("task") in self.type_workers and job.get("wid") not in self.pending \
               and job.get("wid") not in self.working:
            if len(self.working) < self.max_K:
                tmp = self.launchJob(job)
                if tmp is not None:
                    self.working[job.get("wid")] = tmp
            else:
                self.pending[job.get("wid")] = job

        if job.get("task") == "retire" and job.get("wid") in self.working:
            self.retired[job.get("wid")] = self.working.pop(job.get("wid"))
            self.launchPending()

        ### if layoff: remove from pending or stop work in process
        if job.get("task") == "layoff":
            if job.get("wid") in self.pending:
                self.pending.pop("wid")
            elif job.get("wid") in self.working:
                self.stopJob(job.get("wid"))
                self.retired[job.get("wid")] = self.working.pop(job.get("wid"))
                self.launchPending()

        if job.get("task") == "shutdown":
            self.shutDown()

    def launchPending(self):
        ### if pending tasks launch oldest one
        while len(self.working) < self.max_K and len(self.pending) > 0:
            oldest_wid = min(self.pending.keys())
            tmp = self.launchJob(self.pending[oldest_wid])
            if tmp is not None:
                self.working[oldest_wid] = tmp 
            self.pending.pop(oldest_wid)

    def launchJob(self, job):
        if job.get("task") in self.type_workers:
            print "Launching job %d" % job["wid"]
            if self.type_workers[job.get("task")]["stop"] == "message":
                queue = multiprocessing.Queue()
            else:
                queue = None
            p = self.type_workers[job.get("task")]["launch"](job.get("wid"), job.get("data"), job.get("preferences"), queue, self.getResultsQueue(), job.get("more"))
            return {"process":p, "queue": queue}

    def stopJob(self, wid):
        if self.working[wid]["queue"] is not None:
            self.working[wid]["queue"].put({"message": "stop", "type_message": "progress", "source": "plant"})
        else:
            self.working[wid]["process"].stop()
            # self.working[wid]["process"].terminate()

    def shutDown(self):
        del self.pending
        del self.retired
        workers = self.working.keys()
        for wid in workers:
            self.stopJob(wid)
            self.working.pop(wid)
        time.sleep(20)
        del self.working
        self.manager.shutdown()
        self.parent.unregister(self.id)
        print "Worker server stoping..."
        sys.exit()

if __name__ == '__main__':
    args = {}
    if len(sys.argv) > 1:
        args = dict([(k.strip("-"), v) for (k,v) in getopt.getopt(sys.argv[1:], "", ["portnum=", "authkey=", "max_k=", "chroot=","setuid="])[0]])
    for k in ["portnum", "max_k", "setuid"]:
        if k in args:
            try:
                args[k] = int(args[k])
            except ValueError:
                del args[k]
    if "setuid" in args:
        os.setuid(args.pop("setuid"))
    if "chroot" in args:
        os.chroot(args.pop("chroot"))
    WorkServer(**args)





