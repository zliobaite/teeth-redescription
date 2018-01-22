import wx
import wx.grid
### from wx import grid
### from wx import Size, Brush, Colour, NullBrush, NullPen 
### from wx import DC, EVT_KEY_UP, NORMAL_FONT, SOLID, TRANSPARENT_PEN

import re, colorsys, random, datetime, math
from ..reremi.toolICList import ICList
from ..reremi.classData import ColM
from ..reremi.classQuery import SYM, Query, Literal
from ..reremi.classRedescription import Redescription

import pdb

def getRGB(h,l, s):
    Brgb = map(int, [255*v for v in colorsys.hls_to_rgb(h, l, s)])
    if l > 0.5:
        Frgb = map(int, [255*v for v in colorsys.hls_to_rgb(h, 0, s)])
    else:
        Frgb = map(int, [255*v for v in colorsys.hls_to_rgb(h, 1, s)])
    return Brgb, Frgb


class CustRenderer(wx.grid.PyGridCellRenderer):

    BACKGROUND = wx.Colour(255, 255, 255, 255) # wx.Colour(100,100,100)
    TEXT = wx.Colour(76, 76, 76, 255)  #wx.Colour(100,100,100)
    SBRUSH = wx.SOLID
    
    BACKGROUND_SELECTED = wx.Colour(240, 119, 70, 255) # wx.Colour(100,100,100)
    TEXT_SELECTED = wx.Colour(255, 255, 255, 255) # wx.Colour(100,100,100)
    SBRUSH_SELECTED = wx.SOLID

    BACKGROUND_GREY = wx.Colour(240,255,240)
    TEXT_GREY = wx.Colour(131,139,131)
    SBRUSH_GREY = wx.SOLID

    MAP_SORT_NAN = {float('Nan'): None}
    
    """Base class for editors"""

    ### Customisation points
    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        """Customisation Point: Draw the data from grid in the rectangle with attributes using the dc"""

        dc.SetClippingRegion( rect.x, rect.y, rect.width, rect.height )
        back, fore, bstyle = self.BACKGROUND, self.TEXT, self.SBRUSH
        value = grid.GetCellValue( row, col )
        
        if row in grid.GetSelectedRows():
            back, fore, bstyle = self.BACKGROUND_SELECTED, self.TEXT_SELECTED, self.SBRUSH_SELECTED
        elif grid.GetTable().getEnabled(row) == 0:
            back, fore, bstyle = self.BACKGROUND_GREY, self.TEXT_GREY, self.SBRUSH_GREY
        try:
            dc.SetTextForeground( fore )
            dc.SetTextBackground( back)
            dc.SetBrush( wx.Brush( back, bstyle) )
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.DrawRectangle( rect.x, rect.y, rect.width, rect.height )
            dc.SetFont( wx.NORMAL_FONT )
            dc.DrawText( value, rect.x+2,rect.y+2 )
        finally:
            dc.SetTextForeground( self.TEXT)
            dc.SetTextBackground( self.BACKGROUND)
            dc.SetPen( wx.NullPen )
            dc.SetBrush( wx.NullBrush )
            dc.DestroyClippingRegion( )

    # def GetBestSize(self, grid, attr, dc, row, col):
    #     """Customisation Point: Determine the appropriate (best) size for the control, return as wxSize
    #     Note: You _must_ return a wxSize object.  Returning a two-value-tuple
    #     won't raise an error, but the value won't be respected by wxPython.
    #     """         
    #     x,y = dc.GetTextExtent( "%s" % grid.GetCellValue( row, col ) )
    #     # note that the two-tuple returned by GetTextExtent won't work,
    #     # need to give a wxSize object back!
    #     return wx.Size( min(x, 10), min(y, 10))


