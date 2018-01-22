import tempfile
import os.path
import plistlib
import shutil
import zipfile
import codecs
import re

import pdb

from classRedescription import Redescription, printTexRedList, printRedList, parseRedList
from classData import Data
from classQuery import Query
from classPreferencesManager import PreferencesReader, getPM
import toolRead as toolRead


class Package(object):
    """Class to handle the zip packages that contain data, preferences, results, etc. for redescription mining.
    """

    # CONSTANTS
    # Names of the files in the package
    DATA_FILENAMES = ['data_LHS.csv',
                     'data_RHS.csv']
    REDESCRIPTIONS_FILENAME = 'redescriptions.csv'
    PREFERENCES_FILENAME = 'preferences.xml'
    PLIST_FILE = 'info.plist'
    PACKAGE_NAME = 'siren_package'

    FILETYPE_VERSION = 5
    XML_FILETYPE_VERSION = 3

    NA_str = "NA"

    CREATOR = "ReReMi/Siren Package"
    DEFAULT_EXT = ".siren"
    DEFAULT_TMP = "siren"

    def __init__(self, filename, callback_mess=None, mode="r"):
        if filename is not None:
            filename = os.path.abspath(filename)
            if mode !="w" and not os.path.isfile(filename):
                raise IOError('File does not exist')
            if mode !="w" and not zipfile.is_zipfile(filename):
                raise IOError('File is of wrong type')
        self.filename = filename
        self.callback_mess = callback_mess
        self.plist = dict(creator = self.CREATOR,
                          filetype_version = self.FILETYPE_VERSION)

    def __str__(self):
        return "PACKAGE: %s" % self.filename

    def raiseMess(self):
        if self.callback_mess is not None:
            self.callback_mess()

    def getFilename(self):
        return self.filename

    def getPackagename(self):
        return self.plist.get('package_name')

    def getFormatV(self):
        return self.plist.get('filetype_version', -1)
    def isOldXMLFormat(self):
        return self.getFormatV() <= self.XML_FILETYPE_VERSION
    def isLatestFormat(self):
        return self.getFormatV() == self.FILETYPE_VERSION

    def getSaveFilename(self):
        svfilename = self.filename
        if self.isOldXMLFormat():
            parts = self.filename.split(".")
            if len(parts) == 1:
                svfilename += "_new"
            elif len(parts) > 1:
                svfilename = ".".join(parts[:-1]) + "_new."+ parts[-1]
        return svfilename

    def getNamelist(self):
        return self.package.namelist()

    def closePack(self):
        if self.package is not None:
            self.package.close()
            self.package = None
            
    def openPack(self):
        try:
            self.package = zipfile.ZipFile(self.filename, 'r')
            plist_fd = self.package.open(self.PLIST_FILE, 'r')
            self.plist = plistlib.readPlist(plist_fd)
        except Exception:
            self.package = None
            self.plist = {}
            self.raiseMess()
            raise

