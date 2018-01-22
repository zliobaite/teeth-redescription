import sys, os.path
import wx
import wx.lib.mixins.listctrl  as  listmix
from ..reremi.classQuery import SYM, Literal, Query
from ..reremi.classRedescription import Redescription
from ..reremi.classBatch import Batch
from ..reremi.classData import Data

import pdb

LIST_TYPES_NAMES = ['file', 'run', 'manual', 'history']
LIST_TYPES_ICONS = [wx.ART_REPORT_VIEW, wx.ART_EXECUTABLE_FILE, wx.ART_LIST_VIEW, wx.ART_LIST_VIEW]

def makeContainersIL(icons):
    size_side = 16
    il = wx.ImageList(size_side, size_side)
    for (i, icon) in enumerate(icons): 
        il.Add(wx.ArtProvider.GetBitmap(icon, wx.ART_FRAME_ICON, (size_side, size_side)))
    return il

###### DRAG AND DROP UTILITY
class ListDrop(wx.PyDropTarget):
    """ Drop target for simple lists. """

    def __init__(self, setFn):
        """ Arguments:
         - setFn: Function to call on drop.
        """
        wx.PyDropTarget.__init__(self)

        self.setFn = setFn

        # specify the type of data we will accept
        self.data = wx.PyTextDataObject()
        self.SetDataObject(self.data)

    # Called when OnDrop returns True.  We need to get the data and
    # do something with it.
    def OnData(self, x, y, d):
        # copy the data from the drag source to our data object
        if self.GetData():
            self.setFn(x, y, self.data.GetText())

        # what is returned signals the source what to do
        # with the original data (move, copy, etc.)  In this
        # case we just return the suggested value given to us.
        return d


#----------------------------------------------------------------------------
#----------------------------------------------------------------------------
from bisect import bisect


class MyTextEditMixin:
    """    
    A mixin class that enables any text in any column of a
    multi-column listctrl to be edited by clicking on the given row
    and column.  You close the text editor by hitting the ENTER key or
    clicking somewhere else on the listctrl. You switch to the next
    column by hiting TAB.

    To use the mixin you have to include it in the class definition
    and call the __init__ function::

        class TestListCtrl(wx.ListCtrl, TextEditMixin):
            def __init__(self, parent, ID, pos=wx.DefaultPosition,
                         size=wx.DefaultSize, style=0):
                wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
                TextEditMixin.__init__(self) 


    Authors:     Steve Zatz, Pim Van Heuven (pim@think-wize.com)
    """

    editorBgColour = wx.Colour(255,255,175) # Yellow
    editorFgColour = wx.Colour(0,0,0)       # black
        
    def __init__(self):
        #editor = wx.TextCtrl(self, -1, pos=(-1,-1), size=(-1,-1),
        #                     style=wx.TE_PROCESS_ENTER|wx.TE_PROCESS_TAB \
        #                     |wx.TE_RICH2)

        self.make_editor()
        self.Bind(wx.EVT_TEXT_ENTER, self.CloseEditor)
        # self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self)


    def make_editor(self, col_style=wx.LIST_FORMAT_LEFT):
        
        style =wx.TE_PROCESS_ENTER|wx.TE_PROCESS_TAB|wx.TE_RICH2
        style |= {wx.LIST_FORMAT_LEFT: wx.TE_LEFT,
                  wx.LIST_FORMAT_RIGHT: wx.TE_RIGHT,
                  wx.LIST_FORMAT_CENTRE : wx.TE_CENTRE
                  }[col_style]
        
        editor = wx.TextCtrl(self, -1, style=style)
        editor.SetBackgroundColour(self.editorBgColour)
        editor.SetForegroundColour(self.editorFgColour)
        font = self.GetFont()
        editor.SetFont(font)

        self.curRow = 0
        self.curCol = 0

        editor.Hide()
        if hasattr(self, 'editor'):
            self.editor.Destroy()
        self.editor = editor

        self.col_style = col_style
        self.editor.Bind(wx.EVT_CHAR, self.OnChar)
        self.editor.Bind(wx.EVT_KILL_FOCUS, self.CloseEditor)
        
        
    def OnItemSelected(self, evt):
        self.curRow = evt.GetIndex()
        evt.Skip()
        

    def OnChar(self, event):
        ''' Catch the TAB, Shift-TAB, cursor DOWN/UP key code
            so we can open the editor at the next column (if any).'''

        keycode = event.GetKeyCode()
        if keycode == wx.WXK_TAB and event.ShiftDown():
            self.CloseEditor()
            if self.curCol-1 >= 0:
                self.OpenEditor(self.curCol-1, self.curRow)
            
        elif keycode == wx.WXK_TAB:
            self.CloseEditor()
            if self.curCol+1 < self.GetColumnCount():
                self.OpenEditor(self.curCol+1, self.curRow)

        elif keycode == wx.WXK_ESCAPE:
            self.CloseEditor()

        elif keycode == wx.WXK_DOWN:
            self.CloseEditor()
            if self.curRow+1 < self.GetItemCount():
                self._SelectIndex(self.curRow+1)
                self.OpenEditor(self.curCol, self.curRow)

        elif keycode == wx.WXK_UP:
            self.CloseEditor()
            if self.curRow > 0:
                self._SelectIndex(self.curRow-1)
                self.OpenEditor(self.curCol, self.curRow)
            
        else:
            event.Skip()

    
    def OnLeftDown(self, evt=None):
        ''' Examine the click and double
        click events to see if a row has been click on twice. If so,
        determine the current row and columnn and open the editor.'''
        if self.editor.IsShown():
            self.CloseEditor()
            
        x,y = evt.GetPosition()
        row,flags = self.HitTest((x,y))
    
        if row != self.curRow: # self.curRow keeps track of the current row
            evt.Skip()
            return
        
        # the following should really be done in the mixin's init but
        # the wx.ListCtrl demo creates the columns after creating the
        # ListCtrl (generally not a good idea) on the other hand,
        # doing this here handles adjustable column widths
        
        self.col_locs = [0]
        loc = 0
        for n in range(self.GetColumnCount()):
            loc = loc + self.GetColumnWidth(n)
            self.col_locs.append(loc)

        
        col = bisect(self.col_locs, x+self.GetScrollPos(wx.HORIZONTAL)) - 1
        self.OpenEditor(col, row)


    def OpenEditor(self, col, row):
        ''' Opens an editor at the current position. '''

        # give the derived class a chance to Allow/Veto this edit.
        evt = wx.ListEvent(wx.wxEVT_COMMAND_LIST_BEGIN_LABEL_EDIT, self.GetId())
        evt.m_itemIndex = row
        evt.m_col = col
        item = self.GetItem(row, col)
        evt.m_item.SetId(item.GetId()) 
        evt.m_item.SetColumn(item.GetColumn()) 
        evt.m_item.SetData(item.GetData()) 
        evt.m_item.SetText(item.GetText()) 
        ret = self.GetEventHandler().ProcessEvent(evt)
        if ret and not evt.IsAllowed():
            return   # user code doesn't allow the edit.

        if self.GetColumn(col).m_format != self.col_style:
            self.make_editor(self.GetColumn(col).m_format)
    
        x0 = self.col_locs[col]
        x1 = self.col_locs[col+1] - x0

        scrolloffset = self.GetScrollPos(wx.HORIZONTAL)

        # scroll forward
        if x0+x1-scrolloffset > self.GetSize()[0]:
            if wx.Platform == "__WXMSW__":
                # don't start scrolling unless we really need to
                offset = x0+x1-self.GetSize()[0]-scrolloffset
                # scroll a bit more than what is minimum required
                # so we don't have to scroll everytime the user presses TAB
                # which is very tireing to the eye
                addoffset = self.GetSize()[0]/4
                # but be careful at the end of the list
                if addoffset + scrolloffset < self.GetSize()[0]:
                    offset += addoffset

                self.ScrollList(offset, 0)
                scrolloffset = self.GetScrollPos(wx.HORIZONTAL)
            else:
                # Since we can not programmatically scroll the ListCtrl
                # close the editor so the user can scroll and open the editor
                # again
                self.editor.SetValue(self.GetItem(row, col).GetText())
                self.curRow = row
                self.curCol = col
                self.CloseEditor()
                return

        y0 = self.GetItemRect(row)[1]
        
        editor = self.editor
        editor.SetDimensions(x0-scrolloffset,y0, x1,-1)
        
        editor.SetValue(self.getDataHdl().getList(self.getDataHdl().getLidAtPos(item.GetId())).getName()) 
        editor.Show()
        editor.Raise()
        editor.SetSelection(-1,-1)
        editor.SetFocus()
    
        self.curRow = row
        self.curCol = col

    
    # FIXME: this function is usually called twice - second time because
    # it is binded to wx.EVT_KILL_FOCUS. Can it be avoided? (MW)
    def CloseEditor(self, evt=None):
        ''' Close the editor and save the new value to the ListCtrl. '''
        if not self.editor.IsShown():
            return
        text = self.editor.GetValue()
        self.editor.Hide()
        self.SetFocus()
        
        # post wxEVT_COMMAND_LIST_END_LABEL_EDIT
        # Event can be vetoed. It doesn't has SetEditCanceled(), what would 
        # require passing extra argument to CloseEditor() 
        evt = wx.ListEvent(wx.wxEVT_COMMAND_LIST_END_LABEL_EDIT, self.GetId())
        evt.m_itemIndex = self.curRow
        evt.m_col = self.curCol
        item = self.GetItem(self.curRow, self.curCol)
        evt.m_item.SetId(item.GetId()) 
        evt.m_item.SetColumn(item.GetColumn()) 
        evt.m_item.SetData(item.GetData()) 
        evt.m_item.SetText(text) #should be empty string if editor was canceled
        ret = self.GetEventHandler().ProcessEvent(evt)
        if not ret or evt.IsAllowed():
            self.getDataHdl().getList(self.getDataHdl().getLidAtPos(item.GetId())).setName(text)
            # if self.IsVirtual():
            #     # replace by whather you use to populate the virtual ListCtrl
            #     # data source
            #     self.SetVirtualData(self.curRow, self.curCol, text)
            # else:
            #     self.SetStringItem(self.curRow, self.curCol, text)
        self.RefreshItem(self.curRow)

    def _SelectIndex(self, row):
        listlen = self.GetItemCount()
        if row < 0 and not listlen:
            return
        if row > (listlen-1):
            row = listlen -1
            
        self.SetItemState(self.curRow, ~wx.LIST_STATE_SELECTED,
                          wx.LIST_STATE_SELECTED)
        self.EnsureVisible(row)
        self.SetItemState(row, wx.LIST_STATE_SELECTED,
                          wx.LIST_STATE_SELECTED)



