import csv, re
import matplotlib.pyplot as plt
import numpy
import pdb

### FILES
SITES_KK = "../prepared_data/IUCN_all_nbspc3+_bio-kk.csv"
RED_SUPPS = "../xps/queries_suppids.txt"

### PARAMETERS
map_leg = ['Af', 'Am', 'As', 'Aw', 'BSh', 'BSk', 'BWh', 'BWk', 'Cfa', 'Cfb', 'Cfc', 'Csa', 'Csb', 'Cwa', 'Cwb', 'Cwc', 'Dfa', 'Dfb', 'Dfc', 'Dfd', 'Dsa', 'Dsb', 'Dsc', 'Dwa', 'Dwb', 'Dwc', 'Dwd', 'ET'] #, 'F']

# map_leg = ['A', 'B', 'C', 'D', 'E'] #, 'F']

colors_n = ['Af', 'Am', 'As', 'Aw', 'BSh', 'BSk', 'BWh', 'BWk', 'Cfa', 'Cfb','Cfc', 'Csa', 'Csb', 'Csc', 'Cwa','Cwb', 'Cwc', 'Dfa', 'Dfb', 'Dfc','Dfd', 'Dsa', 'Dsb', 'Dsc', 'Dsd','Dwa', 'Dwb', 'Dwc', 'Dwd', 'EF', 'ET', 'Ocean']
colors_k = ["#960000", "#FF0000", "#FF6E6E", "#FFCCCC", "#CC8D14", "#CCAA54", "#FFCC00", "#FFFF64", "#007800", "#005000", "#003200", "#96FF00", "#00D700", "#00AA00", "#BEBE00", "#8C8C00", "#5A5A00", "#550055", "#820082", "#C800C8", "#FF6EFF", "#646464", "#8C8C8C", "#BEBEBE", "#E6E6E6", "#6E28B4", "#B464FA", "#C89BFA", "#C8C8FF", "#6496FF", "#64FFFF", "#F5FFFF"]
colors_dict = dict(zip(*[colors_n, colors_k]))

classes_patt = ["A[fms]", "Aw", "B", "C", "[DE]"]
classes = ["A*", "Aw", "B*", "C*", "DE", ""]

rids = ["R%d" % i for i in range(1,11)]+ ["R1a", "R1b", "R1c", "R1d", "R1e", "R2a", "R2b", "R5a", "R5b", "R43", "R43a", "R43b", "R69", "R69a", "R69b", "R74"]
rrs = classes+rids

biomes = {}
for (bi, zzs) in enumerate([["R1", "R3", "R4", "R10"], ["R2", "R5", "R6", "R7", "R8", "R9"], ["R43"]]): #, "R69", "R74"]]):
    for zz in zzs:
        biomes[zz] = bi

nb_biomes = len(set(biomes.values()))


### MAIN
data = {}
map_vals = dict([(v,k) for (k,v) in enumerate(map_leg)])
map_counts = [0 for (k,v) in enumerate(map_leg)]

with open(SITES_KK) as csvfile:
    reader = csv.DictReader(csvfile, delimiter=',')
    ID_str = None
    for row in reader:
        if ID_str is None:
            if "ID" in row:
                ID_str = "ID"
            elif "id" in row:
                ID_str = "id"
        # if row['kk'] not in map_vals:
        #     map_vals[row['kk']] = [len(map_vals), 0]
        #     map_leg.append(row['kk'])
        elif row[ID_str] != "enabled_col":
            rv = row['kk']#[0]
            data[int(row[ID_str])] = map_vals[rv]
            map_counts[map_vals[rv]] += 1

########################################
##### PLOTTING
########################################
            
# stats = []
# for patt in classes_patt:    
#     stats.append(numpy.array(map_counts))
#     for i,l in enumerate(map_leg):
#         if not re.match(patt, l):
#             stats[-1][i] = 0
# stats.append(numpy.zeros(len(map_leg)))

# sizes_supps = []
# with open(RED_SUPPS) as csvfile:
#     reader = csv.DictReader(csvfile, delimiter='\t')
#     for row in reader:
#         supparts = [map(int, row[p].split()) for p in ["gamma", "alpha", "beta"]]
#         sizes_supps.append(len(supparts[0]))
#         dt = numpy.array([data[k] for k in supparts[0]])
#         stats.append(numpy.bincount(dt, minlength=len(map_leg)))
# ss = numpy.vstack(stats)


##### PRINT TIKZ PLOT LEGEND COMMANDS
########################################

# print """\\documentclass{article}
# \\usepackage{color}
# \\usepackage{tikz}