######### READING ELEMENTS
##########################

    def read(self, pm, options_args=None):
        elements_read = {}
        self.openPack()

        try:
            preferences = self.readPreferences(pm, options_args)
            if preferences is not None:
                elements_read["preferences"] = preferences
            ## self.plist["NA_str"] = "nan"
            data = self.readData()
            if data is not None:
                elements_read["data"] = data
                reds, rshowids = self.readRedescriptions(data)
                if reds is not None:
                    elements_read["reds"] = reds
                    elements_read["rshowids"] = rshowids
        finally:
            self.closePack()
        return elements_read

    def readPreferences(self, pm, options_args=None):
        # Load preferences
        preferences = None
        if 'preferences_filename' in self.plist:
            try:
                fd = self.package.open(self.plist['preferences_filename'], 'r')
                preferences = PreferencesReader(pm).getParameters(fd, options_args)
            except Exception:
                self.raiseMess()
                raise
            finally:
                fd.close()
        return preferences


    def readData(self):
        data = None
        # Load data
        if self.isOldXMLFormat():
            ################# START FOR BACKWARD COMPATIBILITY WITH XML
            if 'data_filename' in self.plist:
                try:
                    fd = self.package.open(self.plist['data_filename'], 'r')
                    data = Data.readDataFromXMLFile(fd)
                except Exception as e:
                    print e
                    self.raiseMess()
                    raise
                finally:
                    fd.close()

        elif 'data_LHS_filename' in self.plist:
            try:
                fdLHS = self.package.open(self.plist['data_LHS_filename'], 'r')
                if self.plist.get('data_RHS_filename', self.plist['data_LHS_filename']) != self.plist['data_LHS_filename']:
                    fdRHS = self.package.open(self.plist['data_RHS_filename'], 'r')
                else:
                    fdRHS = None
                NA_str = self.plist.get('NA_str', None)
                if NA_str is None and self.getFormatV() <= 4:
                    NA_str = "nan"
                # pdb.set_trace()    
                data = Data([fdLHS, fdRHS, {}, NA_str], "csv")
            except Exception:
                data = None
                self.raiseMess()
                raise
            finally:
                fdLHS.close()
                if fdRHS is not None: 
                    fdRHS.close()
        return data

    def readRedescriptions(self, data):
        reds = None
        rshowids = None
        # Load redescriptions
        if 'redescriptions_filename' in self.plist:
            try:
                fd = self.package.open(self.plist['redescriptions_filename'], 'r')
                if self.isOldXMLFormat():
                    reds, rshowids = readRedescriptionsXML(fd, data)
                else:
                    reds = []
                    parseRedList(fd, data, reds)
                    rshowids = range(len(reds))
            except Exception:
                self.raiseMess()
                raise
            finally:
                fd.close()
        return reds, rshowids

######### WRITING ELEMENTS
##########################
    def getTmpDir(self):
        return tempfile.mkdtemp(prefix=self.DEFAULT_TMP)
            
    ## The saving function
    def writeToFile(self, filename, contents):
        # Store old package_filename
        old_package_filename = self.filename
        self.filename = os.path.abspath(filename)
        # Get a temp folder
        tmp_dir = self.getTmpDir()
        #package_dir = os.path.join(tmp_dir, filename)
        #os.mkdir(package_dir)

        # Write plist
        plist, filens = self.makePlistDict(contents)
        try:
            plistlib.writePlist(plist, os.path.join(tmp_dir, self.PLIST_FILE))
        except IOError:
            shutil.rmtree(tmp_dir)
            self.filename = old_package_filename
            self.raiseMess()
            raise

        # Write data files
        if "data" in contents:
            try:
                filenames = [os.path.join(tmp_dir, plist['data_LHS_filename']), None]
                if plist.get('data_RHS_filename', plist['data_LHS_filename']) != plist['data_LHS_filename']:
                    filenames[1] = os.path.join(tmp_dir, plist['data_RHS_filename'])
                writeData(contents["data"], filenames, toPackage = True)
            except IOError:
                shutil.rmtree(tmp_dir)
                self.filename = old_package_filename
                self.raiseMess()
                raise

        # Write redescriptions
        if "redescriptions" in contents:
            try:
                writeRedescriptions(contents["redescriptions"], os.path.join(tmp_dir, plist['redescriptions_filename']),
                                    contents["rshowids"], names=False, with_disabled=True, toPackage = True)
            except IOError:
                shutil.rmtree(tmp_dir)
                self.filename = old_package_filename
                self.raiseMess()
                raise

        # Write preferences
        if "preferences" in contents:
            try:
                writePreferences(contents["preferences"], contents["pm"],
                                 os.path.join(tmp_dir, plist['preferences_filename']), toPackage = True)
            except IOError:
                shutil.rmtree(tmp_dir)
                self.filename = old_package_filename
                self.raiseMess()
                raise

        # All's there, so pack
        try:
            package = zipfile.ZipFile(self.filename, 'w')
            package.write(os.path.join(tmp_dir, self.PLIST_FILE),
                          arcname = os.path.join('.', self.PLIST_FILE))
            for eln, element in filens.items():
                package.write(os.path.join(tmp_dir, element),
                              arcname = os.path.join('.', element),
                              compress_type = zipfile.ZIP_DEFLATED)
        except Exception:
            shutil.rmtree(tmp_dir)
            self.filename = old_package_filename
            self.raiseMess()
            raise
        finally:
            package.close()

        # All's done, delete temp file
        shutil.rmtree(tmp_dir)

    
    def makePlistDict(self, contents):
        """Makes a dict to write to plist."""
        d = dict(creator = self.CREATOR,
            filetype_version = self.FILETYPE_VERSION)
        
        if self.filename is None:
            d['package_name'] = self.PACKAGE_NAME
        else:
            (pn, suffix) = os.path.splitext(os.path.basename(self.filename))
            if len(pn) > 0:
                d['package_name'] = pn
            else:
                d['package_name'] = self.PACKAGE_NAME

        fns = {}              
        if "data" in contents:
            d['NA_str'] = contents["data"].NA_str
            fns['data_LHS_filename'] = self.DATA_FILENAMES[0]
            if not contents["data"].isSingleD():
                fns['data_RHS_filename'] = self.DATA_FILENAMES[1]
                                
        if "redescriptions" in contents and len(contents["redescriptions"]) > 0:
            fns['redescriptions_filename'] = self.REDESCRIPTIONS_FILENAME

        if "preferences" in contents:
            fns['preferences_filename'] = self.PREFERENCES_FILENAME
        d.update(fns)
        return d, fns


