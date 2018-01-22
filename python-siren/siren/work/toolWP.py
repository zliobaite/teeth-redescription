from classWorkInactive import WorkInactive
from classWorkLocal import WorkLocal
from classWorkClient import WorkClient
import pdb

class WorkPlant(object):

    def __init__(self):
        self.wp = None
        self.wp = self.setupWorkPlant()
        self.upcall = []

    def setUpCall(self, upcall):
        self.upcall = upcall
    def setWP(self,wp):
        self.wp = wp
        for upcall in self.upcall:
            upcall()
    def getWP(self):
        return self.wp

    def setupWorkPlant(self, ip=None, numport=None, authkey=None):
        if self.wp is None or (ip, numport, authkey) != self.wp.getParameters():
            # wp = WorkInactive()
            
            # if ip is None:
            #     return wp
            # elif ip == "local":

            if ip is not None and ip != "local":
                try:
                    wp = WorkClient(ip, numport, authkey)
                except Exception as e:
                    wp = WorkInactive()
                    raise e
            else:
                wp = WorkLocal()
            return wp
        else:
            return self.wp
 
# if __name__ == '__main__':
#     wp, msg, err = resetWorkPlant("127.0.0.1", 55444, "shufflin")
#     print msg