# \\newcommand{\\bplotHist}[3]{
# \\node[anchor=west] at (-8., -#2) {#1};
# \\foreach \\b/\\w/\\c in {#3}{ %0.00/21.72/kclass0,21.72/18.96/kclass1,40.68/2.71/kclass2}{
# \\draw [color=white,fill=\\c, fill opacity=.8, line width=.1pt] (\\b,{-#2-.45}) rectangle +(\\w,.9);}}
# """

# print "\n".join(["\definecolor{kclass%d}{HTML}{%s}" % (jc, colors_dict[map_leg[jc]].strip("#")) for jc in range(ss.shape[1])])

# print """
# \\begin{document}
# \\begin{tikzpicture}[xscale=.18, yscale=0.5]"""

# cs =  numpy.cumsum(numpy.hstack([numpy.zeros((ss.shape[0], 1)), ss]), axis=1)
# for jr in range(5):
#     sst = "\n".join(["\\node[anchor=center, inner sep=1pt, text=white] at (%.2f,%d)  {\\footnotesize{%s}}; %%%% %d" % (cs[jr,jc]/100. + ss[jr,jc]/200., 5-jr, map_leg[jc], ss[jr,jc]) for jc in range(ss.shape[1]) if ss[jr,jc] > 0])
#     print sst

# for jr in range(ss.shape[0]):
#     sst = ",".join(["%.2f/%.2f/kclass%d" % (cs[jr,jc]/100., ss[jr,jc]/100., jc) for jc in range(ss.shape[1]) if ss[jr,jc] > 0])
#     print "\\bplotHist{%s}{%d}{%s}" % (rrs[jr], jr, sst)

# print """\\end{tikzpicture}
# \\end{document}"""
   
# exit()


##### MAKE PLOT WITH PYPLOT
#############################
# ax = plt.subplot(1,1,1)
# xs = 4.5-numpy.arange(ss.shape[0])

# for i in range(ss.shape[1]):
#     if i > 0:
#         # ax.bar(left=xs, height=ss[:, i], width=0.8, bottom=numpy.sum(ss[:,:i], axis=1), color=colors_dict[map_leg[i]], linewidth=0.1, orientation="horizontal")        
#         ax.bar(bottom=xs, width=ss[:, i], height=0.8, left=numpy.sum(ss[:,:i], axis=1), color=colors_dict[map_leg[i]], linewidth=0.1, edgecolor='white', orientation="horizontal")
#     else:
#         # ax.bar(left=xs, height=ss[:, i], width=0.8, bottom=0, color=colors_dict[map_leg[i]], linewidth=0.1, orientation="horizontal")
#         ax.bar(bottom=xs, width=ss[:, i], height=0.8, left=0, color=colors_dict[map_leg[i]], linewidth=0.1, edgecolor='white', orientation="horizontal")
# ax.set_xlim(0,7050)
# ax.set_ylim(-27,6)
# ax.set_yticks(xs+0.5)

# ax.set_yticklabels(rrs)
        
# plt.show()


########################################
##### ENTROPY COMPUTATIONS
########################################


map_c = numpy.array(map_counts, dtype=numpy.float)
marg_ks = map_c/map_c.sum()
tot = map_c.sum()

sites, kk = zip(*data.items())
assign_kk = numpy.array(kk)
map_sites = dict([(v,k) for (k,v) in enumerate(sites)])


print "Entropies H(X|Y)/H(X) (nb of bits to encode membership in supp(R) knowing Koeppen classes / nb of bits without that knowledge)"

i = 0 
with open(RED_SUPPS) as csvfile:
    reader = csv.DictReader(csvfile, delimiter='\t')
    for row in reader:
        supparts = [map(int, row[p].split()) for p in ["gamma", "alpha", "beta"]]
        size_supps = float(len(supparts[0]))
        for j in range(1):
            if j == 0:
                supp = supparts[0]
            else:
                supp = sorted(numpy.random.choice(sites, len(supparts[0])))
            dt = numpy.array([data[k] for k in supp])
            counts = numpy.bincount(dt, minlength=len(map_leg))
            # dp_inr = counts/map_c
            hA = -(size_supps/tot)*numpy.log2(size_supps/tot) - (1-size_supps/tot)*numpy.log2(1-size_supps/tot)
            # cA = -size_supps*numpy.log2(size_supps/tot) - (tot-size_supps)*numpy.log2(1-size_supps/tot)
            # cB = 0
            hB = 0
            for ci, c in enumerate(counts):
                if c!= 0 and c!=map_c[ci]:
                    hB -= map_c[ci]/tot*(c/map_c[ci]*numpy.log2(c/map_c[ci]) + (1-c/map_c[ci])*numpy.log2(1-c/map_c[ci]))
                    # cB -= c*numpy.log2(c/map_c[ci]) + (map_c[ci]-c)*numpy.log2(1-c/map_c[ci])
            print " ===", rids[i], hB/hA
        i += 1