class ColorRenderer(CustRenderer):

    ### Customisation points
    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        """Customisation Point: Draw the data from grid in the rectangle with attributes using the dc"""

        dc.SetClippingRegion( rect.x, rect.y, rect.width, rect.height )
        back, fore, bstyle = self.BACKGROUND, self.TEXT, self.SBRUSH
        value = grid.GetCellValue( row, col )
        
        tmp = re.match("^#h(?P<h>[0-9]*)l(?P<l>[0-9]*)#(?P<val>.*)$", value)
        if tmp is not None:
            s = 1
            if row in grid.GetSelectedRows(): s=0.5
            elif grid.GetTable().getEnabled(row) == 0: s= 0.2 
            rgb_back, rgb_fore = getRGB(int(tmp.group("h"))/255.0, int(tmp.group("l"))/255.0, s)
            back, fore, bstyle = wx.Colour(*rgb_back), wx.Colour(*rgb_fore), self.SBRUSH
            value = tmp.group("val")
        elif row in grid.GetSelectedRows():
            back, fore, bstyle = self.BACKGROUND_SELECTED, self.TEXT_SELECTED, self.SBRUSH_SELECTED
        elif grid.GetTable().getEnabled(row) == 0:
            back, fore, bstyle = self.BACKGROUND_GREY, self.TEXT_GREY, self.SBRUSH_GREY
        try:
            dc.SetTextForeground( fore )
            dc.SetTextBackground( back)
            dc.SetBrush( wx.Brush( back, bstyle) )
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.DrawRectangle( rect.x, rect.y, rect.width, rect.height )
            dc.SetFont( wx.NORMAL_FONT )
            dc.DrawText( value, rect.x+2,rect.y+2 )
        finally:
            dc.SetTextForeground( self.TEXT)
            dc.SetTextBackground( self.BACKGROUND)
            dc.SetPen( wx.NullPen )
            dc.SetBrush( wx.NullBrush )
            dc.DestroyClippingRegion( )

    # def GetBestSize(self, grid, attr, dc, row, col):
    #     """Customisation Point: Determine the appropriate (best) size for the control, return as wxSize
    #     Note: You _must_ return a wxSize object.  Returning a two-value-tuple
    #     won't raise an error, but the value won't be respected by wxPython.
    #     """         
    #     x,y = dc.GetTextExtent( "%s" % grid.GetCellValue( row, col ) )
    #     # note that the two-tuple returned by GetTextExtent won't work,
    #     # need to give a wxSize object back!
    #     return wx.Size( min(x, 10), min(y, 10))


