import wx
### from wx import ALIGN_CENTER, ALL, EXPAND, HORIZONTAL, ID_ANY, SL_HORIZONTAL, VERTICAL
### from wx import FONTFAMILY_DEFAULT, FONTSTYLE_NORMAL, FONTWEIGHT_NORMAL
### from wx import EVT_BUTTON, EVT_SCROLL_CHANGED, EVT_SCROLL_THUMBRELEASE
### from wx import BoxSizer, Button, DefaultPosition, Font, Slider, StaticText


import numpy
import re
# The recommended way to use wx with mpl is with the WXAgg
# backend. 
# import matplotlib
# matplotlib.use('WXAgg')
import matplotlib.pyplot as plt
import scipy.spatial.distance
#from mpl_toolkits.basemap import Basemap
import mpl_toolkits.basemap
from matplotlib.patches import Polygon

from ..reremi.classQuery import Query
from ..reremi.classSParts import SSetts
from ..reremi.classRedescription import Redescription
from classTDView import TDView


import pdb

class MapView(TDView):

    TID = "MAP"
    SDESC = "Map"
    title_str = "Map"
    ordN = 1
    geo = True
    MAP_POLY = True #False
    typesI = "vr"

    marg_f = 100.0
    proj_def = "mill"
    proj_names = {"None": None,
                  "Gnomonic": "gnom",
                  "Mollweide": "moll",
                  "Gall Stereographic Cylindrical": "gall",
                  "Miller Cylindrical": "mill",
                  "Mercator": "merc",
                  "Hammer": "hammer",
                  "Geostationary": "geos",
                  "Near-Sided Perspective": "nsper",
                  "van der Grinten": "vandg",
                  "McBryde-Thomas Flat-Polar Quartic": "mbtfpq",
                  "Sinusoidal": "sinu",
                  "Lambert Conformal": "lcc",
                  "Equidistant Conic": "eqdc",
                  "Cylindrical Equidistant": "cyl",
                  "Oblique Mercator": "omerc",
                  "Albers Equal Area": "aea",
                  "Orthographic": "ortho",
                  "Cassini-Soldner": "cass",
                  "Robinson": "robin",
                  ######
                  "Azimuthal Equidistant": "aeqd",
                  "Lambert Azimuthal Equal Area": "laea",
                  "Stereographic": "stere",
                  #############
                  "Cylindrical Equal Area": "cea", 
                  "Eckert IV": "eck4", 
                  "Kavrayskiy VII": "kav7",
                  "Polyconic": "poly",
                  "N/S-Polar Lambert Azimuthal": "nplaea",
                  "N/S-Polar Stereographic": "npstere",
                  "N/S-Polar Azimuthal Equidistant": "npaeqd",
                  # "Rotated Pole": "rotpole",
                  # "Transverse Mercator": "tmerc",
                      }

    proj_pk = {"aeqd": ["lat_0", "lon_0", "width", "height"],
               "laea": ["lat_0", "lon_0","width", "height"],
               "stere": ["lat_0", "lon_0","width", "height"],
               ###
               "npaeqd": ["lon_0", "boundinglat"],
               "nplaea": ["lon_0", "boundinglat"],
               "npstere": ["lon_0", "boundinglat"],
               ###
               "spaeqd": ["lon_0", "boundinglat"],
               "splaea": ["lon_0", "boundinglat"],
               "spstere": ["lon_0", "boundinglat"],              
               ##############
               "geos": ["lon_0"],
               "vandg": ["lon_0"],
               "moll": ["lon_0"],
               "hammer": ["lon_0"],
               "robin": ["lon_0"],
               "mbtfpq": ["lon_0"],
               "sinu": ["lon_0"],
               "eck4": ["lon_0"], 
               "kav7": ["lon_0"],
               "ortho": ["lat_0", "lon_0"],
               "nsper": ["lat_0", "lon_0", "satellite_height"],
               "poly": ["lat_0", "lon_0","width", "height"],
               "gnom": ["lat_0", "lon_0", "width", "height"],
               "cass": ["lat_0", "lon_0", "width", "height"],
               #############
               "eqdc": ["lat_0", "lon_0", "lat_1", "lat_2","width", "height"],
               "aea": ["lat_0", "lon_0", "lat_1", "lat_2","width", "height"],
               "omerc": ["lat_0", "lon_0","lat_1", "lon_1", "lat_2", "lon_2","width", "height"],               
               "lcc": ["lat_0", "lon_0","lat_1", "lon_1", "lat_2", "lon_2","width", "height"],
               #############
               "cea": ["llcrnrlat", "llcrnrlon", "urcrnrlat", "urcrnrlon"],
               "cyl": ["llcrnrlat", "llcrnrlon", "urcrnrlat", "urcrnrlon"],
               "merc": ["llcrnrlat", "llcrnrlon", "urcrnrlat", "urcrnrlon"],
               "mill": ["llcrnrlat", "llcrnrlon", "urcrnrlat", "urcrnrlon"],
               "gall": ["llcrnrlat", "llcrnrlon", "urcrnrlat", "urcrnrlon"],
                }        
        
    bounds_def = {"llon": -180., "ulon": 180., "llat": -90., "ulat": 90.}
    # bounds_try = {"llon": -180., "ulon": 180., "llat": -90., "ulat": 90.}

    def drawMap(self):
        """ Draws the map
        """

        # if self.getParentCoords() is None:
        #     self.coords_proj = None
        #     return
        if not hasattr( self, 'axe' ):
            self.bm, self.bm_args = self.makeBasemapProj()

            self.coords_proj = self.mapCoords(self.getParentCoords(), self.bm)
            if self.bm is not None:
                self.axe = self.MapfigMap.add_axes([0, 0, 1, 1])
                self.bm.ax = self.axe
            else:
                llon, ulon, llat, ulat = self.getParentCoordsExtrema()
                midlon, midlat = (llon + ulon)/2, (llat + ulat)/2
                mside = max(abs(llon-midlon), abs(llat-midlat))
                self.axe = self.MapfigMap.add_subplot(111,
                                                      xlim=[midlon-1.05*mside, midlon+1.05*mside],
                                                      ylim=[midlat-1.05*mside, midlat+1.05*mside])
            ## self.MapcanvasMap.draw()
            # self.axe = self.MapfigMap.add_axes([llon, llat, ulat-llat, ulon-llon])

            self.prepareInteractive()
            self.MapcanvasMap.draw()

            
    def additionalElements(self):        
        flags = wx.ALIGN_CENTER | wx.ALL # | wx.EXPAND

        self.buttons = []
        self.buttons.append({"element": wx.Button(self.panel, size=(self.butt_w,-1), label="Expand"),
                             "function": self.OnExpandSimp})
        self.buttons[-1]["element"].SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        
        self.sld_sel = wx.Slider(self.panel, -1, 10, 0, 100, wx.DefaultPosition, (self.sld_w, -1), wx.SL_HORIZONTAL)

        ##############################################
        add_boxB = wx.BoxSizer(wx.HORIZONTAL)
        add_boxB.AddSpacer((self.getSpacerWn()/2.,-1))

        v_box = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self.panel, wx.ID_ANY,u"- opac. disabled +")
        label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        v_box.Add(label, 0, border=1, flag=flags) #, userData={"where": "*"})
        v_box.Add(self.sld_sel, 0, border=1, flag=flags) #, userData={"where":"*"})
        add_boxB.Add(v_box, 0, border=1, flag=flags)

        add_boxB.AddSpacer((self.getSpacerWn(),-1))
        add_boxB.Add(self.buttons[-1]["element"], 0, border=1, flag=flags)

        add_boxB.AddSpacer((self.getSpacerWn()/2.,-1))

        #return [add_boxbis, add_box]
        return [add_boxB]

    def makeBackground(self):   
        self.makeBasemapBack(self.bm)
    def makeFinish(self, xylims, xybs):
        self.axe.axis([xylims[0], xylims[1], xylims[2], xylims[3]])

    def plotSimple(self):
        return not self.drawPoly()
    def isReadyPlot(self):
        return self.suppABCD is not None and self.getCoords() is not None    
    def getAxisLims(self):
        xx = self.axe.get_xlim()
        yy = self.axe.get_ylim()
        return (xx[0], xx[1], yy[0], yy[1])

    def getPCoords(self):
        if self.coords_proj is not None:
            return zip(*[self.coords_proj[0][0,:,0], self.coords_proj[0][1,:,0]])
        return []

    def getCoordsXY(self, id):
	if self.coords_proj is None:
            return (0,0)
	else:
            return self.coords_proj[0][:,id,0]
    def getCoords(self, axi=None, ids=None):
        if self.coords_proj is None:
            return self.coords_proj
        if axi is None:
            self.coords_proj[0][:,:,0]
        elif ids is None:
            return self.coords_proj[0][axi,:,0]
        return self.coords_proj[0][axi,ids,0]

    def getCoordsP(self, id):
        return self.coords_proj[0][:,id,1:self.coords_proj[1][id]].T

    def apply_mask(self, path, radius=0.0):
        if path is not None and self.getCoords() is not None:
            return [i for i, point in enumerate(self.getPCoords()) if (self.dots_draws["draw_dots"][i] and path.contains_point(point, radius=radius))]
        return []

    def getParentCoords(self):
        if not self.hasParent():
            #self.suppABCD = [0,0,0,0]
            return [[[self.bounds_def[k]] for k in ["llon", "llon", "ulon", "ulon"]],
                    [[self.bounds_def[k]] for k in ["llat", "ulat", "ulat", "llat"]]]
        return self.parent.dw.getCoords()
    def getParentCoordsExtrema(self):
        if not self.hasParent():
            return (-180., 180., -90., 90.)
        return self.parent.dw.getCoordsExtrema()

    
    def mapCoords(self, coords, bm=None):
        self.mapoly = self.getMapPoly() & (min([len(cs) for cs in coords[0]]) > 2)

        nbc_max = max([len(c) for c in coords[0]])
        proj_coords = [numpy.zeros((2, len(coords[0]), nbc_max+1)), []]

        for i in range(len(coords[0])):
            if bm is None:
                p0, p1 = (coords[0][i], coords[1][i])
            else:
                p0, p1 = bm(coords[0][i], coords[1][i])
            proj_coords[1].append(len(p0)+1)
            proj_coords[0][0,i,0] = numpy.mean(p0)
            proj_coords[0][0,i,1:proj_coords[1][-1]] = p0
            proj_coords[0][1,i,0] = numpy.mean(p1)
            proj_coords[0][1,i,1:proj_coords[1][-1]] = p1
        return proj_coords

    def drawPoly(self):
        return self.mapoly 

    def getMapPoly(self):
        t = self.getParentPreferences()
        try:
            mapoly = t["map_poly"]["data"] == "yes"
        except:
            mapoly = MapView.MAP_POLY
        return mapoly

    def drawEntity(self, idp, fc, ec, sz=1, zo=4, dsetts={}):
        if self.drawPoly():
            return [self.axe.add_patch(Polygon(self.getCoordsP(idp), closed=True, fill=True, fc=fc, ec=ec, zorder=zo))]
                    
        else:
            ## print idp, fc, ec
            x, y = self.getCoordsXY(idp)
            return self.axe.plot(x, y, mfc=fc, mec=ec, marker=dsetts["shape"], markersize=sz, linestyle='None', zorder=zo)

    def getBasemapProjSetts(self):
        proj = self.proj_def 
        t = self.getParentPreferences()
        if "map_proj" in t:
            tpro = re.sub(" *\(.*\)$", "", t["map_proj"]["data"])
            if tpro in self.proj_names:
                proj = self.proj_names[tpro]
        resolution = "c"
        if "map_resolution" in t:
            resolution = t["map_resolution"]["data"][0]

        return proj, resolution
            
    def getBasemapBackSetts(self):
        t = self.getParentPreferences()
        draws = {"rivers": False, "coasts": False, "countries": False,
                 "states": False, "parallels": False, "meridians": False,
                 "continents":False, "lakes": False, "seas": False}
        ### DEBUG
        draws = {"rivers": False, "coasts": True, "countries": False,
                 "states": False, "parallels": False, "meridians": False,
                 "continents":False, "lakes": False, "seas": False}

        colors = {"line_color": "gray", "sea_color": "#F0F8FF", "land_color": "white", "none":"white"}
        more = {}
        
        for typ_elem in ["map_elem_area", "map_elem_natural", "map_elem_geop", "map_elem_circ"]:
            if typ_elem in t:
                for elem in t[typ_elem]["data"]:                    
                    draws[elem] = True
                    
        for k in ["map_back_alpha", "map_back_scale"]:
            if k in t:
                more[k] = t[k]["data"]/100.0
            else:
                more[k] = 1.
        for k in ["map_back"]:
            if k in t:
                more[k] = t[k]["value"]
            else:
                more[k] = 0
            
        for color_k in colors.keys():
            if color_k in t:
                colors[color_k] = "#"+"".join([ v.replace("x", "")[-2:] for v in map(hex, t[color_k]["data"])]) 
        return draws, colors, more

    def getParallelsRange(self):
        span = float(self.bm_args["urcrnrlat"] - self.bm_args["llcrnrlat"])
        # if self.bm_args["llcrnrlat"] < self.bm_args["urcrnrlat"]:
        #     span = float(self.bm_args["urcrnrlat"] - self.bm_args["llcrnrlat"])
        # else:
        #     span = (180. - self.bm_args["llcrnrlon"]) + (self.bm_args["urcrnrlon"] + 180.)
        opts = [60, 30, 10, 5, 1]
        p = numpy.argmin(numpy.array([((span/k)-5.)**2 for k in opts]))
        step = opts[p]
        # if self.bm_args["llcrnrlon"] < self.bm_args["urcrnrlon"]:
        return numpy.arange(int(self.bm_args["llcrnrlat"]/step)*step, (int(self.bm_args["urcrnrlat"]/step)+1)*step, step)
        # else:
        #     return numpy.concatenate([numpy.arange(int(self.bm_args["llcrnrlon"]/step)*step, (int(180./step)+1)*step, step),
        #                                   numpy.arange(int(-180./step)*step, (int(self.bm_args["urcrnrlon"]/step)+1)*step, step)])

        
    def getMeridiansRange(self):
        if self.bm_args["llcrnrlon"] < self.bm_args["urcrnrlon"]:
            span = float(self.bm_args["urcrnrlon"] - self.bm_args["llcrnrlon"])
        else:
            span = (180. - self.bm_args["llcrnrlon"]) + (self.bm_args["urcrnrlon"] + 180.)
        opts = [60, 30, 10, 5, 1]
        p = numpy.argmin(numpy.array([((span/k)-5.)**2 for k in opts]))
        step = opts[p]
        if self.bm_args["llcrnrlon"] < self.bm_args["urcrnrlon"]:
            return numpy.arange(int(self.bm_args["llcrnrlon"]/step)*step, (int(self.bm_args["urcrnrlon"]/step)+1)*step, step)
        else:
            return numpy.concatenate([numpy.arange(int(self.bm_args["llcrnrlon"]/step)*step, (int(180./step)+1)*step, step),
                                          numpy.arange(int(-180./step)*step, (int(self.bm_args["urcrnrlon"]/step)+1)*step, step)])

    def getBasemapCorners(self):
        coords = ["llon", "ulon", "llat", "ulat"]
        allundef = True
        ## try_bounds = {"llon": -30., "ulon": 30., "llat": 30., "ulat": 110.}

        mbounds = dict([("c_"+c, v) for (c,v) in self.bounds_def.items()])
        mbounds.update(dict([("margc_"+c, 1./self.marg_f) for (c,v) in self.bounds_def.items()]))
        t = self.getParentPreferences()
        for c in coords:
            ### get corners from settings
            if c in t:
                mbounds["c_"+c] = t[c]["data"]
                ## mbounds["c"+c] = try_bounds[c] #self.getParentPreferences()[c]["data"]
            allundef &=  (mbounds["c_"+c] == -1)
        if allundef:
            ### if all equal -1, set corners to def, globe wide
            mbounds.update(self.bounds_def)
        else:
            ### get corners from data
            mbounds["llon"], mbounds["ulon"], mbounds["llat"], mbounds["ulat"] = self.getParentCoordsExtrema()
            for coord in coords:
                ### if corners coords from settings lower than 180,
                ### replace that from data, and drop margin
                if numpy.abs(mbounds["c_"+coord]) <= 180: #numpy.abs(self.bounds_def[coord]):
                    mbounds[coord] = mbounds["c_"+coord]                    
                    mbounds["margc_"+coord] = 0.

        for coord in ["lon", "lat"]:
            mbounds["marg_l"+coord] = mbounds["margc_l"+coord] * (mbounds["u"+coord]-mbounds["l"+coord]) 
            mbounds["marg_u"+coord] = mbounds["margc_u"+coord] * (mbounds["u"+coord]-mbounds["l"+coord]) 
        return mbounds
    
    def makeBasemapProj(self):
        proj, resolution = self.getBasemapProjSetts()
        if proj is None:
            return None, None
        mbounds = self.getBasemapCorners()
        ## print "MBOUNDS", "\n".join(["%s:%s" % (k,v) for (k,v) in mbounds.items()])

        # circ_equ=2*numpy.pi*6378137.
        # circ_pol=2*numpy.pi*6356752.
        # circ_avg=2*numpy.pi*6371000.
        circ_def=2*numpy.pi*6370997.

        llcrnrlon = numpy.max([-180., mbounds["llon"]-mbounds["marg_llon"]])
        urcrnrlon = numpy.min([180., mbounds["ulon"]+mbounds["marg_ulon"]])
        if urcrnrlon <= llcrnrlon:
            if "lon_0" in self.proj_pk[proj]:
                span_lon = (360+urcrnrlon-llcrnrlon)
            else:
                urcrnrlon = self.bounds_def["ulon"]
                llcrnrlon = self.bounds_def["llon"]
                span_lon = (urcrnrlon-llcrnrlon)
        else:
            span_lon = (urcrnrlon-llcrnrlon)

        lon_0 = llcrnrlon + span_lon/2.0
        if lon_0 > 180:
            lon_0 -= 360
            
        llcrnrlat = numpy.max([-90., mbounds["llat"]-mbounds["marg_llat"]])
        urcrnrlat = numpy.min([90., mbounds["ulat"]+mbounds["marg_ulat"]])
        if urcrnrlat <= llcrnrlat:
            urcrnrlat = self.bounds_def["ulat"]
            llcrnrlat = self.bounds_def["llat"]
        if "lat_0" in self.proj_pk[proj]:
            llcrnrlatT = numpy.max([-180., mbounds["llat"]-mbounds["marg_llat"]])
            urcrnrlatT = numpy.min([180., mbounds["ulat"]+mbounds["marg_ulat"]])
        else:
            llcrnrlatT = llcrnrlat
            urcrnrlatT = urcrnrlat 
        span_lat = (urcrnrlatT-llcrnrlatT)
        lat_0 = llcrnrlatT + span_lat/2.0
        if numpy.abs(lat_0) > 90:
            lat_0 = numpy.sign(lat_0)*(180 - numpy.abs(lat_0))

        boundinglat = 0
        height = span_lat/360.
        if numpy.sign(urcrnrlat) == numpy.sign(llcrnrlat):
            width = numpy.cos((numpy.pi/2.)*numpy.min([numpy.abs(urcrnrlat),numpy.abs(llcrnrlat)])/90.)*span_lon/360.
            if urcrnrlat > 0:
                boundinglat = llcrnrlat
            else:
                boundinglat = urcrnrlat
        else: ### contains equator, the largest, factor 1
            width = span_lon/360.
        height = numpy.min([height, 0.5])
        width = numpy.min([width, 1.])
        args_all = {"width": circ_def*width, "height": circ_def*height,
                    "lon_0": lon_0, "lat_0": lat_0,
                    "lon_1": lon_0, "lat_1": lat_0,
                    "lon_2": lon_0+5, "lat_2": lat_0-5, 
                    "llcrnrlon": llcrnrlon, "llcrnrlat": llcrnrlat,
                    "urcrnrlon": urcrnrlon, "urcrnrlat": urcrnrlat,
                    "boundinglat": boundinglat, "satellite_height": 30*10**6}
        if args_all["lat_1"] == -args_all["lat_2"]:
            args_all["lat_2"] = +4

        args_p = {"projection": proj, "resolution":resolution}
        if proj in ["npaeqd", "nplaea", "npstere"]:
            if boundinglat > 0:                
                args_p["projection"] = "np"+proj[2:]
            elif boundinglat < 0:
                args_p["projection"] = "sp"+proj[2:]
            else:
                args_p["projection"] = proj[2:]
        for param_k in self.proj_pk[args_p["projection"]]:
            args_p[param_k] = args_all[param_k]
        # print "Proj", args_p["projection"], "H", height, "W", width, "Corners", (llcrnrlon, llcrnrlat), (urcrnrlon, urcrnrlat) #, "args", args_all
        # print "--- ARGS ALL\n", "\n".join(["%s:%s" % (k,v) for (k,v) in args_all.items()])
        # print "--- ARGS P\n", "\n".join(["%s:%s" % (k,v) for (k,v) in args_p.items()])
        try:
            bm = mpl_toolkits.basemap.Basemap(**args_p)
            # print "<< Basemap init succeded!", args_p
        except ValueError:
            # print ">> Basemap init failed!", args_p
            # print "H", height, "W", width, "Corners", (llcrnrlon, llcrnrlat), (urcrnrlon, urcrnrlat), "args", args_all
            bm = None 
        ### print "BM Corners", (bm.llcrnrlon, bm.llcrnrlat), (bm.urcrnrlon, bm.urcrnrlat)
        return bm, args_all
        
    def makeBasemapBack(self, bm=None):
        if bm is None:
            return
        draws, colors, more = self.getBasemapBackSetts()
        bounds_color, sea_color, contin_color, lake_color = colors["none"], colors["none"], colors["none"], colors["none"]
        if draws["rivers"]:
            bm.drawrivers(color=colors["sea_color"])
        if draws["coasts"]:
            bounds_color = colors["line_color"]
            bm.drawcoastlines(color=colors["line_color"])
        if draws["countries"]:
            bounds_color = colors["line_color"]
            bm.drawcountries(color=colors["line_color"])
        if draws["states"]:
            bounds_color = colors["line_color"]
            bm.drawstates(color=colors["line_color"])
        if draws["continents"]:
            contin_color = colors["land_color"]
        if draws["seas"]:
            sea_color = colors["sea_color"]
        if draws["lakes"]:
            lake_color = colors["sea_color"]
            
        if draws["parallels"]:
            tt = self.getParallelsRange()
            # print "parallels", tt
            bm.drawparallels(tt, linewidth=0.5, labels=[1,0,0,1])
        if draws["meridians"]:
            tt = self.getMeridiansRange()
            # print "meridians", tt
            bm.drawmeridians(tt, linewidth=0.5, labels=[0,1,1,0])

        func_map = {1: bm.shadedrelief, 2: bm.etopo, 3: bm.bluemarble}
        bd = False
        if more.get("map_back") in func_map:
            ### HERE http://matplotlib.org/basemap/users/geography.html
            try:
                func_map[more.get("map_back")](alpha=more["map_back_alpha"], scale=more["map_back_scale"])
                bd = True
            except IndexError:
                bd = False
                print "Impossible to draw the image map background!"
        if not bd:
            if bounds_color != colors["none"] or sea_color != colors["none"]:
                bm.drawmapboundary(color=bounds_color, fill_color=sea_color)
            if contin_color != colors["none"] or lake_color != colors["none"] or sea_color != colors["none"]:
                bm.fillcontinents(color=contin_color, lake_color=lake_color)
            # bm.drawlsmask(land_color=contin_color,ocean_color=sea_color,lakes=draws["lakes"])
            
    def getLidAt(self, x, y):
        ids_drawn = numpy.where(self.dots_draws["draw_dots"])[0]
        d = scipy.spatial.distance.cdist(self.coords_proj[0][:, ids_drawn, 0].T, [(x,y)])
        cands = [ids_drawn[i[0]] for i in numpy.argsort(d, axis=0)[:5]]
        i = 0
        while i < len(cands):
            path = Polygon(self.getCoordsP(cands[i]), closed=True)
            if path.contains_point((x,y), radius=0.0):
                return cands[i]
            i += 1
        return None
