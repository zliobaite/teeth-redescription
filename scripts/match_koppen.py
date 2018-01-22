import numpy
import pdb

KOP_IN = "../misc/Koeppen-Geiger-ASCII.txt"
pr_folder = "../prepared_data/"
SITES_IN = pr_folder+"IUCN_all_nbspc3+_bio.csv"
SITES_KK = pr_folder+"IUCN_all_nbspc3+_bio-kk.csv"

print "Assigning sites to Koeppen-Geiger classes..."
print "Data input: %s" % SITES_IN
print "Data output: %s" % SITES_KK

kop_data = []
kop_val = []
with open(KOP_IN) as fp:
    for li, line in enumerate(fp):
        parts = line.strip().split()
        if li > 0:            
            kop_data.append((float(parts[1]),float(parts[0])))
            kop_val.append(parts[2])
            
site_data = []
site_lines = []
head = []
with open(SITES_IN) as fp:
    for li, line in enumerate(fp):
        parts = line.strip().split(",")
        if li > 1:
            site_data.append((float(parts[1].strip('"')),float(parts[2].strip('"'))))
            site_lines.append(line.strip())
        else:
            head.append(line.strip())
            
kop_data = numpy.array(kop_data)
site_data = numpy.array(site_data)

# print numpy.max(kop_data[:,0]), numpy.max(kop_data[:,1])
kamp = numpy.array(range(kop_data.shape[0])) #numpy.where((kop_data[:,0] > -160) & (kop_data[:,1] > 60))[0]
samp = numpy.array(range(site_data.shape[0])) #numpy.where((site_data[:,0] > 160) & (site_data[:,1] > 60))[0]
# print samp.shape

rkop_data = numpy.round(2*numpy.array(kop_data[kamp,:])+0.25)
rsite_data = numpy.round(2*numpy.array(site_data[samp,:])+0.25)
dd = dict([(tuple(rkop_data[i,:]), i) for i in range(rkop_data.shape[0])])

dx = [dd.get(tuple(rsite_data[i,:]),-1) for i in range(rsite_data.shape[0])]
# rsite_data = numpy.round(2*numpy.array(site_data[samp,:])+0.5)

miss = [ci for (ci,c) in enumerate(dx) if c<0]
nf1, nf2, nf3 = ([], [], [])
for m in miss:
    found = []
    for (offx, offy) in [(0,1), (0,-1), (1,0), (-1,0)]:
        if (rsite_data[m,0]+offx, rsite_data[m,1]+offy) in dd:
            found.append((offx, offy))
    if len(found) == 0:
        nf1.append(m)
        for (offx, offy) in [(1,1), (1,-1), (-1,1), (-1,-1)]:
            if (rsite_data[m,0]+offx, rsite_data[m,1]+offy) in dd:
                found.append((offx, offy))
    if len(found) == 0:
        nf2.append(m)
        for (offx, offy) in [(1,2), (1,-2), (2,1), (-2,1), (-1,2), (-1,-2), (2,-1), (-2,-1), (2,2), (-2,-2)]:
            if (rsite_data[m,0]+offx, rsite_data[m,1]+offy) in dd:
                found.append((offx, offy))
    if len(found) == 0:
        nf3.append(m)
    else:
        di = 0
        if len(found) > 1:
            ds = [dd[(rsite_data[m,0]+offx, rsite_data[m,1]+offy)] for (offx, offy) in found]
            di = numpy.argmin([numpy.sum((kop_data[ds[di],:]-site_data[m,:])**2) for di in range(len(ds))])
        offx, offy = found[di]
        dx[m] = dd[(rsite_data[m,0]+offx, rsite_data[m,1]+offy)]
        # print "NOT FOUND" #, ci, found
#pdb.set_trace()


with open(SITES_KK, "w") as fp:
    p = head[0].split(" # ")
    fp.write("\n".join([p[0]+',kk', head[1]+',F']+["%s,%s" % (site_lines[ki], kop_val[k]) for ki,k in enumerate(dx)]))
    ## fp.write("\n".join([p[0]+',"ki","kk # '+p[1], head[1]+',"F","F"']+["%s,%d,%s" % (site_lines[ki], k, kop_val[k]) for ki,k in enumerate(dx[:10])]))
print "Done."