#----------------------------------------------------------------------------
#----------------------------------------------------------------------------


class ListCtrlBasis(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    type_lc = "-"

    def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition,
                     size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        self.parent = parent
        self.cm = None
        self.pid = None
        self.upOn = True
        self.InsertColumn(0, '')
        dt = ListDrop(self._dd)
        self.SetDropTarget(dt)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnRightClick)
        # self.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.OnFoc)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftClick)

    def OnLeftClick(self, event):
        self.getCManager().makeMainMenu()
        
    def OnRightClick(self, event):
        if self.hasCManager():
            self.getViewHdl().markFocus(self)
            self.getCManager().makePopupMenu()

    def getTypeL(self):
        return self.type_lc
    def isItemsL(self):
        return False
    def isContainersL(self):
        return False

    def setCManager(self, cm, pid=None):
        self.cm = cm
        self.pid = pid
    def getCManager(self):
        return self.cm
    def getDataHdl(self):
        if self.hasCManager():
            return self.cm.getDataHdl()
    def getViewHdl(self):
        if self.hasCManager():
            return self.cm.getViewHdl()

    def hasCManager(self):
        return self.cm is not None
    def getPid(self):
        return self.pid

    def turnUp(self, val):
        self.upOn = val
    def isUp(self):
        return self.upOn

    def getAssociated(self, which):
        if self.hasCManager():
            return self.getCManager().getAssociated(self.getPid(), which)
        return None

    # def OnKeyDown(self, event):
    #     pass
        # print event.GetKeyCode(), event.GetModifiers()
        # if event.GetKeyCode() in [wx.WXK_LEFT, wx.WXK_RIGHT]:
        #     print "navigate"
        #     # self.listm.jumpToNextLC(self)
    
    # def OnDeSelect(self, event):
    #     index = event.GetIndex()
    #     self.SetItemBackgroundColour(index, 'WHITE')

    # def OnFocus(self, event):
    #     self.SetItemBackgroundColour(0, wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DHIGHLIGHT))

    def _onInsert(self, event):
        # Sequencing on a drop event is:
        # wx.EVT_LIST_ITEM_SELECTED
        # wx.EVT_LIST_BEGIN_DRAG
        # wx.EVT_LEFT_UP
        # wx.EVT_LIST_ITEM_SELECTED (at the new index)
        # wx.EVT_LIST_INSERT_ITEM
        #--------------------------------
        # this call to onStripe catches any addition to the list; drag or not
        if self.hasCManager():
            self._onStripe()
            # self.getCManager().setIndices(self.getPid(), "drag", -1)
            event.Skip()

    def _onDelete(self, event):
        if self.hasCManager():
            self._onStripe()
            event.Skip()

    def getFirstSelection(self):
        return self.GetFirstSelected()
    def getSelection(self):
        l = []
        idx = -1
        while True: # find all the selected items and put them in a list
            idx = self.GetNextItem(idx, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if idx == -1:
                break
            l.append(idx)
        return l
    def getNbSelected(self):
        return self.GetSelectedItemCount()
    def setFocusRow(self, row):
        self.Focus(row)
    def setFoundRow(self, row):
        self.Focus(row)
        # #self.SetItemBackgroundColour(0, wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOWTEXT))
        # if self.IsSelected(row):
        #     self.SetItemTextColour(row, wx.Colour(0,222,222))
        # else:
        self.SetItemTextColour(row, wx.Colour(139,0,0))
    def setUnfoundRow(self, row):
        self.SetItemTextColour(row, wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOWTEXT))


    def clearSelection(self):
        sels = self.getSelection()
        for sel in sels:
            self.Select(sel, on=0)
        return sels
    def setSelection(self, sels):
        self.clearSelection()
        for sel in sels:
            self.Select(sel, on=1)

    def _startDrag(self, e):
        """ Put together a data object for drag-and-drop _from_ this list. """
        # Create the data object: Just use plain text.
        if self.hasCManager():
            txt = ",".join(map(str, self.getSelection()))
            data = wx.PyTextDataObject()
            data.SetText(txt)

            ### single item select
            # idx = e.GetIndex()
            # data.SetText("%s" % idx)

            # Create drop source and begin drag-and-drop.
            dropSource = wx.DropSource(self)
            dropSource.SetData(data)
            res = dropSource.DoDragDrop(flags=wx.Drag_DefaultMove)

    def _dd(self, x, y, text): ## drag release
        # Find insertion point.
        if self.hasCManager():
            trg_where = {"index": None, "after": False}
            index, flags = self.HitTest((x, y))
            if index == wx.NOT_FOUND: ### if not found move to end
                trg_where["index"] = -1
            else:
                trg_where["index"] = index
                # Get bounding rectangle for the item the user is dropping over.
                rect = self.GetItemRect(index)
                # If the user is dropping into the lower half of the rect, we want to insert _after_ this item.
                if y > (rect.y - rect.height/2.):
                    trg_where["after"] = True
            self.getCManager().manageDrag(self, trg_where, text)

    def _onStripe(self):
        if self.GetItemCount()>0:
            for x in range(self.GetItemCount()):
                if x % 2==0:
                    self.SetItemBackgroundColour(x,wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DLIGHT))
                else:
                    self.SetItemBackgroundColour(x,wx.WHITE)

    def GetNumberRows(self):
        return self.GetItemCount()
    def GetNumberCols(self):
        return self.GetColumnCount()
        

class ListCtrlContainers(ListCtrlBasis, MyTextEditMixin):
    type_lc = "containers" 
    list_width = 150
    
    def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize):
        ListCtrlBasis.__init__(self, parent, ID, pos, size,
                               style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_NO_HEADER | wx.LC_SINGLE_SEL)
        MyTextEditMixin.__init__(self)
        self.InsertColumn(0, '')
        self.SetColumnWidth(0, self.list_width)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._onSelect)
        self.AssignImageList(makeContainersIL(LIST_TYPES_ICONS), wx.IMAGE_LIST_SMALL)
        # self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        
    def isContainersL(self):
        return True

    def setCManager(self, cm, pid=None):
        ListCtrlBasis.setCManager(self, cm, pid)

    def RefreshItem(self, row):
        llid = self.getDataHdl().getLidAtPos(row)        
        self.upItem(row, llid)
        
    def upItem(self, i, llid):
        self.SetStringItem(i, 0, self.getDataHdl().getList(llid).getShortStr())
        self.SetItemImage(i, self.getDataHdl().getList(llid).getSrcTypId())

    def loadData(self, lid=None, cascade=True):
        if self.GetItemCount() > 0:
            self.DeleteAllItems()
        if self.getPid() is not None:
            for (i, llid) in enumerate(self.getDataHdl().getOrdLists()):
                self.InsertStringItem(i, "")
                self.upItem(i, llid)
                if llid == lid:
                    if not cascade:
                        self.turnUp(False)
                    self.Select(i)
                    if not cascade:
                        self.turnUp(True)

        # if lid is None and cascade:
        #     ll = self.getAssociated("items")
        #     ll.loadData(lid)

    def _onSelect(self, event):
        if self.isUp():
            self.getViewHdl().setLid(self.getPid(), lid=None, pos=event.GetIndex())
        event.Skip()

    def _onStripe(self):
        pass


