import numpy
import wx
### from wx import ALIGN_CENTER, ALL, EXPAND, HORIZONTAL
### from wx import FONTFAMILY_DEFAULT, FONTSTYLE_NORMAL, FONTWEIGHT_NORMAL
### from wx import BoxSizer, Button, Font, NewId
### from wx import EVT_BUTTON, EVT_LEFT_DCLICK

# The recommended way to use wx with mpl is with the WXAgg
# backend. 

from ..reremi.classSParts import SSetts
from classGView import GView

import matplotlib
# matplotlib.use('WXAgg')

import matplotlib.pyplot as plt
import matplotlib.colors

import pdb

class TDView(GView):

    TID = None
    NBBINS = 20
        
    def updateMap(self):
        """ Redraws the map
        """
        if self.wasKilled():
            return

        if self.isReadyPlot():

            self.clearPlot()

            self.makeBackground()   
            dsetts = self.getDrawSettDef()

            ### SELECTED DATA
            selected = self.getUnvizRows()
            # selected = self.getParentData().selectedRows()
            selp = 0.5
            if self.sld_sel is not None:
                selp = self.sld_sel.GetValue()/100.0

            x0, x1, y0, y1 = self.getAxisLims()
            bx, by = (x1-x0)/100.0, (y1-y0)/100.0

            if self.isSingleVar():
                ccs = self.getQCols()
                col = self.getCol(ccs[0][0], ccs[0][1])
                vec = col.getVector()
                cmap, vmin, vmax = (self.getCMap(col.typeId()), numpy.nanmin(vec), numpy.nanmax(vec))

                # ##### KOEPPEN MAP
                # if (col.side, col.id) == (1, 20):
                #     colors_n = ['Af', 'Am', 'As', 'Aw', 'BSh', 'BSk', 'BWh', 'BWk', 'Cfa', 'Cfb','Cfc', 'Csa', 'Csb', 'Csc', 'Cwa','Cwb', 'Cwc', 'Dfa', 'Dfb', 'Dfc','Dfd', 'Dsa', 'Dsb', 'Dsc', 'Dsd','Dwa', 'Dwb', 'Dwc', 'Dwd', 'EF','ET', 'Ocean']
                #     colors_k = ["#960000", "#FF0000", "#FF6E6E", "#FFCCCC", "#CC8D14", "#CCAA54", "#FFCC00", "#FFFF64", "#007800", "#005000", "#003200", "#96FF00", "#00D700", "#00AA00", "#BEBE00", "#8C8C00", "#5A5A00", "#550055", "#820082", "#C800C8", "#FF6EFF", "#646464", "#8C8C8C", "#BEBEBE", "#E6E6E6", "#6E28B4", "#B464FA", "#C89BFA", "#C8C8FF", "#6496FF", "#64FFFF", "#F5FFFF"]
                #     colors_dict = dict(zip(*[colors_n, colors_k]))
                #     map_colnb = [colors_dict[v] for v in col.ord_cats]
                #     cmap = matplotlib.colors.ListedColormap(map_colnb, name='custom', N=len(map_colnb))
                # ############
                                
                norm = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax, clip=True)
                mapper = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)
                ec_dots = numpy.array([mapper.to_rgba(v, alpha=dsetts["color_e"][-1]) for v in vec])
                fc_dots = numpy.array([mapper.to_rgba(v, alpha=dsetts["color_f"][-1]) for v in vec])
                lc_dots = numpy.array([mapper.to_rgba(v, alpha=dsetts["color_l"][-1]) for v in vec])
                self.dots_draws = {"fc_dots": fc_dots, "ec_dots": ec_dots, "lc_dots": lc_dots,
                                   "sz_dots": numpy.ones(vec.shape)*dsetts["size"],
                                   "zord_dots": numpy.ones(vec.shape)*self.DEF_ZORD,
                                   "draw_dots": numpy.ones(vec.shape, dtype=bool)}
                mapper.set_array(vec)

            else:
                self.dots_draws = self.prepareEntitiesDots()
                mapper = None
                
            if len(selected) > 0:
                self.dots_draws["fc_dots"][numpy.array(list(selected)), -1] *= selp
                self.dots_draws["ec_dots"][numpy.array(list(selected)), -1] *= selp
                self.dots_draws["lc_dots"][numpy.array(list(selected)), -1] *= selp
            draw_indices = numpy.where(self.dots_draws["draw_dots"])[0]
            
            if self.plotSimple(): ##  #### NO PICKER, FASTER PLOTTING.
                ku, kindices = numpy.unique(self.dots_draws["zord_dots"][draw_indices], return_inverse=True)
                ## pdb.set_trace()
                for vi, vv in enumerate(ku):
                    self.axe.scatter(self.getCoords(0,draw_indices[kindices==vi]),
                                    self.getCoords(1,draw_indices[kindices==vi]),
                                    c=self.dots_draws["fc_dots"][draw_indices[kindices==vi],:],
                                    edgecolors=self.dots_draws["ec_dots"][draw_indices[kindices==vi],:],
                                    s=5*self.dots_draws["sz_dots"][draw_indices[kindices==vi]], marker=dsetts["shape"],
                                    zorder=vv)
            else:
                for idp in draw_indices:
                        self.drawEntity(idp, self.getPlotColor(idp, "fc"), self.getPlotColor(idp, "ec"),
                                                self.getPlotProp(idp, "sz"), self.getPlotProp(idp, "zord"), dsetts)
            if mapper is not None:
                ax2 = self.axe #.twinx()
                nb = self.NBBINS
                if col.typeId() == 2: ### Categorical
                    nb = [b-0.5 for b in numpy.unique(vec)]
                    nb.append(nb[-1]+1)
                    bins_ticks = numpy.unique(vec)
                    bins_lbl = [col.getCatForVal(b, "NA") for b in bins_ticks]
                n, bins, patches = plt.hist(vec, bins=nb)
                sum_h = numpy.max(n)
                norm_h = [ni*0.1*float(x1-x0)/sum_h+0.03*float(x1-x0) for ni in n]
                norm_bins = [(bi-bins[0])/float(bins[-1]-bins[0]) * 0.95*float(y1-y0) + y0 + 0.025*float(y1-y0) for bi in bins]
                if col.typeId() == 2: ### Categorical
                    norm_bins_ticks = [(bi-bins[0])/float(bins[-1]-bins[0]) * 0.95*float(y1-y0) + y0 + 0.025*float(y1-y0) for bi in bins_ticks]
                else:
                    norm_bins_ticks = norm_bins
                    bins_lbl = bins
                left = [norm_bins[i] for i in range(len(n))]
                width = [norm_bins[i+1]-norm_bins[i] for i in range(len(n))]

                colors = [mapper.to_rgba(numpy.mean(bins[i:i+2])) for i in range(len(n))]
                bckc = "white" 
                ax2.barh(y0, -(0.13*(x1-x0)+bx), y1-y0, x1+0.13*(x1-x0)+2*bx, color=bckc, edgecolor=bckc)
                ax2.barh(left, -numpy.array(norm_h), width, x1+0.13*(x1-x0)+2*bx, color=colors, edgecolor=bckc, linewidth=2)
                ax2.plot([x1+2*bx+0.1*(x1-x0), x1+2*bx+0.1*(x1-x0)], [norm_bins[0], norm_bins[-1]], color=bckc, linewidth=2)
                x1 += 0.13*(x1-x0)+2*bx
                self.axe.set_yticks(norm_bins_ticks)
                self.axe.set_yticklabels(bins_lbl)
                # self.axe.yaxis.tick_right()
                self.axe.tick_params(direction="inout", left="off", right="on",
                                         labelleft="off", labelright="on")

                # ylbls_ext = self.axe.yaxis.get_ticklabel_extents(self.MapcanvasMap.get_renderer())[1].get_points()
                # print "Win ext", self.axe.get_window_extent() # get the original position
                # print ylbls_ext 
                # ratio = ylbls_ext[0,0]/ ylbls_ext[1,0]
                # pos1 = self.axe.get_position() # get the original position
                # print "New position", [pos1.x0, pos1.y0,  ratio*pos1.width, pos1.height]
                # self.axe.set_position([pos1.x0, pos1.y0,  ratio*pos1.width, pos1.height]) # set a new position 

            self.makeFinish((x0, x1, y0, y1), (bx, by))   
            self.updateEmphasize(review=False)
            self.MapcanvasMap.draw()
            self.MapfigMap.canvas.SetFocus()
        else:
            self.plot_void()      

    def getCanvasConnections(self):
        return [("MASK", None),
                ("key_press_event", self.key_press_callback),
                ("button_release_event", self.on_click),
                ("motion_notify_event", self.on_motion)]
            
    def makeBackground(self):   
        pass
    def makeFinish(self, xylims, xybs):
        pass

    def additionalBinds(self):
        self.MapredMapQ[0].Bind(wx.EVT_TEXT_ENTER, self.OnEditQuery)
        self.MapredMapQ[1].Bind(wx.EVT_TEXT_ENTER, self.OnEditQuery)
        for button in self.buttons:
            button["element"].Bind(wx.EVT_BUTTON, button["function"])
        self.sld_sel.Bind(wx.EVT_SCROLL_THUMBRELEASE, self.OnSlide)
        ##self.sld_sel.Bind(wx.EVT_SCROLL_CHANGED, self.OnSlide)

    def OnSlide(self, event):
        self.updateMap()
    
    def plotSimple(self):
        return True
    def isReadyPlot(self):
        return False    
    def getAxisLims(self):
        return (0,1,0,1)

    def hoverActive(self):
        return GView.hoverActive(self) and not self.mc.isActive()
    def inCapture(self, event):
        return self.getCoords() is not None and event.inaxes == self.axe

    
