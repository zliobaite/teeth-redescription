import wx
### from wx import ALIGN_CENTER, EVT_TOGGLEBUTTON, EXPAND, RAISED_BORDER
### from wx import FlexGridSizer, NewId, Panel, ToggleButton

from classGView import GView

import pdb


class Filler(object):
    unactive_color = (225,225,225)
    active_color = (255,249,178)
    active_color = (247,247,200)


    def getVizType(self):
        if self.parent.getVizm().isVizSplit():
            return "s"
        return "t"
    def getFWidth(self):
        return GView.fwidth[self.getVizType()]    
    def getFHeight(self):
        return GView.fheight[self.getVizType()]

    def __init__(self, parent, pos):
        self.parent = parent
        self.pos = pos
        self.mapFrame = self.parent.tabs["viz"]["tab"]
        self.panel = wx.Panel(self.mapFrame, -1, style=wx.RAISED_BORDER)
        self.drawFrame()
        self.binds()
        # self.mapFrame.Show()

    def getGPos(self):
        return self.pos

    def resetGPos(self, npos):
        self.mapFrame.GetSizer().Detach(self.panel)
        self.pos = npos
        self.mapFrame.GetSizer().Add(self.panel, pos=self.getGPos(), flag=wx.EXPAND|wx.ALIGN_CENTER, border=0)

    def binds(self):
        self.boxSel.Bind(wx.EVT_TOGGLEBUTTON, self.OnSelect)

    def OnSelect(self, event):
        self.parent.getVizm().setActiveViz(self.getGPos())

    def _SetSize(self):
        pixels = tuple(self.mapFrame.GetClientSize())
        laybox = self.mapFrame.GetSizer()
        # sz = (laybox.GetCols(), laybox.GetRows())
        sz = self.parent.getVizm().getVizGridSize()
        pixels = (max(self.getFWidth(), (pixels[0]-2*self.parent.getVizm().getVizBb())/float(sz[1])),
                  max(self.getFHeight(), (pixels[1]-2*self.parent.getVizm().getVizBb())/float(sz[0])))
        self.boxSel.SetMinSize(pixels)
        self.panel.SetMinSize(pixels)
        laybox.Layout()

                
    def drawFrame(self):
        # self.boxSel = wx.ToggleButton(self.panel, wx.NewId(), "(%d,%d)" % (self.getGPos()[0], self.getGPos()[1]), style=wx.ALIGN_CENTER, size=(50,50))
        self.boxSel = wx.ToggleButton(self.panel, wx.NewId(), "", style=wx.ALIGN_CENTER|wx.EXPAND, size=(50,50))
        self.masterBox =  wx.FlexGridSizer(rows=1, cols=1, vgap=0, hgap=0)
        self.masterBox.Add(self.boxSel, 0, border=1,  flag=wx.ALIGN_CENTER)

        self.panel.SetSizer(self.masterBox)
        self.mapFrame.GetSizer().Add(self.panel, pos=self.getGPos(), flag=wx.EXPAND|wx.ALIGN_CENTER, border=0)            
        self._SetSize()

    def popSizer(self):
        self.mapFrame.GetSizer().Remove(self.panel)
        self.mapFrame.GetSizer().Layout()
        return self.panel

    def setActive(self):
        self.boxSel.SetValue(True)
        self.boxSel.Disable()
        self.boxSel.SetBackgroundColour(self.active_color)

    def setUnactive(self):
        self.boxSel.SetValue(False)
        self.boxSel.Enable()
        self.boxSel.SetBackgroundColour(self.unactive_color)

            