class GridTable(wx.grid.PyGridTableBase):

    fields_def = []
    renderer = CustRenderer
    name_m = None

    #### COLUMN WIDTHS
    width_colcheck = 25
    width_colid = 50
    width_colname = 150
    width_colnamew = 300
    width_colinfo = 80
    width_colinfow = 100
    width_colinfon = 8


    def __init__(self, parent, tabId, frame, short=None):
        wx.grid.PyGridTableBase.__init__(self)
        self.details = {}
        self.short = short
        self.sc = set() # show column (for collapsed/expanded columns)
        self.parent = parent
        self.tabId = tabId
        self.fields = self.fields_def
        self.data = ICList()
        self.sortids = ICList()
        self.sortP = (None, False)
        self.currentRows = self.nbItems()
        self.currentColumns = len(self.fields)
        self.matching = [] ### for find function
        
        #### GRID
        self.grid = wx.grid.Grid(frame)
        self.grid.SetTable(self)
        self.setSelectedRow(0)
        self.grid.EnableEditing(False)
        #self.grid.AutoSizeColumns(True)

        self.grid.RegisterDataType(wx.grid.GRID_VALUE_STRING,
                                   self.renderer(),
                                   wx.grid.GridCellAutoWrapStringEditor())

        self.grid.RegisterDataType(wx.grid.GRID_VALUE_BOOL,
                              wx.grid.GridCellBoolRenderer(),
                              wx.grid.GridCellBoolEditor()) 

        # attr = wx.grid.GridCellAttr()
        # attr.SetEditor(wx.grid.GridCellBoolEditor())
        # attr.SetRenderer(wx.grid.GridCellBoolRenderer())
        # self.grid.SetColAttr(0,attr)

        ########## HERE
        self.grid.Bind(wx.EVT_KEY_UP, self.OnKU)
        self.grid.Bind(wx.grid.EVT_GRID_LABEL_LEFT_CLICK, self.setSort)
        self.grid.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self.setFocus)
        self.grid.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.OnViewData)
        self.grid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnRightClick)
        self.grid.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.OnMouse)
        
    # def showPopupMenu(self, event):
    #     self.table.highlightRow(event.GetRow())
    #     parent.currentList = self

    def GetCellBackgroundColor(self, row, col):
        """Return the value of a cell"""
        return wx.Colour(100,100,100)

    def Hide(self):
        self.grid.Hide()

    def Show(self):
        self.grid.Show()

    ### GRID METHOD
    def GetNumberRows(self):
        """Return the number of rows in the grid"""
        return self.nbItems()

    ### GRID METHOD
    def GetColLabelValue(self, col):
        """Return the number of rows in the grid"""
        direct = '  '
        if col == self.sortP[0]:
            if self.sortP[1]:
                direct = SYM.SYM_ARRTOP
            else:
                direct = SYM.SYM_ARRBOT
        return "  %s %s" % (self.fields[col][0], direct)

    ### GRID METHOD
    def GetNumberCols(self):
        """Return the number of columns in the grid"""
        return len(self.fields)

    ### GRID METHOD
    def IsEmptyCell(self, row, col):
        """Return True if the cell is empty"""
        return self.GetValue(row, col) is None

    ### GRID METHOD
    def GetTypeName(self, row, col):
        """Return the name of the data type of the value in the cell"""
        if (col == 0):
            return wx.grid.GRID_VALUE_BOOL
        else:
            return wx.grid.GRID_VALUE_STRING
        # if row < len(self.sortids) and col < len(self.fields):
        #     return self.getFieldV(self.sortids[row], self.fields[col], dict(self.details))
        # else:
        #     return None

    def getFieldV(self, x, field, details):
        methode = eval(field[1])
        if callable(methode):
            if len(field) > 2 and field[2] is not None:
                details.update(field[2])
            try:
                return methode(details)
            except IndexError:
                methode(details)
        else:
            return methode

    ### GRID METHOD
    def GetValue(self, row, col):
        """Return the value of a cell"""
        if row >= 0 and row < self.nbItems() and col >= 0 and col < len(self.fields):
            details = {"aim": "list"}
            details.update(self.details)
            # print "Here!", self.tabId, self.parent.selectedTab['id']#, self.sortids, row, self.fields, col
            #pdb.set_trace()
            return "%s" % self.getFieldV(self.sortids[row], self.fields[col], details)
        else:
            return None

    ### GRID METHOD
    def SetValue(self, row, col, value):
        pass

    def getNamesList(self):
        """Return the value of a cell"""
        names_list = []
        details = {"aim": "list"}
        details.update(self.details)
        if self.name_m is not None:
            for x in self.sortids:
                v = "%s" % self.getFieldV(x, (0, self.name_m), details)
                names_list.append((x,v))
        return names_list

    def nbItems(self):
        return len(self.sortids)

    def getItemAtRow(self, row):
        """Return the data of a row"""
        if row < self.nbItems() and self.sortids[row] < len(self.data):
            return self.data[self.sortids[row]]
        else:
            return None

    def getRowForItem(self, rid):
        """Return the row of an entry"""
        try:
            return self.sortids.index(rid)
        except:
            return None

    def getPositionFromRow(self, row):
        if row is not None and row < self.nbItems() and self.sortids[row] < len(self.data):
            return self.sortids[row]
        else:
            return None

    def getRowFromPosition(self, pos):
        try:
            return self.sortids.index(pos)
        except:
            return None

    def resetSizes(self):
        self.GetView().AutoSize()
        for coli, f in enumerate(self.fields):
            if len(f) > 3:
                self.GetView().SetColSize(coli, f[3])

    def resetDetails(self, details={}, review=True):
        self.sortP = (None, False)
        self.details = details
        if review:
            self.ResetView()
            self.resetSizes()
            
    def resetData(self, data=None, srids=None):
        if data is not None:
            self.data = data
        else:
            self.data = ICList()
        
        if srids is not None:
            self.sortids = srids
        else:
            self.sortids = ICList([idi for idi in range(len(self.data))], True)

        self.resetFields()
        self.updateSort()
        self.ResetView()
        self.resetSizes()

    def resetFields(self, dw=None, review=True):
        self.sortP = (None, False)

    def getEnabled(self, row):
        return self.getItemAtRow(row).getEnabled()

    def notify_change(self):
        if type(self.data) == ICList:
            self.data.isChanged = True

    def flipEnabled(self, row):
        self.data[self.sortids[row]].flipEnabled()
        self.notify_change()
        self.ResetView()

    def flipAllEnabled(self, dids=None):
        if dids is None:
            dids = range(len(self.data))
        for did in dids:
            self.data[did].flipEnabled()
        self.notify_change()
        self.ResetView()

    def setAllDisabled(self, dids=None):
        if dids is None:
            dids = range(len(self.data))
        for did in dids:
            self.data[did].setDisabled()
        self.notify_change()
        self.ResetView()

    def setAllEnabled(self, dids=None):
        if dids is None:
            dids = range(len(self.data))
        for did in dids:
            self.data[did].setEnabled()
        self.notify_change()
        self.ResetView()

    def OnMouse(self,event):
        if event.GetRow() < self.nbItems():
            self.setSelectedRow(event.GetRow(), event.GetCol())
            if event.Col == 0:
                self.flipEnabled(event.GetRow())                
       
    def ResetView(self):
        """Trim/extend the control's rows and update all values"""
        self.GetView().BeginBatch()
        for current, new, delmsg, addmsg in [
                (self.currentRows, self.GetNumberRows(), wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED),
                (self.currentColumns, self.GetNumberCols(), wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED, wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED),
        ]:
            if new < current:
                msg = wx.grid.GridTableMessage(
                        self,
                        delmsg,
                        new,    # position
                        current-new,
                )
                self.GetView().ProcessTableMessage(msg)
            elif new > current:
                msg = wx.grid.GridTableMessage(
                        self,
                        addmsg,
                        new-current
                )
                self.GetView().ProcessTableMessage(msg)
        self.GetView().EndBatch()
        self.currentRows = self.nbItems()
        self.currentColumns = len(self.fields)

        if self.getSelectedRow() is not None and not self.grid.IsVisible(self.getSelectedRow(), 0):
            self.grid.MakeCellVisible(self.getSelectedRow(), 0)

    def deleteDisabled(self):
        pass

    def getSelectedItem(self):
        if self.getSelectedRow() is not None:
            return self.getItemAtRow(self.getSelectedRow())
        return

    def getSelectedPos(self):
        if self.getSelectedRow() is not None:
            return self.getPositionFromRow(self.getSelectedRow())
        return
    
    def getSelectedRow(self):
        if len(self.GetView().GetSelectedRows()) > 0:
            return self.GetView().GetSelectedRows()[0]
        else:
            return None

    def getSelectedCol(self):
        return max(0,self.GetView().GetGridCursorCol())

    def setSelectedRow(self, row, col=0):
        if row is None: row = 0
        if col is None: col = 0
        self.GetView().SetGridCursor(row,col)
        self.GetView().SelectRow(row)
        
    def neutraliseSort(self):
        self.sortP = (None, False)

    def setSort(self, event):
        colS = event.GetCol()
        if colS == -1:
            pass ### TODO select all
        else:
            old = self.sortP[0]
            if self.sortP[0] == colS:
                self.sortP = (self.sortP[0], not self.sortP[1])
            else:
                self.sortP = (colS, True)
            self.updateSort()
            self.ResetView()

    def setFocus(self, event):
        pass
        
    def updateSort(self):
        selected_row = self.getSelectedRow()
        selected_col = self.getSelectedCol()
        selected_id = None
        if selected_row is not None:
            selected_id = self.getPositionFromRow(selected_row)

        if self.sortP[0] is not None:
            details = {"aim": "sort"}
            details.update(self.details)
            self.sortids.sort(key= lambda x: self.getFieldV(x, self.fields[self.sortP[0]], details), reverse=self.sortP[1])
        if selected_id is not None:
            self.setSelectedRow(self.getRowFromPosition(selected_id), selected_col)

    def quitFind(self):
        pass

    def updateFindO(self, matching, non_matching, cid=None):
        if len(matching) > 0:
            self.sortP = (None, False)
            selected_col = self.getSelectedCol()
            self.sortids = matching+non_matching
            self.matching = matching
            self.setSelectedRow(len(matching)-1, selected_col)
            self.ResetView()

    def updateFind(self, matching=None, non_matching=None, cid=None):
        if matching is not None:
            self.matching = matching
        if matching is None or len(matching) > 0:
            self.setSelectedRow(self.getNextMatch(cid), self.getSelectedCol())
            self.ResetView()

    def getNextMatch(self, n=None):
        if n is None:
            n = self.getSelectedRow()
        
        if len(self.matching) > 0:
            if n >= self.getRowForItem(self.matching[-1]):
                return self.getRowForItem(self.matching[0])
            else:
                for si in range(len(self.matching)):
                    if self.getRowForItem(self.matching[si]) > n:
                        return self.getRowForItem(self.matching[si])
        else:
            n += 1
            if n == self.nbItems():
                n = 0
            return n
            
    def OnRightClick(self, event):
        if event.GetRow() < self.nbItems():
            self.setSelectedRow(event.GetRow(), event.GetCol())
            self.parent.makePopupMenu(self.parent.toolFrame)

    def OnKU(self, event):
        if self.grid.GetGridCursorRow() < self.nbItems():
            self.setSelectedRow(self.grid.GetGridCursorRow(), self.grid.GetGridCursorCol())
        event.Skip()

    def OnViewData(self, event):
        if event.GetRow() < self.nbItems():
            self.setSelectedRow(event.GetRow(), event.GetCol())
            self.viewData()

