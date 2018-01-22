import os.path
import collections
import sys
import re

import pdb

from ..reremi.classRedescription import Redescription, printTexRedList, printRedList, parseRedList
from ..reremi.classData import Data, DataError
from ..reremi.classQuery import Query
from ..reremi.toolICList import ICList
from ..reremi.toolICDict import ICDict
from ..reremi.toolLog import Log
from ..reremi.classBatch import Batch
from ..reremi.classPreferencesManager import PreferencesManager, PreferencesReader
from ..reremi import toolRead
from ..reremi.classPackage import Package, writePreferences, writeRedescriptions

#from findFiles import findFile

def findFile(fname, path=[]):
    """Finds file from path (always including the current working directory) and returns
    its path or 'None' if the file does not exist.
    If path is not given or an empty list, only checks if the file is present locally.

    On Windows, this also chagnges forward slashes to backward slashes in the path."""
    if os.path.exists(fname):
        return fname

    for p in path:
        testpath = os.path.join(os.path.normpath(p), fname)
        if os.path.exists(testpath):
            return testpath

    return None


class DataWrapper(object):
    """Contains all the data
    """


    def __init__(self, logger=None, package_filename = None, conf_defs=[]):
        """Inits the class. Either package_filename or the others should be given.
        """

        #### [[idi, 1] for idi in range(len(self.data))]
        if logger is None:
            self.logger = Log()
        else:
            self.logger = logger
        self.pm = PreferencesManager(conf_defs)
        self.data = None
        self.polys = None
        self.pdp = None
        self.resetRedescriptions()
        self.preferences = ICDict(self.pm.getDefaultTriplets())
        self.package = None
        self._isChanged = False
        self._isFromPackage = False

        # (possible) function pointers to tell we've started and stopped reading
        # If these are not None, they have to be triples (fnc, *args, **kwargs)
        # See: self.registerStartReadingFileCallback and self.registerStopReadingFileCallback
        self.startReadingFileCallback = None
        self.stopReadingFileCallback = None

        if package_filename is not None:
            self.openPackage(package_filename)
        
    def resetRedescriptions(self, reds=[]):
        self.reds = Batch(reds)
        self.rshowids = ICList(range(len(reds)), True)

    def getColNames(self):
        if self.data is not None:
            return self.data.getNames()
        return [[],[]]

    def dataHasMissing(self):
        if self.data is not None:
            return self.data.hasMissing()
        return False

    def getNbRows(self):
        if self.data is not None:
            return self.data.nbRows()
        return 0

    def getDataCols(self, side):
        if self.data is not None:
            return self.data.cols[side]
        return []

    def getDataRows(self):
        if self.data is not None:
            return self.data.getRows()
        return []

    def getData(self):
        return self.data

    def isGeospatial(self):
        if self.data is not None and self.data.isGeospatial():
            return True
        else:
            return False

    def getCoords(self):
        if self.data is not None and self.data.isGeospatial():
            return self.data.coords
        
    def getCoordsExtrema(self):
        if self.data is not None and self.data.isGeospatial():
            return self.data.getCoordsExtrema()
        return None

    def getReds(self):
        if self.reds is not None:
            return self.reds
        return []
    def getNbReds(self):
        if self.reds is not None:
            return len(self.reds)
        return 0

    def getShowIds(self):
        if self.rshowids is not None:
            return self.rshowids
        return []

    def getPreferencesManager(self):
        return self.pm
             
    def getPreferences(self):
        return self.preferences

    def getPreference(self, param_id):
        if self.preferences is not None and param_id in self.preferences:
            return self.preferences[param_id]["data"]
        else:
            return False
    def registerStartReadingFileCallback(self, fnc, *args, **kwargs):
        """Registers the function DataWrapper calls when it starts to read a file (to tell that it
        starts reading the file). Parameters: fnc, [*args,] [**kwargs],
        where fnc is a function with prototype
        fnc(msg, [short_msg], [*args], [**kwargs])"""
        self.startReadingFileCallback = (fnc, args, kwargs)

    def registerStopReadingFileCallback(self, fnc, *args, **kwargs):
        """Registers the function DataWrapper calls when it stops reading a file.
        Parameters: fnc, [*args,] [**kwargs],
        where fnc is a function with prototype
        fnc([msg], [*args], [**kwargs])"""
        self.stopReadingFileCallback = (fnc, args, kwargs)

    def __str__(self):
        return "coords = " + str(self.getCoords()) + "; " \
            + "data = " + str(self.data) + "; " \
            + "#reds = " + str(len(self.reds)) + "; " \
            + "rshowids = " + str(self.rshowids) + "; " \
            + "preferences = " + str(self.preferences) + "; " \
            + "package_name = " + str(self.package_name) + "; " \
            + "isChanged = " + str(self.isChanged) + "; " \
            + "isFromPackage = " + str(self.isFromPackage)

    ## Setters
    @property
    def isChanged(self):
        """The property tracking if dw (incl. reds and rshowids) has changed"""
        isChanged = self._isChanged
        if self.reds is not None:
            isChanged |= self.reds.isChanged
        if self.rshowids is not None:
            isChanged |= self.rshowids.isChanged
        if self.preferences is not None:
            isChanged |= self.preferences.isChanged 
        return isChanged
    
    @isChanged.setter
    def isChanged(self, value):
        if isinstance(value, bool):
            if value is False:
                if self.reds is not None:
                    self.reds.isChanged = value
                if self.rshowids is not None:
                    self.rshowids.isChanged = value
                if self.preferences is not None:
                    self.preferences.isChanged = value
            self._isChanged = value
        else:
            raise TypeError("The isChanged property accepts only Boolean attributes")

                #isChanged = property(_get_isChanged, _set_isChanged)
    
    @property
    def isFromPackage(self):
        """The property tracking if dw was loaded from a package"""
        return self._isFromPackage

    @isFromPackage.setter
    def isFromPackage(self, value):
        if isinstance(value, bool):
            self._isFromPackage = value
        else:
            raise TypeError("The isFromPackage property accepts only Boolean attributes")
        
    def updatePreferencesDict(self, params):
        #if type(params) == dict:
        if isinstance(params, collections.MutableMapping):
            self.preferences.update(params)
            self.resetSSetts()
            #self.isChanged = True

    def setData(self, data):
        self.data = data
        self.resetSSetts()

    def resetSSetts(self):
        if self.getData() is not None:
            if self.getData().hasMissing() is False:
                parts_type = "grounded"
            else:
                parts_type = self.preferences.get("parts_type", {"data": None})["data"]
            pval_meth = self.preferences.get("method_pval", {"data": None})["data"]
            self.getData().getSSetts().reset(parts_type, pval_meth)