class ListCtrlItems(ListCtrlBasis, listmix.CheckListCtrlMixin):
    type_lc = "items" 
        
    def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize):
        ListCtrlBasis.__init__(self, parent, ID, pos, size,
                               style=wx.LC_REPORT | wx.LC_HRULES) # | wx.LC_NO_HEADER)
        listmix.CheckListCtrlMixin.__init__(self)
        
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self._startDrag)        
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self._startDrag)        
        self.Bind(wx.EVT_LIST_INSERT_ITEM, self._onInsert)
        self.Bind(wx.EVT_LIST_DELETE_ITEM, self._onDelete)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        self.Bind(wx.EVT_LIST_COL_CLICK, self.OnColClick)
        self.upck = True

    def OnItemActivated(self, event):
        if self.hasCManager():
            ll = self.getDataHdl().getList(self.getViewHdl().getLid())
            return self.cm.onItemActivated(ll, event.GetIndex())
        
    def isItemsL(self):
        return True

    def getNbCols(self):
        return self.getDataHdl().getNbFields()
    def getColsInfo(self, lid=None, cs=None, refresh=False):
        return self.getDataHdl().getColsInfo(lid, cs, refresh)
    def getItemForIid(self, iid):
        try:
            return self.getDataHdl().getItemForIid(iid)
        except KeyError:
            return None
    ##def getItemForPos(self, pos):
    ##    try:
    ##        return self.getDataHdl().getItemForPos(pos) ### implement
    ##    except KeyError:
    ##        return None

    def getIidItemForPos(self, pos):
        iid = self.getIidAtPos(pos)
        if iid is not None:
            return (iid, self.getDataHdl().getItemForIid(iid))
        return None

    def getItemData(self, iid, pos):
        return self.getDataHdl().getItemData(iid, pos)

    def setCManager(self, cm, pid=None):
        self.cm = cm
        self.pid = pid

    def RefreshItem(self, row):
        ll = self.getDataHdl().getList(self.getViewHdl().getLid())
        self.loadItem(ll, row)

    def OnCheckItem(self, index, flag):
        #### set disabled on item
        if self.upck:
            lid = self.getAssociated("lid")
            self.getDataHdl().checkItem(lid, index, flag)
            self.setBckColor(index, flag)
            self.getDataHdl().notify_change()

    def upItem(self, i, rdt):
        for (cid, cv) in enumerate(rdt["cols"]):
            self.SetStringItem(i, cid, cv)
        if "checked" in rdt:
            self.upck = False
            self.CheckItem(i, rdt["checked"])
            self.setBckColor(i, rdt["checked"])
            self.upck = True

    def setBckColor(self, i, checked=False):
        if checked:
            self.SetItemTextColour(i, wx.SystemSettings_GetColour( wx.SYS_COLOUR_WINDOWTEXT ))
        else:
            self.SetItemTextColour(i, wx.SystemSettings_GetColour( wx.SYS_COLOUR_GRAYTEXT ))

    def updateColsTitles(self, lid):
        for cid, col in enumerate(self.getColsInfo(lid)):
            tmp = self.GetColumn(cid)
            tmp.SetText(col["title"])
            self.SetColumn(cid, tmp)

    def loadData(self, lid=None, refresh=True):
        if self.GetItemCount() > 0:
            self.DeleteAllItems()
        if lid is None:
            return
        ### check nb cols match
        if refresh or self.getNbCols() != self.GetColumnCount():
            self.DeleteAllColumns()
            for cid, col in enumerate(self.getColsInfo(lid, refresh=refresh)):
                self.InsertColumn(cid, col["title"], format=col["format"], width=col["width"])
        else:
            self.updateColsTitles(lid)
        ll = self.getDataHdl().getList(lid)
        if ll is not None:
            # for item in ll.getItems():
            #     print item.status, item
            for i in range(len(ll)):
                self.InsertStringItem(i, "")
                self.loadItem(ll, i)

    def loadItem(self, ll, i):
        pap = self.IsSelected(i)
        rdt = ll.getItemDataAtPos(i)
        self.upItem(i, rdt)
        self.Select(i, pap)

    def OnColClick(self, event):
        colS = event.GetColumn()
        if colS == -1:
            event.Skip()
        else:
            lid = self.getAssociated("lid")
            ll = self.getDataHdl().getList(lid)
            (oldC, newC) = ll.setSort(colS)
            if oldC is not None or newC is not None:
                self.updateColsTitles(lid)
            new_poss = ll.updateSort(self.getSelection())
            if new_poss is not None:
                self.loadData(lid, refresh=False)
                for pos in new_poss:
                    self.Select(pos)

class SplitBrowser:

    def __init__(self, parent, pid, frame):
        self.parent = parent
        self.pid = pid
        self.active_lid = None
        self.cm = None
        self.last_foc = None

        self.sw = wx.SplitterWindow(frame, -1, style=wx.SP_LIVE_UPDATE) #|wx.SP_NOBORDER)
        panelL = wx.Panel(self.sw, -1)
        panelR = wx.Panel(self.sw, -1)
        
        self.lcc = ListCtrlContainers(panelL, -1)
        self.lci = ListCtrlItems(panelR, -1)

        vbox1 = wx.BoxSizer(wx.HORIZONTAL)
        vbox1.Add(self.lcc, 1, wx.EXPAND)
        panelL.SetSizer(vbox1)
        vbox1 = wx.BoxSizer(wx.HORIZONTAL)
        vbox1.Add(self.lci, 1, wx.EXPAND)
        panelR.SetSizer(vbox1)
        
        self.sw.SplitVertically(panelL, panelR, self.lcc.list_width)
        self.sw.SetSashGravity(0.)
        self.sw.SetMinimumPaneSize(1)

        ### WITHOUT SPLITTER
        # panel = wx.Panel(frame, wx.NewId())

        # list1 = ListCtrlContainers(panel, -1)
        # list2 = ListCtrlItems(panel, -1)
        
        # vbox1 = wx.BoxSizer(wx.HORIZONTAL)
        # vbox1.Add(list1, 1, wx.EXPAND)
        # vbox1.Add(list2, 1, wx.EXPAND)
        # panel.SetSizer(vbox1)
        # self.sw = panel

    def getSW(self):
        return self.sw
    def getCM(self):
        return self.cm
    def getDataHdl(self):
        if self.cm is not None:
            return self.cm.getDataHdl()
        return None
    def getLid(self):
        return self.active_lid
    def getLCC(self):
        return self.lcc
    def getLCI(self):
        return self.lci
    def getPid(self):
        return self.pid

    def getWhich(self, which):
        if which == "items":
            return self.lci
        if which == "containers":
            return self.lcc
        if which == "pid":
            return self.pid
        if which == "lid":
            return self.active_lid
    def getFocused(self):
        ff = self.sw.FindFocus()
        if ff is not None:
            return ff
        return self.last_foc
    def getFocusedL(self):
        ret = None
        ff = self.sw.FindFocus()
        if ff is not None and (ff == self.lci or ff == self.lcc):
            ret = ff
        elif (self.last_foc == self.lci or self.last_foc == self.lcc):
            ret = self.last_foc
        return ret

    def markFocus(self, foc=None):
        if foc is not None:
            self.last_foc = foc
        else:
            self.last_foc = self.sw.FindFocus()

    def GetNumberRowsItems(self):
        return self.lci.GetNumberRows()
    def GetNumberRowsContainers(self):
        return self.lcc.GetNumberRows()
    def GetNumberColsItems(self):
        return self.lci.GetNumberCols()
    def GetNumberColsContainers(self):
        return self.lcc.GetNumberCols()
    def GetNumberRowsFocused(self):
        ll = self.getFocusedL()
        if ll is not None:
            return ll.GetNumberRows()
        return 0
    def GetNumberColsFocused(self):
        ll = self.getFocusedL()
        if ll is not None:
            return ll.GetNumberCols()
        return 0
    def GetNumberRows(self):
        return self.GetNumberRowsFocused()
    def GetNumberCols(self):
        return self.GetNumberColsFocused()
    def nbItems(self):
        return self.lci.GetNumberRows()
    def nbLists(self):
        return self.lcc.GetNumberRows()

    def nbSelectedItems(self):
        return self.lci.getNbSelected()
    def nbSelectedLists(self):
        return self.lcc.getNbSelected()
    def nbSelectedFocused(self):
        ll = self.getFocusedL()
        if ll is not None:
            return ll.getNbSelected()
        return 0
    def nbSelected(self):
        return self.nbSelectedFocused()

    def Hide(self):
        self.getSW().Hide()

    def Show(self):
        self.getSW().Show()

    def resetCM(self, cm=None):
        self.cm = cm
        if cm is not None:
            self.lcc.setCManager(cm, self.pid)
            self.lci.setCManager(cm, self.pid)
            if len(self.getDataHdl().getOrdLists()) > 0:
                self.active_lid = self.getDataHdl().getOrdLists()[0]
                self.lcc.loadData(self.active_lid)

    def refresh(self, cascade=True):
        self.lcc.loadData(self.active_lid, cascade)
        if len(self.getDataHdl().getOrdLists()) == 0:
            self.lci.loadData(None)

    def updateLid(self, lid):
        if lid != self.active_lid: # check validity lid 
            self.active_lid = lid
            self.refresh()

    def setLid(self, pid=0, lid=None, pos=None):
        if lid is not None:
            self.active_lid = lid
            self.lcc.setFocusRow(self.getDataHdl().getListPosForId(lid))
        elif pos is not None:
            lid = self.getDataHdl().getListIdAtPos(pos)
            self.active_lid = lid
            self.lci.loadData(lid)

    def setSelectedItem(self, iid):
        pos = self.getDataHdl().getList(self.getLid()).getPosForIid(iid)
        self.lci.setFocusRow(pos)


        