class VarTable(GridTable):     

    fields_def = [('','self.data[x].getEnabled', None, GridTable.width_colcheck),
                  ('id', 'self.data[x].getId', None, GridTable.width_colid),
                  ('name', 'self.data[x].getName', None, GridTable.width_colnamew),
                  ('type', 'self.data[x].getType', None, GridTable.width_colinfow)]
    fields_miss = [('missing', 'self.data[x].getMissInfo', None, GridTable.width_colinfo)]
    fields_var = {1: [('density', 'self.data[x].getDensity', None, GridTable.width_colinfo)],
                  2:[('categories', 'self.data[x].getCategories', None, GridTable.width_colinfo)],
                  3:[('min', 'self.data[x].getMin', None, GridTable.width_colinfo),
                     ('max', 'self.data[x].getMax', None, GridTable.width_colinfo)]}
    name_m = 'self.data[x].getName'

    def notify_change(self):
        self.parent.updateDataInfo()
        if type(self.data) == ICList:
            self.data.isChanged = True

    
    def viewData(self, pos=None, viewT=None):
        if viewT is None:
            viewT = self.parent.viewsm.getDefaultViewT("R", self.parent.tabs[self.tabId]["type"])
        if pos is None:
            datVar = self.getSelectedItem()
        else:
            datVar = self.getItemAtRow(pos)
        queries = [Query(), Query()]
        queries[datVar.side].extend(-1, Literal(False, datVar.getTerm()))
        self.parent.viewsm.newRedVHist(queries, viewT)
 
    def resetFields(self, dw=None, review=True):
        self.sortP = (None, False)
        self.fields = []
        self.fields.extend(self.fields_def)
        if len([r for r in self.data if r.hasMissing()]) > 0:
            self.fields.extend(self.fields_miss)
        for tyid in set([r.typeId() for r in self.data]):
            self.fields.extend(self.fields_var[tyid])