################################################################
    def loadRedescriptionsFromFile(self, redescriptions_filename):
        """Loads new redescriptions from file"""
        tmp_reds, tmp_rshowids = (None, None)
        self._startMessage('importing', redescriptions_filename)
        try:
            tmp_reds, tmp_rshowids = self._readRedescriptionsFromFile(redescriptions_filename)
        except IOError as arg:
            self.logger.printL(1,"Cannot open: %s" % arg, "dw_error", "DW")
            self._stopMessage()
            raise
        except Exception:
            self.logger.printL(1,"Unexpected error while importing redescriptions from file %s!\n%s" % (redescriptions_filename, sys.exc_info()[1]), "dw_error", "DW")
            self._stopMessage()
            raise
        finally:
            self._stopMessage('importing')
        return tmp_reds, tmp_rshowids


#################### IMPORTS            
    def importDataFromCSVFiles(self, data_filenames):
        fnames = list(data_filenames[:2])
        self._startMessage('importing', fnames)        
        try:
            tmp_data = self._readDataFromCSVFiles(data_filenames)
        except DataError as details:
            self.logger.printL(1,"Problem reading files.\n%s" % details, "dw_error", "DW")
            self._stopMessage()
            raise
        except IOError as arg:
            self.logger.printL(1,"Cannot open: %s" % arg, "dw_error", "DW")
            self._stopMessage()
            raise
        except Exception:
            self.logger.printL(1,"Unexpected error while importing data from CSV files!\n%s" %  sys.exc_info()[1], "dw_error", "DW")
            self._stopMessage()
            raise
        else:
            self.setData(tmp_data)
            self.resetRedescriptions()
            self._isChanged = True
            self._isFromPackage = False
        finally:
            self._stopMessage('importing')

    def importRedescriptionsFromFile(self, redescriptions_filename):
        """Loads new redescriptions from file"""
        self._startMessage('importing', redescriptions_filename)
        try:
            tmp_reds, tmp_rshowids = self._readRedescriptionsFromFile(redescriptions_filename)
        except IOError as arg:
            self.logger.printL(1,"Cannot open: %s" % arg, "dw_error", "DW")
            self._stopMessage()
            raise
        except Exception:
            self.logger.printL(1,"Unexpected error while importing redescriptions from file %s!\n%s" % (redescriptions_filename, sys.exc_info()[1]), "dw_error", "DW")
            self._stopMessage()
            raise
        else:
            self.reds = tmp_reds
            self.rshowids = tmp_rshowids
        finally:
            self._stopMessage('importing')

    def importPreferencesFromFile(self, preferences_filename):
        """Imports mining preferences from file"""
        self._startMessage('importing', preferences_filename)
        try:
 
            tmp_preferences = self._readPreferencesFromFile(preferences_filename)
        except IOError as arg:
            self.logger.printL(1,"Cannot open: %s" % arg, "dw_error", "DW")
            self._stopMessage()
            raise
        except Exception:
            self.logger.printL(1,"Unexpected error while importing preferences from file %s!\n%s" % (preferences_filename, sys.exc_info()[1]), "dw_error", "DW")
            self._stopMessage()
            raise
        else:
            self.preferences = tmp_preferences
            self.preferences.isChanged = True 
        finally:
            self._stopMessage('importing')
            
    def openPackage(self, package_filename):
        """Loads new data from a package"""
        self._startMessage('loading', [package_filename])
        try:
            self._readPackageFromFile(package_filename)
        except DataError as details:
            self.logger.printL(1,"Problem reading files.\n%s" % details, "dw_error", "DW")
            self._stopMessage()
            raise
        except IOError as arg:
            self.logger.printL(1,"Cannot open: %s" % arg, "dw_error", "DW")
            self._stopMessage()
            raise
        except Exception:
            self.logger.printL(1,"Unexpected error while importing package from file %s!\n%s" % (package_filename, sys.exc_info()[1]), "dw_error", "DW")
            self._stopMessage()
            raise
        finally:
            self._stopMessage('loading')

