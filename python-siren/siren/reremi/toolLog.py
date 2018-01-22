import sys
import pdb
import random
import datetime
import copy
        
class Log(object):
    def __init__(self, verbosity=1, output = '-', method_comm = None):
        self.tics = {None: datetime.datetime.now()}
        self.progress_ss = {"current": 0, "total": 0}
        self.bit = 1
        self.out = []
        self.oqu = []
        self.verbosity = -1
        self.addOut(verbosity, output, method_comm)

    #### FOR PICKLING !!
    def __getstate__(self):
        tmp = {}
        for k,v in self.__dict__.items():
            if k == 'out':
                tmp[k] = []
            else:
                tmp[k] = v
        return tmp

    ############ THE CLOCK PART
    def getTic(self, id, name=None):
        if name is None:
            return self.tics[None]
        elif (id, name) in self.tics:
            return self.tics[(id, name)]
        else:
            return None
        
    def setTic(self, id, name):
        self.tics[(id, name)] = datetime.datetime.now()
        return self.tics[(id, name)]

    def setTac(self, id, name=None):
        if name is None:
            return (self.tics[None], datetime.datetime.now())
        elif (id, name) in self.tics:
            return (self.tics.pop((id,name)), datetime.datetime.now())

    def getTac(self, id, name):
        if name is None:
            return (self.tics[None], datetime.datetime.now())
        elif (id, name) in self.tics:
            return (self.tics[(id,name)], datetime.datetime.now())

    def clockTic(self, id, name=None, details=None):
        tic = self.setTic(id,name)
        if name is None: name = "\t"
        mess = "Start %s\t((at %s))" % (name, tic)
        if details is not None:
            mess += ("\t%s" % details)
        self.printL(1, mess, "time", id)

    def clockTac(self, id, name=None, details=""):
        tic, tac = self.getTac(id,name)
        if name is None: name = "\t"
        mess = "End %s\t((at %s, elapsed %s))" % (name, tac, tac-tic)
        if details is not None:
            mess += ("\t%s" % details)
        self.printL(1, mess, "time", id)
    ####### END CLOCK
        
    ####### THE TRACKING PART
    def initProgressFull(self, constraints, souvenirs, explore_list=None, level=-1, id=None):
        if explore_list is not None:
            self.progress_ss["pairs_gen"] = sum([p[-1] for p in explore_list])
        else:
            self.progress_ss["pairs_gen"] = 0
        self.progress_ss["cand_var"] = 1
        self.progress_ss["cand_side"] = [souvenirs.nbCols(0)*self.progress_ss["cand_var"],
                                         souvenirs.nbCols(1)*self.progress_ss["cand_var"]]
        self.progress_ss["generation"] = constraints.getCstr("batch_cap")*sum(self.progress_ss["cand_side"])
        self.progress_ss["expansion"] = (constraints.getCstr("max_var", side=0)+constraints.getCstr("max_var", side=0)-2)*2*self.progress_ss["generation"]
        self.progress_ss["total"] = self.progress_ss["pairs_gen"] + constraints.getCstr("max_red")*self.progress_ss["expansion"]
        self.progress_ss["current"] = 0
        if level > -1:
            self.printL(level, self.getProgress(), 'progress', id)

    def initProgressPart(self, constraints, souvenirs, reds, level=-1, id=None):
        self.progress_ss["cand_var"] = 1
        self.progress_ss["cand_side"] = [souvenirs.nbCols(0)*self.progress_ss["cand_var"],
                                         souvenirs.nbCols(1)*self.progress_ss["cand_var"]]
        self.progress_ss["generation"] = constraints.getCstr("batch_cap")*sum(self.progress_ss["cand_side"])
        self.progress_ss["expansion"] = (constraints.getCstr("max_var", side=0)-min([constraints.getCstr("max_var", side=0)]+[len(r.queries[0]) for r in reds])+
                                         constraints.getCstr("max_var", side=1)-min([constraints.getCstr("max_var", side=1)]+[len(r.queries[1]) for r in reds]))*self.progress_ss["generation"]
        self.progress_ss["total"] = self.progress_ss["expansion"]
        self.progress_ss["current"] = 0
        if level > -1:
            self.printL(level, self.getProgress(), 'progress', id)

    def updateProgress(self, details=None, level=-1, id=None):
        if details is not None:
            if "pload" in details:
                self.progress_ss["current"] += details["pload"]
            elif len(details) == 1:
                if details["rcount"] > 0:
                    self.progress_ss["current"] += self.progress_ss["expansion"]

        if level > -1:
            self.printL(level, self.getProgress(), 'progress', id)

    def sendCompleted(self, id):
        self.printL(1, None, 'progress', id)

    def getProgress(self):
        return (self.progress_ss["total"], self.progress_ss["current"])
    ####### END TRACKING
    
    def disp(self):
        tmp = "LOGGER"
        for out in self.out:
            tmp += "\n\t* %s -> %s" % (out["verbosity"],  out["destination"])
        for out in self.oqu:
            tmp += "\n\t* %s -> %s" % (out["verbosity"],  out["destination"])
        return tmp
        
    def resetOut(self):
        self.out = []
        self.oqu = []
        self.verbosity = -1
        
    def addOut(self,  verbosity=1, output = '-', method_comm = None):
        # print "Adding output:\t", output, type(output), method_comm
        ### CHECK OUTPUT
        self.bit = 0
        if type(output) == str:
            if output in ['-', "stdout"]:
                tmp_dest = sys.stdout
            elif output == 'stderr':
                tmp_dest = sys.stderr
            else:
                try:
                    tmp_dest = open(output, 'w')
                except IOError:
                    return
        else:
            tmp_dest = output
            

        ### CHECK VERBOSITY
        if type(verbosity) == int:
            verbosity = {"*": verbosity, "progress":0, "result":0, "error":0} 
        
        if type(verbosity) == dict:
            if max(verbosity.values()) > self.verbosity:
                self.verbosity = max(verbosity.values())
        else:
            return

        ### OK ADD OUTPUT
        if output is not None and type(output) is not str:
             self.oqu.append({"verbosity": verbosity, "destination": tmp_dest, "method": method_comm})
        else:
            self.out.append({"verbosity": verbosity, "destination": tmp_dest, "method": method_comm})
        return len(self.out)+len(self.oqu)-1

    def usesOutMethods(self):
        for out in self.out+self.oqu:
            if out["method"] is not None:
                return True
        return False

    def printL(self, level, message, type_message="*", source=None):
        for out in self.out+self.oqu:
            if ( type_message in out["verbosity"].keys() and level <= out["verbosity"][type_message]) \
                   or  ( type_message not in out["verbosity"].keys() and "*" in out["verbosity"].keys() and level <= out["verbosity"]["*"]):
                
                if type(out["destination"]) == file:
                    if type_message == "*":
                        header = ""
                    else:
                        header = type_message
                    if source is None:
                        header += ""
                    else:
                        header += "@%s" % source
                    if len(header) > 0:
                        header = "[[%-10s]]\t" % header
                    out["destination"].write("%s%s\n" % (header, message))
                    out["destination"].flush()
                else:
                    # print "Log printing:\t", type_message, message, "\n\tFrom", source ," to ", out["destination"]
                    out["method"](out["destination"], message, type_message, source)
        
        