class RowTable(GridTable):     
    ## (#NBROWS)
    fields_def = [('','self.data[x].getEnabled'),
                  ('id', 'self.data[x].getId')]
    name_m = 'self.data[x].getRName'
    renderer = ColorRenderer

    def __init__(self, parent, tabId, frame, short=None):
        GridTable.__init__(self, parent, tabId, frame, short)
        self.fix_col = 0

    def viewData(self, pos=None, viewT=None):
        if viewT is None:
            viewT = self.parent.viewsm.getDefaultViewT("R", self.parent.tabs[self.tabId]["type"])
        queries = [Query(), Query()]
        self.parent.viewsm.newRedVHist(queries, viewT)
 
    def resetFields(self, dw=None, review=True):
        self.sortP = (None, False)
        self.fix_col = 2
        if dw is not None:
            self.cols_map = {}
            self.fields = []
            for f in self.fields_def:
                f = (re.sub("NBROWS", "%d" % dw.getData().nbRows(), f[0]), f[1])
                self.fields.append(f)
            ## self.fields.extend(self.fields_def)
            if dw.getData().hasRNames():
                self.fields.append(('name', 'self.data[x].getRName'))
                name_m = 'self.data[x].getRName'
                self.fix_col += 1
            for side, sideS in [(0, "LHS"),(1, "RHS")]:
                nb = max(1,len(dw.getDataCols(side))-1.0)
                for ci, col in enumerate(dw.getDataCols(side)):
                    self.cols_map[(side, col.getId())] = len(self.fields)
                    self.fields.append(("%s:%s" % (sideS, col.getName()), 'self.data[x].getValue', {"side":side, "col": col.getId(), "range": col.getRange(), "NA": col.NA, "r":ci/nb}))
            if review:
                self.ResetView()


    ### GRID METHOD
    def GetValue(self, row, col):
        """Return the value of a cell"""
        if row >= 0 and row < self.nbItems() and col >= 0 and col < len(self.fields):
            details = {"aim": "row"}
            details.update(self.details)
            tmp = self.getFieldV(self.sortids[row], self.fields[col], details)
            details = {"aim": "list"}
            details.update(self.details)
            labl = self.getFieldV(self.sortids[row], self.fields[col], details)
            if col >= self.fix_col:
                h = 125*self.fields[col][2]["side"] + int(100*self.fields[col][2]["r"])
                if tmp == "-" or (math.isnan(tmp) and math.isnan(self.fields[col][2]["NA"])) \
                       or (tmp == self.fields[col][2]["NA"]):
                    l = 255
                else:
                    rangeV = self.fields[col][2]["range"]
                    lr = row/(1.0*self.nbItems())
                    if type(rangeV) is dict:
                        if len(rangeV) > 1:
                            lr = rangeV.get(tmp, 0)/(len(rangeV)-1.0)
                        else:
                            lr = 1
                    elif type(rangeV) is tuple:
                        if rangeV[0] != rangeV[1]:
                            lr = (rangeV[1]-tmp)/(rangeV[1]-rangeV[0])
                        else:
                            lr = 1
                    l = 125*lr+100

                # sc = 1.0*self.fields[col][2]["max"] - self.fields[col][2]["min"]
                # if sc == 0:
                #     lr = 0.5
                # else:
                #     lr = (tmp - self.fields[col][2]["min"])/sc
                if col in self.sc:
                    return "#h%dl%d#%s" % (h,l,labl)
                else:
                    try:
                        return "#h%dl%d#%s" % (h,l,"")
                    except TypeError:
                        print h,l, tmp, self.fields[col][2]["range"], self.fields[col][2]["NA"]
            else:
                return tmp
        else:
            # print "Get Value RowTable", row, col
            return None

    ### GRID METHOD
    def GetColLabelValue(self, col):
        """Return the column label"""
        if col >= self.fix_col and col not in self.sc:
            name = ""
        else:
            name = " %s " % self.fields[col][0]
        direct = '  '
        if col == self.sortP[0]:
            if self.sortP[1]:
                direct = SYM.SYM_ARRTOP
            else:
                direct = SYM.SYM_ARRBOT
        return name + direct

    def notify_change(self):
        self.parent.updateDataInfo()
        self.parent.recomputeAll()
        
    def resetData(self, data=None, srids=None):
        if data is not None:
            self.data = data
        else:
            self.data = ICList()

        if srids is not None:
            self.sortids = srids
        else:
            self.sortids = ICList([idi for idi in range(len(self.data))], True)
        self.sortP = (None, False)
        self.redraw()

    def resetDetails(self, details={}, review=True):
        self.sortP = (None, False)
        self.details = details
        if review:
            self.redraw()

    def redraw(self, details={}, review=True):
        crow, ccol = self.GetView().GetGridCursorRow(), self.GetView().GetGridCursorCol()
        self.ResetView()
        self.GetView().SetColMinimalAcceptableWidth(8)
        #self.GetView().SetRowMinimalAcceptableHeight(5)
        self.GetView().SetDefaultColSize(8, True)
        #self.GetView().SetDefaultRowSize(1, True)
        self.GetView().SetColSize(0, self.width_colcheck)
        self.GetView().SetColSize(1, self.width_colid)
        for i in range(2, self.fix_col):
            # details = {"aim": "list"}
            # details.update(self.details)
            # sz = max([len("%s" % self.getFieldV(sid, self.fields[i], details)) for sid in self.sortids])
            self.GetView().SetColSize(i, self.width_colname) #10*(sz+2))
        for cid in self.sc:
            pls = 2
            if cid == self.sortP[0]:
                pls = 4
            self.GetView().SetColSize(cid, 10*(len(self.fields[cid][0])+pls))