######################## READS
    def _readDataFromCSVFiles(self, data_filenames):
        try:
            data = Data(data_filenames, "csv")
        except Exception:
            self._stopMessage()
            raise
        return data

    def _readRedescriptionsFromFile(self, filename, data=None):
        if data is None:
            if self.data is None:
                self._stopMessage()
                raise Exception("Cannot load redescriptions if data is not loaded")
            else:
                data = self.data
        reds = Batch([])
        show_ids = None

        filep = open(filename, mode='r')
        parseRedList(filep, data, reds)
        rshowids = ICList(range(len(reds)), True)
        return reds, rshowids

    def _readPreferencesFromFile(self, filename):
        filep = open(filename, mode='r')
        return ICDict(PreferencesReader(self.pm).getParameters(filep))

    def _readPackageFromFile(self, filename):
        package = Package(filename, self._stopMessage)
        elements_read = package.read(self.pm)        

        self.package_name = package.getPackagename()
        if elements_read.get("data") is not None:
            self.setData(elements_read.get("data"))
        else:
            self.data = None
        if elements_read.get("reds") is not None:
            self.reds = Batch(elements_read.get("reds"))
            self.rshowids = ICList(elements_read.get("rshowids"), False)
        else:
            self.reds = Batch([])
            self.rshowids = ICList([], False)
        if elements_read.get("preferences"):
            self.preferences = ICDict(elements_read.get("preferences"))
        else:
            self.preferences = self.pm.getDefaultTriplets()
        self.package = package
        self._isChanged = False
        self._isFromPackage = True