class RefsList:
    list_types_map = dict([(v,k) for (k,v) in enumerate(LIST_TYPES_NAMES)])

    @classmethod
    def getDefaultSrc(tcl):
        return ('manual', None)
    @classmethod
    def getHistSrc(tcl):
        return ('history', None)
    @classmethod
    def getPackSrc(tcl):
        return ('file', 0)
    @classmethod
    def makeSrc(tcl, src=None):
        if src is None:
            return RefsList.getDefaultSrc()
        elif src == "pack":
            return RefsList.getPackSrc()
        elif src == "hist":
            return RefsList.getHistSrc()
        return src

    def makeName(self):
        self.name = "L#%d" % self.id
        if self.src[0] == 'run':
            self.name = "%s#%s" % (self.src[1][1].title(), self.src[1][0])
        elif self.src[0] == 'history':
            self.name = "Hist"
        elif self.src[0] == 'file':
            self.name = "//"
            if self.src[1] == 0:
                self.name += "Package"
            elif self.src[1] is not None and os.path.exists(self.src[1]):
                self.name += os.path.basename(self.src[1])

    def __init__(self, parent, id, src=None, name=None, iids=[]):        
        self.id = id
        self.src = RefsList.makeSrc(src)
        self.parent = parent
        self.sortids = list(iids)
        self.sortP = (None, False)
        if name is None:
            self.makeName()
        else:
            self.name = name
        self.isChanged = False
        
    def getSrc(self):
        return self.src
    def getSrcTyp(self):
        return self.src[0]
    def getSrcTypId(self):
        return RefsList.list_types_map[self.src[0]]
    def getSrcInfo(self):
        return self.src[1]
    def getSrcPath(self):
        if self.src[0] == 'file' and not type(self.src[1]) is int and os.path.exists(self.src[1]):
            return self.src[1]
        else:
            return None
    def hasSrcPath(self):
        return self.src[0] == 'file' and not type(self.src[1]) is int and os.path.exists(self.src[1])

    def setSrc(self, src_typ, src_info=None):
        self.src = (src_typ, src_info)
        self.makeName()

    def getSortInfo(self):
        direct = '  '
        if self.sortP[0] is not None:
            if self.sortP[1]:
                direct = SYM.SYM_ARRTOP
            else:
                direct = SYM.SYM_ARRBOT
        return (self.sortP[0], direct)

    def setSort(self, colS=None):
        old = self.sortP[0]
        if colS is not None:
            if self.sortP[0] == colS:
                self.sortP = (self.sortP[0], not self.sortP[1])
            else:
                self.sortP = (colS, False)
        else:
            self.sortP = (None, False)
        return (old, colS)

    def updateSort(self, poss=None):
        idxs = []
        if poss is not None:
            idxs = set([self.getIidAtPos(pos) for pos in poss])

        if self.sortP[0] is not None:
            tmp = [(x, self.parent.getItemFieldV(x, self.parent.fields[self.sortP[0]], {"aim": "sort", "id": x})) for x in self.sortids]
            self.sortids.sort(key= lambda x:
                              self.parent.getItemFieldV(x, self.parent.fields[self.sortP[0]], {"aim": "sort", "id": x}),
                              reverse=self.sortP[1])
            new_poss = []
            if len(idxs) > 0:
                new_poss = [pos for (pos, idx) in enumerate(self.sortids) if idx in idxs] 
            return new_poss
        return None
    
    def setIids(self, iids):
        self.sortids = list(iids)    
        self.isChanged = True
    def insertIid(self, iid, pos=-1):
        if pos == -1:
            pos = len(self.sortids)
        self.sortids.insert(pos, iid)
        self.isChanged = True
        self.setSort()
    def insertIids(self, iids, pos=-1):
        if pos == -1:
            pos = len(self.sortids)
        for p in iids[::-1]:
            self.sortids.insert(pos, p)
        self.isChanged = True
        self.setSort()
        
    def getIids(self):
        return list(self.sortids)

    def getItemDataAtPos(self, pos):
        rid = self.getIidAtPos(pos)
        return self.parent.getItemData(rid, pos)

    def containsIid(self, idx):
        return idx in self.sortids
    def getPosForIid(self, idx):
        try:
            return self.sortids.index(idx)
        except ValueError: #### is not there...
            return None

    def getIidAtPos(self, pos):
        try:
            return self.sortids[pos]
        except IndexError:
            return None
    def getIidsAtPoss(self, poss=None):
        if poss is None:
            return list(self.sortids)
        else:
            return [self.getIidAtPos(p) for p in poss]
    def getIidsAfterPos(self, pos=None):
        if pos is None:
            return list(self.sortids)
        else:
            return list(self.sortids[pos:])
    def getVIidsAtPoss(self, poss=None):
        return [l for l in self.getIidsAtPoss(poss) if l is not None]

    def getName(self):
        return self.name
    def setName(self, text):
        self.name = text
    def getShortStr(self):
        return "(%d%s) %s" % (len(self.sortids), "*"*(1*self.isChanged), self.getName())
    def nbItems(self):
        return len(self.sortids)

    def __len__(self):
        return len(self.sortids)
    def __str__(self):
        return "%s (%d)" % (self.getName(), len(self.sortids))

    def deleteItems(self, poss=None):
        if poss is None:
            del_iids = list(self.sortids)
            del self.sortids[:]
        else:
            del_iids = []
            poss = sorted(poss)
            while len(poss) > 0:
                del_iids.append(self.sortids.pop(poss.pop()))
        self.isChanged = True
        return del_iids[::-1]

        # ttd = numpy.ones(len(self.sortids), dtype=int)
        # ttd[[self.sortids[p] for p in poss]] = 0
        # csum = ttd.cumsum()-1
        # self.sortids = [csum[i] for i in self.sortids if ttd[i]==1]
        # for i in range(len(ttd)-1, -1, -1):
        #     if ttd[i] == 0:
        #         self.items.pop(i)