######### ADDITIONAL FUNCTIONS
###############################

def readRedescriptionsXML(filep, data):
    red = []
    show_ids = None
    
    doc = toolRead.parseXML(filep)
    if doc is not None:
        tmpreds = doc.getElementsByTagName("redescriptions")
        if len(tmpreds) == 1:
            reds_node = tmpreds[0]
            for redx in reds_node.getElementsByTagName("redescription"):
                tmp = Redescription()
                tmp.fromXML(redx)
                tmp.recompute(data)
                reds.append(tmp)
            tmpsi = reds_node.getElementsByTagName("showing_ids")
            if len(tmpsi) == 1:
                show_ids = toolRead.getValues(tmpsi[0], int)
                if len(show_ids) == 0 or min(show_ids) < 0 or max(show_ids) >= len(reds):
                    show_ids = None
    if show_ids is None:
        show_ids = range(len(reds))
    return reds, rshowids


def writeRedescriptions(reds, filename, rshowids=None, names = [None, None], with_disabled=False, toPackage = False, style="", full_supp=False):
    if names is False:
        names = [None, None]
    if rshowids is None:
        rshowids = range(len(reds))
    red_list = [reds[i] for i in rshowids if reds[i].getEnabled() or with_disabled]
    if toPackage:
        fields_supp = [-1, "status_disabled"]
    else:
        fields_supp = None
        # with codecs.open(filename, encoding='utf-8', mode='w') as f:
    with open(filename, mode='w') as f:
        if style == "tex":
            f.write(codecs.encode(printTexRedList(red_list, names, fields_supp), 'utf-8','replace'))
        else:
            f.write(codecs.encode(printRedList(red_list, names, fields_supp, full_supp=full_supp), 'utf-8','replace'))
            
def writePreferences(preferences, pm, filename, toPackage = False, inc_def=False):
    with open(filename, 'w') as f:
        f.write(PreferencesReader(pm).dispParameters(preferences, True, defaults=inc_def))

def writeData(data, filenames, toPackage = False):
    data.writeCSV(filenames)

def saveAsPackage(filename, data, preferences=None, pm=None, reds=None):
    package = Package(None, None, mode="w")

    (filename, suffix) = os.path.splitext(filename)
    contents = {}
    if data is not None:
        contents['data'] = data                                
    if reds is not None and len(reds) > 0:
        contents['redescriptions'] = reds
        contents['rshowids'] = range(len(reds))
    if preferences is not None:
        if pm is None:
            pm = getPM()
        contents['preferences'] = preferences
        contents['pm'] = pm

    package.writeToFile(filename+suffix, contents)