##        print "Done Loading"

    def prepareContentPackage(self):
        contents = {}
        if self.data is not None:
            contents['data'] = self.data                                
        if self.reds is not None and len(self.reds) > 0:
            contents['redescriptions'] = self.reds
            contents['rshowids'] = self.rshowids
        if self.preferences is not None:
            contents['preferences'] = self.preferences
            contents['pm'] = self.pm
        return contents


    def savePackageToFile(self, filename, suffix=Package.DEFAULT_EXT):
        try:
            if self.package is None:
                self.package = Package(None, self._stopMessage, mode="w")
            self._writePackageToFile(filename, suffix)
        except DataError as details:
            self.logger.printL(1,"Problem writing package.\n%s" % details, "dw_error", "DW")
            self._stopMessage()
            raise
        except IOError as arg:
            self.logger.printL(1,"Cannot open file for package %s" % filename, "dw_error", "DW")
            self._stopMessage()
            raise
        except Exception:
            self.logger.printL(1,"Unexpected error while writing package!\n%s" % sys.exc_info()[1], "dw_error", "DW")
            self._stopMessage()
            raise

    ## The saving function
    def _writePackageToFile(self, filename, suffix=Package.DEFAULT_EXT):
        """Saves all information to a new file"""
        if suffix is None:
            (filename, suffix) = os.path.splitext(filename)
        else:
            (fn, sf) = os.path.splitext(filename)
            if sf == suffix:
                filename = fn

        # Tell everybody
        self._startMessage('saving', filename+suffix)
        # Test that we can write to filename
        try:
            f = open(os.path.abspath(filename+suffix), 'a+')
        except IOError as arg:
            self.logger.printL(1,"Cannot open: %s" % arg, "dw_error", "DW")
            self._stopMessage()
            return
        else:
            f.close()
            
        self.package.writeToFile(filename+suffix, self.prepareContentPackage())
        # self._isChanged = False
        self.isChanged = False
        self._isFromPackage = True

        # Tell others we're done
        self._stopMessage('saving')
        ## END THE SAVING FUNCTION

    def getPackageSaveFilename(self):
        if self.package is not None:
            return self.package.getSaveFilename()
        return None
    
    def savePackage(self):
        """Saves to known package"""
        if self.package is None:
            raise ValueError('Cannot save if package_filename is None, use savePackageToFile instead')
        else:
            self.savePackageToFile(self.package.getSaveFilename(), None)

    def exportPreferences(self, filename, inc_def=False):
        self._startMessage('exporting prefs', filename)
        try:
            writePreferences(self.preferences, self.pm, filename, False, inc_def)
        except Exception:
            self._stopMessage()
            raise
        self._stopMessage('exporting prefs')

    def exportRedescriptions(self, filename, reds=None, rshowids=None):
        self._startMessage('exporting', filename)
        with_disabled = re.search("[^a-zA-Z0-9]all[^a-zA-Z0-9]", filename) is not None
        style = ""
        named = re.search("[^a-zA-Z0-9]named[^a-zA-Z0-9]", filename) is not None
        full_supp = re.search("[^a-zA-Z0-9]support[^a-zA-Z0-9]", filename) is not None
        if named:
            names = self.data.getNames()
        else:
            names = [None, None]
        if re.search("\.tex$", filename):
            style = "tex"
        try:
            if reds is None:
                reds = self.reds
                rshowids = self.rshowids
            if rshowids is None:
                rshowids = range(len(reds))
            writeRedescriptions(reds, filename, rshowids, names=names, with_disabled=with_disabled, style=style, full_supp=full_supp)
        except Exception:
            self._stopMessage()
            raise
        self._stopMessage('exporting')
            

    def _startMessage(self, action, filenames):
        "Shows the message if needed"
        if self.startReadingFileCallback is not None:
            (fnc, args, kwargs) = self.startReadingFileCallback
            msg = 'Please wait. ' + action.capitalize() + ' file'
            short_msg = action.capitalize() + ' file'
            if len(filenames) <= 1:
                msg += ' '
            else:
                msg += 's '
                short_msg += 's'

            if isinstance(filenames, basestring):
                # In Python 3, test has to be isinstance(filenames, str)
                filenames = [filenames]
            msg += ' '.join(map(os.path.basename, filenames))
            # filename can be a list of filenames with full paths, hence map()
            fnc(msg, short_msg, *args, **kwargs)

    def _stopMessage(self, action=None):
        "Removes the message if needed"
        if self.stopReadingFileCallback is not None:
            (fnc, args, kwargs) = self.stopReadingFileCallback
            if action is None:
                mess = "An error occurred"
            else:
                mess = action.capitalize()+' done'
            fnc(mess, *args, **kwargs)

    # def getPolys(self, pdp, boundaries):
    #     if pdp is not None and self.pdp != pdp:
    #         self.pdp = pdp
    #         try:
    #             self.polys = make_polys.makePolys(self.pdp, boundaries)
    #         except Exception as e:
    #             self.logger.printL(1,"Failed drawing polygons.\nFall back to dots...", "dw_error", "DW")
    #             self.polys = None
    #     return self.polys


# def main():
#     # print "UNCOMMENT"
#     # pdb.set_trace()
#     pref_dir = os.path.dirname(__file__)
#     conf_defs = [findFile('miner_confdef.xml', ['../reremi', os.path.split(pref_dir)[0]+'/reremi', './confs']),
#                  findFile('ui_confdef.xml', [pref_dir, './confs'])]

#     dw = DataWrapper(None,"/home/galbrun/TKTL/redescriptors/sandbox/runs/rajapaja_basic/rajapaja.siren", conf_defs)
#     dw.savePackage()
#     dw_new = DataWrapper(None,"/home/galbrun/TKTL/redescriptors/sandbox/runs/rajapaja_basic/rajapaja_new.siren")
#     for red in dw_new.reds:
#         print red

# if __name__ == '__main__':
#     main()