class StaticContent:

    str_item = 'item'
    fields_def = []
    name_m = None
    check_m = None

    #### COLUMN WIDTHS
    width_colcheck = 25
    width_colid = 50
    width_colname = 150
    width_colnamew = 300
    width_colinfo = 80
    width_colinfow = 100
    width_colinfon = 8

    def __init__(self):
        self.details = {}
        self.items = Batch()
        self.nlid = 0
        self.lists = {}
        self.lists_ord = []
        
    def notify_change(self):
        print "Changed"
        
    #### ACCESSING LISTS
    def getListPosForId(self, idx):
        try:
            return self.lists_ord.index(idx)
        except IndexError:
            return None
    def getListIdAtPos(self, pos):
        try:
            return self.lists_ord[pos]
        except IndexError:
            return None
    def getList(self, idx):
        try:
            return self.lists[idx]
        except KeyError:
            return None
    def getListAtPos(self, pos):
        try:
            return self.lists[self.lists_ord[pos]]
        except IndexError:
            return None

    def getOrdLists(self):
        return self.lists_ord
    def getLidForSrc(self, src):
        for lid, llist in self.lists.items():
            if llist.getSrc() == src:
                return lid
        return None

    #### ACCESSING ITEMS
    def getCheckF(self):
        return ('', self.check_m)
    def getNameF(self):
        return ('name', self.name_m)
    def getDataF(self, i):
        if i < len(self.fields):
            return self.fields[i]
        return None

    def getFields(self, lid=None, refresh=False):
        return self.fields
    def getNbFields(self):
        return len(self.fields)
    def getColsInfo(self, lid=None, cs=None, refresh=False):
        infos = [{"title": field[0], "format": field[-1], "width": field[-2]} for field in self.getFields(lid, refresh)]
        if lid is not None:
            sort_info = self.lists[lid].getSortInfo()
            if sort_info[0] is not None:
                infos[sort_info[0]]["title"] += sort_info[1] 
        return infos
    def getItemForIid(self, iid):
        try:
            return self.items.getElement(iid)
        except KeyError:
            return None
    def getItemForIidCopy(self, iid): ### Unnecessary?
        try:
            return self.items.getElement(iid).copy()
        except KeyError:
            return None
    def getAllIids(self):
        return self.items.keys()
    def getIidsForLid(self, lid):
        try:
            self.lists[lid].getIids()
        except KeyError:
            return None
    def getItemsForLid(self, lid, pos=None):
        try:
            return [self.getItemForIid(iid) for iid in self.lists[lid].getIidsAtPoss(poss=pos)] 
        except KeyError:
            return None
    def getItemsMapForLid(self, lid, pos=None):
        try: 
            return [(iid, self.getItemForIid(iid)) for iid in self.lists[lid].getIidsAtPoss(poss=pos)] 
        except KeyError:
            return None

    def getItemData(self, iid, pos):
        details = {"aim": "list", "id": iid, "pos": pos} 
        dt = ["%s" % self.getItemFieldV(iid, field, details) for field in self.getFields()]
        ck = self.getItemFieldV(iid, self.getCheckF(), details)==1
        return {"cols": dt, "checked": ck}
    
    def getItemFieldV(self, iid, field, details):
        if iid is None or field is None:
            return ""
        item = self.getItemForIid(iid)
        methode = eval(field[1])
        if callable(methode):
            if len(field) > 2 and field[2] is not None:
                details.update(field[2])
            details.update(self.details)
            try:
                return methode(details)
            except IndexError:
                methode(details)
        else:
            return methode
    def getListsReferIid(self, iid):
        return [(nlid, ll) for (nlid, ll) in self.lists.items() if ll.containsIid(iid)]
 
    def resetDetails(self, details={}):
        self.resetAllSorts()
        self.details = details

    def resetAllSorts(self):
        for lk, ll in self.lists.items():
            ll.setSort()

    def getLidAtPos(self, pos):
        try:
            return self.lists_ord[pos]
        except KeyError:
            return None
    def getLidsAtPoss(self, poss=None):
        if poss is None:
            return list(self.lists)
        else:
            return [self.getLidAtPos(p) for p in poss]
    def getVLidsAtPoss(self, poss=None):
        return [l for l in self.getLidsAtPoss(poss) if l is not None]
        
    def getNamesList(self, lid):
        """list of queries for search"""
        names_list = []
        details = {"aim": "list"}
        details.update(self.details)
        return [(x, "%s" % self.getItemFieldV(iid, self.getNameF(), details)) for (x, iid) in enumerate(self.getList(lid).getIids())]
        # return [(x, "%s" % self.getItemFieldV(x, self.getNameF(), details)) for x in self.getList(lid).getIids()]


    def checkItem(self, lid, index, check):
        #### enable/disable doesn't cause list to be marked changed
        if lid is not None:
            iid = self.getList(lid).getIidAtPos(index)
            if iid is not None:
                ck = self.getItemFieldV(iid, self.getCheckF(), {})
                if (ck == 1 and not check) or ( ck == 0 and check):
                    self.getItemForIid(iid).flipEnabled()


class EditableContent(StaticContent):

    def __init__(self):
        StaticContent.__init__(self)
        self.buffer = {}

    #### MANIPULATING CONTENT
    def resetLists(self, src=None, items=[], sord=None):
        self.clearLists()
        nlid = self.addList(src, items, sord)
        return nlid

    def addList(self, src=None, items=[], sord=None, name=None):
        src = RefsList.makeSrc(src)
        nlid = self.nlid
        self.nlid += 1

        iids = self.items.extend(items)
        # if sord is not None and len(iids) > 0 and len(sord) == len(iids):
        #     #### CHECK ORDERING 
        #     oiids = iids
        #     niids = [oiids[ii] for ii in sord]
        self.lists[nlid] = RefsList(self, nlid, src, name, iids) 
        self.lists_ord.append(nlid)
        return nlid

    def deleteLists(self, lids=[], sel=None):
        if len(lids) == 0 and sel is not None:
            lids = self.getVLidsAtPoss(sel)
        for lid in lids:
            self.deleteItems(self.lists[lid].getIids())
            del self.lists[lid]
            self.lists_ord.remove(lid)
        def_lid = None
        if len(self.lists_ord) > 0:
            def_lid = self.lists_ord[0]
        return def_lid
    def deleteList(self, lid):
        if lid in self.lists:
            diids = self.lists[lid].deleteItems()
            self.deleteItems(diids)
            self.lists_ord.remove(lid)
            del self.lists[lid]
    def clearLists(self):
        self.lists = {}
        self.items.reset()
        self.lists_ord = []

    def deleteItemsLid(self, lid, sel=None):
        diids = self.lists[lid].deleteItems(sel)
        self.deleteItems(diids)
    def deleteItems(self, diids=None):
        if diids is None:
            diids = self.items.getIds()
        for drid in diids:
            self.items.deleteElement(drid)

    def cutLists(self, lids=[], sel=None):
        if len(lids) == 0 and sel is not None:
            lids = self.getVLidsAtPoss(sel)
        iids = []
        for lid in lids:
            iids.extend(self.lists[lid].deleteItems())
        self.setBuffer(iids, 'cut')
        return iids
    def cutItemsLid(self, lid, sel=None):
        iids = self.lists[lid].deleteItems(sel)
        self.setBuffer(iids, 'cut')
        return iids

    def copyLists(self, lids=[], sel=None):
        if len(lids) == 0 and sel is not None:
            lids = self.getVLidsAtPoss(sel)
        iids = []
        for lid in lids:
            iids.extend(self.lists[lid].getIids())
        self.setBuffer(iids, 'copy')
        return iids
    def copyItemsLid(self, lid, sel=None):
        iids = self.lists[lid].getIidsAtPoss(sel)
        self.setBuffer(iids, 'copy')
        return iids

    def pasteItems(self, lid, pos):
        iids = []
        if "action" in self.buffer and lid in self.lists:
            if self.buffer["action"] == 'copy':
                rcop = [self.getItemForIidCopy(rid) for rid in self.buffer["iids"]]
                iids = self.items.extend(rcop)
            elif self.buffer["action"] == 'cut':
                iids = self.buffer["iids"]
            if len(iids) > 0:
                self.lists[lid].insertIids(iids, pos)
                self.buffer = {}
            else:
                self.clearBuffer()
        return iids

    def isEmptyBuffer(self):
        return len(self.buffer) == 0
    
    def setBuffer(self, iids, action):
        self.clearBuffer()
        self.buffer["iids"] = iids
        self.buffer["action"] = action
        ## print "Buffer:", self.buffer

    def clearBuffer(self):
        if "action" in self.buffer:
            if self.buffer["action"] == "cut":
                self.deleteItems(self.buffer["iids"])
            self.buffer = {}

    def insertItem(self, lid, item, iid=None, pos=-1):
        if iid is None:
            iid = self.items.append(item)
        else:
            iid = self.items.insert(iid, item)
        self.lists[lid].insertIid(iid, pos)
        return iid
    def insertItems(self, lid, items):
        iids = self.items.extend(items)
        self.lists[lid].insertIids(iids)
        return iids

    def moveItems(self, lid, nlid, sel, pos):
        iids = self.lists[lid].deleteItems(sel)
        self.lists[nlid].insertIids(iids, pos)

    def substituteItem(self, iid, item):
        return self.items.substitute(iid, item)


class VarsSet(StaticContent):
    str_var = 'item'
    ###################### FIELDS VARS 
    fields_def = [('',str_var+'.getSortAble', None, StaticContent.width_colcheck, wx.LIST_FORMAT_LEFT), 
                  ('id', str_var+'.getId', None,  StaticContent.width_colid, wx.LIST_FORMAT_LEFT),
                  ('name', str_var+'.getName', None, StaticContent.width_colnamew, wx.LIST_FORMAT_LEFT),
                  ('type', str_var+'.getType', None, StaticContent.width_colinfow, wx.LIST_FORMAT_LEFT)]
    fields_miss = [('missing', str_var+'.getMissInfo', None, StaticContent.width_colinfo, wx.LIST_FORMAT_RIGHT)]
    fields_var = {1: [('density', str_var+'.getDensity', None, StaticContent.width_colinfo, wx.LIST_FORMAT_RIGHT)],
                  2:[('categories', str_var+'.getCategories', None, StaticContent.width_colinfo, wx.LIST_FORMAT_RIGHT)],
                  3:[('min', str_var+'.getMin', None, StaticContent.width_colinfo, wx.LIST_FORMAT_RIGHT),
                     ('max', str_var+'.getMax', None, StaticContent.width_colinfo, wx.LIST_FORMAT_RIGHT)]}

    name_m = str_var+'.getName'
    check_m = str_var+'.getEnabled'

    def __init__(self, parent):
        self.details = {}
        self.items = None
        self.lists = {}
        self.lists_ord = []
        self.parent = parent
        self.resetFields()

    def notify_change(self):
        self.parent.updateDataInfo()
        
    def resetFields(self, side=None):
        self.resetAllSorts()
        self.fields = []
        if self.items is not None:
            self.fields.extend(self.fields_def)
            if self.items.hasMissing():
                self.fields.extend(self.fields_miss)
            for tyid in self.items.getAllTypes(side):
                self.fields.extend(self.fields_var[tyid])

    def resetContent(self, src, content):
        self.items = content
        self.resetFields()

        src = RefsList.makeSrc(src)
        for side in self.items.getSides():
            self.lists[side] = RefsList(self, side, src, "Vars %s" % side, iids=self.items.getIids(side)) 
            self.lists_ord.append(side)
        return side

    def getFields(self, lid=None, refresh=False):
        if refresh:
            self.resetFields(side=lid)
        return self.fields