#         self.GetView().SetRowSize(self.getSelectedRow(), 10)
# #            self.GetView().SetColSize(cid, wx.DC().GetTextExtent(self.fields[cid][0]))
#        self.GetView().DisableDragColSize()
        self.GetView().DisableDragRowSize()
        self.GetView().SetGridCursor(crow,ccol)

    def setFocus(self, event):
        self.flipFocusCol(event.GetCol())

    def flipFocusCol(self, cid):
        if cid >= self.fix_col:
            if cid in self.sc:
                self.sc.remove(cid)
            else:
                self.sc.add(cid)
            self.redraw()
        if self.getSelectedRow() is not None:
            row = self.getSelectedRow()
        else:
            row = 0
        if not self.grid.IsVisible(row, cid):
            self.grid.MakeCellVisible(row, cid)

    def setFocusCol(self, cid):
        if cid >= self.fix_col:
            if cid not in self.sc:
                self.sc.add(cid)
            self.redraw()

    def delFocusCol(self, cid):
        if cid >= self.fix_col:
            if cid in self.sc:
                self.sc.remove(cid)
            self.redraw()

    def showCol(self, side, col):
        if (side, col) in self.cols_map and self.cols_map[(side, col)] not in self.sc:
            self.sc.add(self.cols_map[(side, col)])
            self.redraw()
            self.grid.MakeCellVisible(self.getSelectedRow(), self.cols_map[(side, col)])

    def showRidRed(self, rid, red=None):
        row = self.getRowForItem(rid)
        if row is not None:
            self.setSelectedRow(row)
            if isinstance(red, Redescription):
                for side in [0,1]:
                    for l in red.queries[side].listLiterals():
                        self.sc.add(self.cols_map[(side, l.colId())])
            elif isinstance(red, ColM):
                self.sc.add(self.cols_map[(red.getSide(), red.getId())])
            self.redraw()
        return row

    def setSort(self, event):
        self.setFocusCol(event.GetCol())
        GridTable.setSort(self, event)
        
    def resetSizes(self):
        pass
