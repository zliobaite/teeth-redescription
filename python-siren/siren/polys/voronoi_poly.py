#! /usr/local/bin/python

#### SHORTER VERSION, EXCLUDING SHAPELY POLYGONS FROM
### https://github.com/Softbass/py_geo_voronoi/blob/master/voronoi_poly.py

import voronoi
import sys, time

def update_maxmin(m_range, x, y):
  if (m_range["max_x"]<x):
    m_range["max_x"]=x
  if (m_range["max_y"]<y):
    m_range["max_y"]=y
  if (m_range["min_x"]>x):
    m_range["min_x"]=x
  if (m_range["min_y"]>y):
    m_range["min_y"]=y
  return m_range

def checkInRange(WorldRange,x,y):

  if x>=WorldRange[1] and x<=WorldRange[3]:
    if y<=WorldRange[0] and y>=WorldRange[2]:
      return True
  return False


def getExtremes(line, m_range):
  a,b,c=line

  if a==0:
    y0=(c-(a*m_range["min_x"]))/b
    y1=(c-(a*m_range["max_x"]))/b
    return [(m_range["min_x"],y0), (m_range["max_x"], y1)]

  if b==0:
    x0=(c-(b*m_range["min_y"]))/a
    x1=(c-(b*m_range["max_y"]))/a
    return [(x0, m_range["min_y"]), (x1, m_range["max_y"])]  
  
  x0=(c-(b*m_range["min_y"]))/a
  x1=(c-(b*m_range["max_y"]))/a

  y0=(c-(a*m_range["min_x"]))/b
  y1=(c-(a*m_range["max_x"]))/b

  return [(x0, m_range["min_y"]), (x1, m_range["max_y"]), (m_range["min_x"],y0), (m_range["max_x"], y1)]


def getExtreme(line, v_known, LR):
  
  global WorldRange

  global_extremes=getExtremes(line, {"min_y":WorldRange[2], "max_y":WorldRange[0], "min_x":WorldRange[1], "max_x":WorldRange[3]})

  v_unknown=None
  CurrentExtreme=None

  for extreme in global_extremes:

    if checkInRange(WorldRange,extreme[0],extreme[1])==False:
      #v_unknown=CurrentExtreme
      continue

    if v_known[0]<extreme[0] and LR==1:
      v_unknown=extreme

    if v_known[0]>extreme[0] and LR==0:
      v_unknown=extreme
    
    if CurrentExtreme:
      if CurrentExtreme[0]==extreme[0]:
        if CurrentExtreme:      

          if CurrentExtreme[1]<extreme[1] and LR==0:
            v_unknown=extreme
          else:
            v_unknown=CurrentExtreme
      
    CurrentExtreme=extreme

    #print LR, v_known, extreme, v_unknown

  return v_unknown    


def linkExtremes(point1, point2, m_range):
  #print "Link Extremes"
  #print point1, point2
  global WorldRange

  if point1[1]==point2[1] or point1[0]==point2[0]:
    #print "already done case"
    return [(point1, point2)]

  if point1[1]==-point2[1] or point1[0]==-point2[0]:
    #print "worst case"
    if point1[1]==-point2[1]:
      if abs(point1[0]-m_range["min_x"])+abs(point2[0]-m_range["min_x"])<abs(point1[0]-m_range["max_x"])+abs(point2[0]-m_range["max_x"]):
        output=[(point1, (WorldRange[1], point1[1])), ((WorldRange[1], point1[1]),(WorldRange[1], point2[1])), ((WorldRange[1], point2[1]), point2)]
      else:
        output=[(point1, (WorldRange[3], point1[1])), ((WorldRange[3], point1[1]),(WorldRange[3], point2[1])), ((WorldRange[3], point2[1]), point2)]
    else:
      if abs(point1[1]-m_range["min_y"])+abs(point2[1]-m_range["min_y"])<abs(point1[1]-m_range["max_y"])+abs(point2[1]-m_range["max_y"]):
        output=[(point1, (point1[0], WorldRange[2])), ((point1[0], WorldRange[2]),(point2[0], WorldRange[2])), ((point2[0], WorldRange[2]), point2)]
      else:
        output=[(point1, (point1[0], WorldRange[0])), ((point1[0], WorldRange[0]),(point2[0], WorldRange[0])), ((point2[0], WorldRange[0]), point2)]

    return output

  #print "one corner case"
  if point1[1]==WorldRange[0] or point1[1]==WorldRange[2]:
    #print "add x:", point2[0]
    #print "add y:", point1[1]
    output=[(point1, (point2[0], point1[1])), ((point2[0], point1[1]), point2)]
  else:
    #print "add x:", point1[0]
    #print "add y:", point2[1]
    output=[(point1, (point1[0], point2[1])), ((point1[0], point2[1]), point2)]
  return output