class RedsSet(EditableContent):
    str_red = 'item'
    ###################### FIELDS REDS
    fields_def_nosplit = [('', str_red+'.getSortAble', None, StaticContent.width_colcheck, wx.LIST_FORMAT_LEFT),
                          ('id', str_red+'.getShortRid', None, StaticContent.width_colid, wx.LIST_FORMAT_LEFT),
                          ('query LHS', str_red+'.getQueryLU', None, StaticContent.width_colnamew, wx.LIST_FORMAT_LEFT),
                          ('query RHS', str_red+'.getQueryRU', None, StaticContent.width_colnamew, wx.LIST_FORMAT_LEFT),
                          ('J', str_red+'.getRoundAcc', None, StaticContent.width_colinfo, wx.LIST_FORMAT_RIGHT),
                          ('p-value', str_red+'.getRoundPVal', None, StaticContent.width_colinfo, wx.LIST_FORMAT_RIGHT),
                          ('|E'+SYM.SYM_GAMMA+'|', str_red+'.getLenI', None, StaticContent.width_colinfo, wx.LIST_FORMAT_RIGHT),
                          ('track', str_red+'.getTrack', None, StaticContent.width_colinfo, wx.LIST_FORMAT_LEFT)]

    fields_def_splits = [('', str_red+'.getSortAble', None, StaticContent.width_colcheck, wx.LIST_FORMAT_LEFT),
                         ('id', str_red+'.getShortRid', None, StaticContent.width_colid, wx.LIST_FORMAT_LEFT),
                         ('query LHS', str_red+'.getQueryLU', None, StaticContent.width_colnamew, wx.LIST_FORMAT_LEFT),
                         ('query RHS', str_red+'.getQueryRU', None, StaticContent.width_colnamew, wx.LIST_FORMAT_LEFT),
                         (SYM.SYM_RATIO+'J', str_red+'.getRoundAccRatio', {"rset_id_num": "test", "rset_id_den": "learn"},
                          StaticContent.width_colinfo, wx.LIST_FORMAT_RIGHT),
                         (SYM.SYM_LEARN+'J', str_red+'.getRoundAcc', {"rset_id": "learn"},
                          StaticContent.width_colinfo, wx.LIST_FORMAT_RIGHT),
                         (SYM.SYM_TEST+'J', str_red+'.getRoundAcc', {"rset_id": "test"},
                          StaticContent.width_colinfo, wx.LIST_FORMAT_RIGHT),
                         (SYM.SYM_LEARN+'pV', str_red+'.getRoundPVal', {"rset_id": "learn"},
                          StaticContent.width_colinfo, wx.LIST_FORMAT_RIGHT),
                         (SYM.SYM_TEST+'pV', str_red+'.getRoundPVal', {"rset_id": "test"},
                          StaticContent.width_colinfo, wx.LIST_FORMAT_RIGHT),
                         (SYM.SYM_LEARN+'|E'+SYM.SYM_GAMMA+'|', str_red+'.getLenI', {"rset_id": "learn"},
                          StaticContent.width_colinfo, wx.LIST_FORMAT_RIGHT),
                         (SYM.SYM_TEST+'|E'+SYM.SYM_GAMMA+'|', str_red+'.getLenI', {"rset_id": "test"},
                          StaticContent.width_colinfo, wx.LIST_FORMAT_RIGHT),
                         ('track', str_red+'.getTrack', None, StaticContent.width_colinfo, wx.LIST_FORMAT_LEFT)]

    fields_def = fields_def_nosplit
    #fields_def = fields_def_splits
    name_m = str_red+'.getQueriesU'
    check_m = str_red+'.getEnabled'

    def __init__(self, parent):
        EditableContent.__init__(self)
        self.parent = parent
        self.resetFields()
        
    def resetFields(self):
        self.resetAllSorts()
        if self.parent.hasDataLoaded() and self.parent.dw.getData().hasLT():
            self.fields = self.fields_def_splits
        else:
            self.fields = self.fields_def_nosplit

    def recomputeAll(self, data):
        for ri, red in self.items.items():
            red.recompute(data)
        if data.hasLT():
            self.fields = self.fields_def_splits
        else:
            self.fields = self.fields_def_nosplit


    def filterToOne(self, compare_ids, parameters):
        disable_ids = self.items.filtertofirstIds(compare_ids, parameters, complement=True)
        self.items.applyFunctTo(".setDisabled()", disable_ids, changes= True)

    def filterAll(self, compare_ids, parameters):
        disable_ids = self.items.filterpairsIds(compare_ids, parameters, complement=True)
        self.items.applyFunctTo(".setDisabled()", disable_ids, changes= True)

    def processAll(self, compare_ids, parameters):
        # current_ids = [i for i in compare_ids if self.items.getItem(i).getEnabled()]
        # bottom_ids = [i for i in compare_ids if not self.items.getItem(i).getEnabled()]
        current_ids = [i for i in compare_ids if self.items[i].getEnabled()]
        bottom_ids = [i for i in compare_ids if not self.items[i].getEnabled()]
        selected_ids = self.items.selected(parameters, current_ids)
        middle_ids = [i for i in current_ids if i not in selected_ids]
        self.items.applyFunctTo(".setDisabled()", middle_ids)
        return selected_ids, middle_ids, bottom_ids