###########EEEEE


def VoronoiPolygonsMod(PointsMap, BoundingBox):
  global WorldRange

  if type(BoundingBox)==type([]) and len(BoundingBox)==4:
      WorldRange=BoundingBox
  else:
      return "Error in Bounding Box"
    
  currenttime=time.time()
  Sitepts = []
  pts = {}

  #print CurrentDate, PointsMap[PointsMap.keys()[0]]
  for grid, stn in PointsMap.items():

    x=float(stn[0])
    y=float(stn[1])
    station=grid
    #station.extend( stn[3:])
    #print x,y,station

    pts[ (x,y) ]=station
  
  stncounts=len(pts.keys())
  #print stncounts, "points"
  
  site_points=[]
  for pt in pts.keys():
    Sitepts.append(voronoi.Site(pt[0],pt[1]))
    site_points.append( (pt[0],pt[1]) )
      

  #print "Calculating Voronoi Lattice",
  
  siteList = voronoi.SiteList(Sitepts)
  context  = voronoi.Context()
  voronoi.Edge.EDGE_NUM=0   
  voronoi.voronoi(siteList,context)

  vertices=context.vertices
  lines=context.lines
  edges=context.edges
  
  #print edges

  #For Faster Access
  edge_dic={}
  for edge in edges:
    edge_dic[edge[0]]=edge[1:]
  
  triangles=context.triangles
  has_edge=context.has_edge

  voronoi_lattice={}

  m_range={}
  m_range["max_x"]=-9999999999
  m_range["max_y"]=-9999999999
  m_range["min_x"]=9999999999
  m_range["min_y"]=9999999999

  #Get the range!!
  for pnt in site_points:
    m_range=update_maxmin(m_range, pnt[0], pnt[1])

  #print "Getting the Polygons"

  prev_percent=0
  for station, ls in has_edge.items():


    voronoi_lattice[station]={}
    voronoi_lattice[station]["coordinate"]=site_points[station]
    voronoi_lattice[station]["info"]=pts[ site_points[station] ]

    polygon=[]
 
    prev_extreme=[]
    Verbose=True
    if Verbose: 
      current_percent=int(station/float(stncounts)*100)
      if current_percent!=prev_percent:
        #print station,"/", stncounts, current_percent, "% Done" 
        timeelapse=time.time()-currenttime
        #print station, timeelapse
        currenttime=time.time()

      prev_percent=current_percent

    #For every lines that the station owns
    for l in ls:
      e=edge_dic[l]

      v1=vertices[e[0]]
      v2=vertices[e[1]]
    
      if e[0] < 0 and checkInRange(WorldRange,v2[0],v2[1])==False: continue
      if e[1] < 0 and checkInRange(WorldRange,v1[0],v1[1])==False: continue

      if e[0] > -1 and e[1] > -1 and checkInRange(WorldRange,v1[0],v1[1])==False and checkInRange(WorldRange,v2[0],v2[1])==False:
        continue 

      if e[0] < 0 or checkInRange(WorldRange,v1[0],v1[1])==False:
        v1=getExtreme(lines[l],v2, LR=0)

        if len(prev_extreme)==0:
          prev_extreme=v1
        else:
          extreme_points=linkExtremes(prev_extreme, v1, m_range)
          for extreme_pair in extreme_points:
            polygon.append(extreme_pair)

      if e[1] < 0 or checkInRange(WorldRange,v2[0],v2[1])==False :
        v2=getExtreme(lines[l],v1, LR=1)

        if len(prev_extreme)==0:
          prev_extreme=v2
        else:
          extreme_points=linkExtremes(prev_extreme, v2, m_range)
          for extreme_pair in extreme_points:
            polygon.append(extreme_pair)

      if v1!=v2:
        polygon.append( (v1,v2) )

    if len(polygon)==0:
      raise IndexError("Station does not have meaningful polygon")
      sys.stderr.write ("\nThis station does not have meaningful polygon:")
      sys.stderr.write (str(pts[ site_points[station] ])+" at "+str(site_points[station])+"\n")
      for l in ls:
        e=edge_dic[l]

        v1=vertices[e[0]]
        v2=vertices[e[1]]
        
        sys.stderr.write(str(e[0])+","+str(e[1])+"\n")
        sys.stderr.write(str(v1)+","+str(v2)+"\n")

      voronoi_lattice.pop(station)
      continue
      
    voronoi_lattice[station]["obj_polygon"]=polygon
    
    #print polygon
        
  return voronoi_lattice