class ContentManager:

    def __init__(self, parent, tabId, frame, short=None):
        self.tabId = tabId
        self.parent = parent
        self.matching = []
        self.curr_match = None
        self.prev_sels = None
        self.initData(parent)
        self.initBrowsers(frame)

    def initData(self, parent):
        self.data = EditableContent()
    def initBrowsers(self, frame):
        self.browsers = {0: SplitBrowser(self, 0, frame)}
        self.browsers[0].resetCM(self)

    def getAssociated(self, pid, which):
        if pid in self.browsers:
            return self.browsers[pid].getWhich(which)
        return None


    def getDataHdl(self):
        return self.data
    def getViewHdl(self, pid=0):
        return self.browsers[pid]
    def getSW(self, pid=0):
        return self.browsers[0].getSW()
    def Show(self, pid=0):
        return self.getSW(pid).Show()
    def Hide(self, pid=0):
        return self.getSW(pid).Hide()

    ################## CONTENT MANAGEMENT METHODS
    def addData(self, src=None, data=[], sord=None, focus=True):
        nlid = self.getDataHdl().addList(src=src, items=data, sord=sord)
        if focus:
            self.getViewHdl().updateLid(nlid)
        return nlid

    def resetData(self, src=None, data=[], sord=None):
        self.getDataHdl().clearLists()
        if len(data) > 0 or src is not None:
            return self.addData(src, data, sord)
        return None

    def resetDetails(self, details={}, review=True):
        self.getDataHdl().resetDetails(details)
        if review:
            self.refreshAll()

    def refreshAll(self):
        for bi, brs in self.browsers.items():
            brs.refresh()

    def onNewList(self):
        self.addData(data=[], focus=False)
        self.refreshAll()
        
    def onDeleteAny(self):
        lc = self.getViewHdl().getFocusedL()
        if lc is not None:
            if lc.isItemsL():
                sel = lc.getSelection()
                self.onDeleteItems(lc.getPid(), sel)
            elif lc.isContainersL():
                sel = lc.getSelection()
                self.onDeleteLists(sel)        
    def onDeleteLists(self, sel):
        def_lid = self.getDataHdl().deleteLists(sel=sel)
        for bi, brs in self.browsers.items():
            brs.updateLid(def_lid)
    def onDeleteItems(self, pid, sel):
        lid = self.browsers[pid].getLid()
        self.getDataHdl().deleteItemsLid(lid, sel)
        self.refreshAll()

    def onCutAny(self):
        lc = self.getViewHdl().getFocusedL()
        if lc is not None:
            if lc.isItemsL():
                sel = lc.getSelection()
                self.onCutItems(lc.getPid(), sel)
            elif lc.isContainersL():
                sel = lc.getSelection()
                self.onCutLists(sel)        
    def onCutLists(self, sel):
        iids = self.getDataHdl().cutLists(sel=sel)
        self.refreshAll()
    def onCutItems(self, pid, sel=None):
        lid = self.browsers[pid].getLid()
        iids = self.getDataHdl().cutItemsLid(lid, sel)
        self.refreshAll()

    def onCopyAny(self):
        lc = self.getViewHdl().getFocusedL()
        if lc is not None:
            if lc.isItemsL():
                sel = lc.getSelection()
                self.onCopyItems(lc.getPid(), sel)
            elif lc.isContainersL():
                sel = lc.getSelection()
                self.onCopyLists(sel)
    def onCopyLists(self, sel):
        iids = self.getDataHdl().copyLists(sel=sel)
    def onCopyItems(self, pid, sel=None):
        lid = self.browsers[pid].getLid()
        iids = self.getDataHdl().copyItemsLid(lid, sel)

    def onPasteAny(self):
        lc = self.getViewHdl().getFocusedL()
        if lc is not None:
            lid = self.browsers[lc.getPid()].getLid()
            pos = -1
            if lc.isItemsL():
                sel = lc.getSelection()
                if len(sel) > 0:
                    pos = sel[-1]
            iids = self.getDataHdl().pasteItems(lid, pos)
            if len(iids) > 0:
                self.refreshAll()

    def insertItem(self, src=None, item=None, iid=None, pos=-1, rfrsh=True):
        src = RefsList.makeSrc(src)
        if item is not None:
            lid = self.getDataHdl().getLidForSrc(src)
            if lid is None:
                lid = self.getDataHdl().addList(src)
            iid = self.getDataHdl().insertItem(lid, item, iid, pos)
        if iid is not None and rfrsh:
            self.refreshAll()
        return iid
    def insertItems(self, src=None, items=[], rfrsh=True):
        lid = self.getDataHdl().getLidForSrc(src)
        if lid is None:
            lid = self.getDataHdl().addList(src)
        iids = self.getDataHdl().insertItems(lid, items)
        if len(iids) > 0 and rfrsh:
            self.refreshAll()
        return iids

    #### TODO HANDLING HIST
    def appendItemToHist(self, item, iid=None, rfrsh=True):
        src = RefsList.getHistSrc()
        self.insertItem(src, item, iid, 0, rfrsh)
    def appendItemsToHist(self, items, rfrsh=True):
        src = RefsList.getHistSrc()
        self.insertItems(src, items, rfrsh)

    def getNbItemsForSrc(self, src=None):
        src = RefsList.makeSrc(src)
        lid = self.getDataHdl().getLidForSrc(src)
        if lid is not None:
            return len(self.getDataHdl().getList(lid))
        return -1
    def getItemsForSrc(self, src=None):
        src = RefsList.makeSrc(src)
        lid = self.getDataHdl().getLidForSrc(src)
        if lid is not None:
            return [self.getDataHdl().getItemForIid(iid) for iid in self.getDataHdl().getList(lid).getIids()]
        return None
    def markSavedSrc(self, src=None, lid=None, path=None):
        if lid is None:
            src = RefsList.makeSrc(src)
            lid = self.getDataHdl().getLidForSrc(src)
        if lid is not None:
            self.getDataHdl().getList(lid).isChanged = False 
            if path is not None:
                self.getDataHdl().getList(lid).setSrc('file', path)
            pos = self.getDataHdl().getListPosForId(lid)
            self.getViewHdl().getLCC().RefreshItem(pos)
            self.refreshAll()

    
    def manageDrag(self, ctrl, trg_where, text):
        lid = self.getAssociated(ctrl.getPid(),"lid")
        sel = map(int, text.split(','))
        pos = None
        if ctrl.type_lc == "containers":
            if trg_where['index'] != -1:
                nlid = self.getDataHdl().getLidAtPos(trg_where['index'])
                if nlid != lid:
                    pos = -1
        else:
            nlid = lid
            pos = trg_where['index']
            if trg_where['after'] and pos != -1:
                pos += 1
        if pos is not None:
            self.getDataHdl().moveItems(lid, nlid, sel, pos)
        self.getViewHdl().refresh()


    def getIidsForAction(self, down=True):
        sel = []
        iids = []
        lc = self.getViewHdl().getFocusedL()
        if lc is not None:
            lid = self.browsers[lc.getPid()].getLid()
            if lc.isItemsL():
                sel = lc.getSelection()
                if len(sel) == 1 and down:
                    iids = self.getDataHdl().getList(lid).getIidsAfterPos(sel[0])
                else:
                    iids = self.getDataHdl().getList(lid).getIidsAtPoss(sel)
            elif lc.isContainersL():
                iids = self.getDataHdl().getList(lid).getIids()
        return iids
    def getIidsForActionDown(self):
        sel = []
        iids = []
        lc = self.getViewHdl().getFocusedL()
        if lc is not None:
            lid = self.browsers[lc.getPid()].getLid()
            if lc.isItemsL():
                sel = lc.getSelection()
                iids = self.getDataHdl().getList(lid).getIidsAtPoss(sel)
            elif lc.isContainersL():
                iids = self.getDataHdl().getList(lid).getIids()
        ### print "IIDS for action", iids
        return iids
    def getIidsForLid(self, lid):
        return self.getDataHdl().getIidsForLid(lid)
    def getItemsForLid(self, lid):
        return self.getDataHdl().getItemsForLid(lid)
    def getItemsMapForLid(self, lid, pos=None):
        return self.getDataHdl().getItemsMapForLid(lid, pos)
    def getItemsForAction(self, down=True):
        return [self.getDataHdl().getItemForIid(iid) for iid in self.getIidsForAction(down)]
    def getNbItemsForAction(self, down=True):
        return len(self.getIidsForAction(down))
    def getSaveListInfo(self, lid=None):
        if lid is None:
            lc = self.getViewHdl().getFocusedL()
            if lc is not None:
                lid = self.browsers[lc.getPid()].getLid()

        if self.getDataHdl().getList(lid) is not None:
            reds = [self.getDataHdl().getItemForIid(iid) for iid in self.getDataHdl().getList(lid).getIids()]
            return {"lid": lid, "reds": reds, "nb_reds": len(reds), "path": self.getDataHdl().getList(lid).getSrcPath()}
        return None

    
    def flipEnabled(self, iids):
        for iid in iids:
            self.getDataHdl().getItemForIid(iid).flipEnabled()
        self.refreshAll()
    def setAllEnabled(self):
        lc = self.getViewHdl().getFocusedL()
        if lc is not None:
            lid = self.browsers[lc.getPid()].getLid()
            iids = self.getDataHdl().getList(lid).getIids()
            for iid in iids:
                self.getDataHdl().getItemForIid(iid).setEnabled()
        self.refreshAll()
    def setAllDisabled(self):
        lc = self.getViewHdl().getFocusedL()
        if lc is not None:
            lid = self.browsers[lc.getPid()].getLid()
            iids = self.getDataHdl().getList(lid).getIids()
            for iid in iids:
                self.getDataHdl().getItemForIid(iid).setDisabled()
        self.refreshAll()

    #### FIND FUNCTIONS
    def getNamesList(self):
        lid = self.getViewHdl().getLid()
        return self.getDataHdl().getNamesList(lid)

    def updateFind(self, matching=None, non_matching=None, cid=None):
        if matching is not None:
            if self.curr_match is not None and self.curr_match >= 0 and self.curr_match < len(self.matching): 
                self.getViewHdl().getLCI().setUnfoundRow(self.matching[self.curr_match])
            self.curr_match = None
            self.matching = matching

        if matching is None or len(matching) > 0:
            self.getNextMatch()
            if self.curr_match == -1:
                if self.prev_sels is None:
                    self.prev_sels = self.getViewHdl().getLCI().clearSelection()
                self.getViewHdl().getLCI().setSelection(self.matching)
            elif self.curr_match == 0:
                self.getViewHdl().getLCI().clearSelection()
            if self.curr_match >= 0:
                self.getViewHdl().getLCI().setFoundRow(self.matching[self.curr_match])
                if self.matching[self.curr_match-1] != self.matching[self.curr_match]:
                    self.getViewHdl().getLCI().setUnfoundRow(self.matching[self.curr_match-1])
            
    def getNextMatch(self, n=None):
        if len(self.matching) > 0:
            if self.curr_match is None:
                self.curr_match = -1
            else:
                self.curr_match += 1
                if self.curr_match == len(self.matching):
                    self.curr_match = 0

    def quitFind(self, matching=None, non_matching=None, cid=None):
        if self.curr_match >=0 and self.curr_match < len(self.matching):
            self.getViewHdl().getLCI().setUnfoundRow(self.matching[self.curr_match])
        if self.prev_sels is not None and self.curr_match != -1:
            self.getViewHdl().getLCI().setSelection(self.prev_sels)
        self.prev_sels = None

    #### Generate pop up menu
    def makePopupMenu(self):
        self.parent.makePopupMenu(self.parent.toolFrame)
    def makeMainMenu(self):
        self.parent.makeMenu(self.parent.toolFrame)
        
    def GetNumberRowsItems(self):
        return self.getViewHdl().GetNumberRowsItems()
    def GetNumberRowsContainers(self):
        return self.getViewHdl().GetNumberRowsContainers()
    def GetNumberColsItems(self):
        return self.getViewHdl().GetNumberColsItems()
    def GetNumberColsContainers(self):
        return self.getViewHdl().GetNumberColsContainers()
    def GetNumberRowsFocused(self):
        return self.getViewHdl().GetNumberRowsFocused()
    def GetNumberColsFocused(self):
        return self.getViewHdl().GetNumberColsFocused()
    def GetNumberRows(self):
        return self.GetNumberRowsFocused()
    def GetNumberCols(self):
        return self.GetNumberColsFocused()
    def nbItems(self):
        return self.getViewHdl().nbItems()
    def nbLists(self):
        return self.getViewHdl().nbLists()

    def nbSelectedItems(self):
        return self.getViewHdl().nbSelectedItems()
    def nbSelectedLists(self):
        return self.getViewHdl().nbSelectedLists()
    def nbSelectedFocused(self):
        return self.getViewHdl().nbSelectedFocused()
    def nbSelected(self):
        return self.getViewHdl().nbSelected()


    def isEmptyBuffer(self):
        return self.getDataHdl().isEmptyBuffer()
    def hasFocusContainersL(self):
        return self.getViewHdl().getFocusedL() is not None and self.getViewHdl().getFocusedL().isContainersL()
    def hasFocusCLFile(self):
        ll = self.getDataHdl().getList(self.getViewHdl().getLid())
        return ll is not None and ll.hasSrcPath()
    def hasFocusItemsL(self):
        return self.getViewHdl().getFocusedL() is not None and self.getViewHdl().getFocusedL().isItemsL()
    def getNbSelected(self):
        if self.getViewHdl().getFocusedL() is not None:
            return len(self.getViewHdl().getFocusedL().getSelection())
        return 0
    def getItemForIid(self, iid):
        return self.getDataHdl().getItemForIid(iid)
    def getSelectedItemPos(self):
        if self.nbSelectedItems() == 1:
            pos = self.getViewHdl().getLCI().getFirstSelection()
            if pos > -1:
                return pos
        return None
    def getSelectedItemIid(self):
        pos = self.getSelectedItemPos()
        if pos > -1:
            return self.getDataHdl().getList(self.getViewHdl().getLid()).getIidAtPos(pos)
        return None
    def getSelectedItem(self):
        iid = self.getSelectedItemIid()
        if iid is not None:
            return self.getDataHdl().getItemForIid(iid)
        return None

    def substituteItem(self, iid, item, rfrsh=True):
        ### just substitute, if absent from data does nothing
        lids = self.getDataHdl().getListsReferIid(iid)
        lid_active = self.getViewHdl().getLid()
        ch = self.getDataHdl().substituteItem(iid, item)
        if not ch:
            return
        pos = None
        for (lid, lcc) in lids:
            lcc.isChanged = True
            if lid_active == lid:
                pos = lcc.getPosForIid(iid)
        if rfrsh:
            self.refreshAll()
        # if pos is not None:
        #     self.getViewHdl().getLCI().RefreshItem(pos)
    def applyEditToData(self, iid, item, rfrsh=True):
        ### handle edit, substitute in data, if absent from data add to
        ### add the old red to hist
        old_item = self.getDataHdl().getItemForIid(iid)
        if old_item is None:
            ### not in the data
            ## print "APPLY CHANGE -- not in the data, adding..."
            self.appendItemToHist(item, iid, rfrsh=False)
        elif old_item != item:
            ## print "APPLY CHANGE -- in the data, substituting..."
            self.substituteItem(iid, item, rfrsh=False)
        # else:
        #     print "APPLY CHANGE -- in the data, identical..."
        if old_item != item:
            ## print "APPLY CHANGE -- Adding to hist..."
            self.appendItemToHist(old_item, rfrsh=False)
            self.refreshAll()
    def updateEdit(self, item, row):
        ll = self.getDataHdl().getList(self.getViewHdl().getLid())
        iid = ll.getIidAtPos(row)
        self.getDataHdl().substituteItem(iid, item)
        ll.isChanged = True
        self.getViewHdl().getLCI().RefreshItem(row)

    # def getSelectedRow(self): ### legacy no s
    #     lc = self.getViewHdl().getFocusedL()
    #     if lc is not None:
    #         return lc.getSelection()
    #     return []
    def getSelectedRow(self): ### legacy no s
        return self.getIidsForAction()

    def onItemActivated(self, ll=None, pos=None):
        if ll is None or pos is None:
            rid = self.getSelectedItemIid()
            red = self.getSelectedItem()
        else:
            rid = ll.getIidAtPos(pos)
            red = self.getDataHdl().getItemForIid(rid)
        self.viewItem(red, rid)

    def viewItem(self, red=None, rid=None, viewT=None):
        if viewT is None:
            viewT = self.parent.viewsm.getDefaultViewT("R", self.parent.tabs[self.tabId]["type"])
        self.parent.viewsm.viewData(viewT, red, rid, self.tabId)        

    def viewData(self, rid=None, viewT=None):
        if rid is None:
            rid = self.getSelectedItemIid()
        red = self.getDataHdl().getItemForIid(rid).copy()
        if viewT is None:
            viewT = self.parent.viewsm.getDefaultViewT("R", self.parent.tabs[self.tabId]["type"])
        return self.parent.viewsm.viewData(viewT, red, rid, self.tabId)        

    def viewListData(self, lid=None, viewT=None):
        items_map = []
        poss = None
        if lid == -1 or lid is None:
            lc = self.getViewHdl().getFocusedL()
            lid = self.browsers[lc.getPid()].getLid()
            if lc.isItemsL():
                poss = lc.getSelection()
        if lid is not None:
            items_map = self.getItemsMapForLid(lid, poss)
        if len(items_map) > 0:
            if viewT is None:
                viewT = self.parent.viewsm.getDefaultViewT("L", self.parent.tabs[self.tabId]["type"])
            self.parent.viewsm.viewData(viewT, items_map, lid, self.tabId)

class VarsManager(ContentManager):

    def initData(self, parent):
        self.data = VarsSet(parent)
    def resetData(self, src=None, data=[], sord=None):
        nlid = self.getDataHdl().resetContent(src, data)
        if nlid is not None:
            self.getViewHdl().updateLid(nlid)
        return nlid

    def viewItem(self, datVar=None, rid=None, viewT=None):
        if viewT is None:
            viewT = self.parent.viewsm.getDefaultViewT("R", self.parent.tabs[self.tabId]["type"])
        if datVar is None and rid is not None:
            datVar = self.getDataHdl().getItemForIid(rid)
        queries = [Query(), Query()]
        queries[datVar.getSide()].extend(-1, Literal(False, datVar.getTerm()))
        self.parent.viewsm.newRedVHist(queries, viewT)

    def viewData(self, rid=None, viewT=None):
        if rid is None:
            rid = self.getSelectedItemIid()
        datVar = self.getDataHdl().getItemForIid(rid)
        if viewT is None:
            viewT = self.parent.viewsm.getDefaultViewT("R", self.parent.tabs[self.tabId]["type"])
        queries = [Query(), Query()]
        queries[datVar.side].extend(-1, Literal(False, datVar.getTerm()))
        self.parent.viewsm.newRedVHist(queries, viewT)


    
class RedsManager(ContentManager):

    def initData(self, parent):
        self.data = RedsSet(parent)
    def getSelectedQueries(self):
        red = self.getSelectedItem()
        if red is not None and isinstance(red, Redescription):
            return red.getQueries()
        return 

    def refreshComp(self, data):
        self.getDataHdl().recomputeAll(data)
        self.uptodate = True

    def filterToOne(self, parameters):
        compare_ids = self.getIidsForAction(down=True) 
        self.getDataHdl().filterToOne(compare_ids, parameters)
        self.refreshAll()
        
    def filterAll(self, parameters):
        compare_ids = self.getIidsForAction(down=True) 
        self.getDataHdl().filterAll(compare_ids, parameters)
        self.refreshAll()

    def processAll(self, parameters, init_current=True):
        iids = {"before": [], "after": [], "compare": []}
        ll = None
        lc = self.getViewHdl().getFocusedL()
        if lc is not None:
            lid = self.browsers[lc.getPid()].getLid()
            ll = self.getDataHdl().getList(lid)
            if lc.isContainersL():
                iids["compare"] = ll.getIids()

            elif lc.isItemsL():
                which = "before"
                for (li, iid) in enumerate(ll.getIids()):
                    if lc.IsSelected(li):
                        which = "after"
                        iids["compare"].append(iid)
                    else:
                        iids[which].append(iid)

        if len(iids["compare"]) > 0 and ll is not None:
            llafter = len(iids["after"])
            if len(iids["compare"]) == 1 and len(iids["after"]) > 0:
                iids["compare"].extend(iids["after"])
                iids["after"] = []
            top, middle, bottom = self.getDataHdl().processAll(iids["compare"], parameters)
            ll.setIids(iids["before"]+top+middle+bottom+iids["after"])
            # print "IIDS", iids["before"],top,middle,bottom,iids["after"]
            # print len(iids["before"]), len(iids["before"])+len(top)+len(middle)+len(bottom), len(ll), llafter, len(ll)-llafter
            self.refreshAll()
            if lc.isItemsL():
                for li in range(len(iids["before"]), len(ll)-llafter):
                    lc.Select(li)


    def recomputeAll(self, restrict):
        if self.parent.hasDataLoaded():
            self.uptodate = False
            self.refreshComp(self.parent.dw.getData())
            # for k,v in self.opened_edits.items():
            #     mc = self.parent.accessViewX(k)
            #     if mc is not None:
            #         mc.refresh()
            self.refreshAll()
