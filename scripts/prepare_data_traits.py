import re
import numpy
import os
import pdb

### INPUT FILES
rd_folder = "../raw_data/"
traits_file = rd_folder+"data_dental_master.csv"
bio_file_all = rd_folder+"data_sites_IUCN_narrowA.csv"
occurence_file = rd_folder+"occurence_IUCN_%s.csv"
bio_legend_file = rd_folder+"bio_legend.txt"

### OUTPUT FILES
pr_folder = "../prepared_data/"
agg_file = pr_folder+"IUCN_%s_agg.csv"
aggrnd_file = pr_folder+"IUCN_%s_agg_rounded%d.csv"
bio_file = pr_folder+"IUCN_%s_bio.csv"

stats_file = "../misc/IUCN_ordfam_stats.tex"

### PARAMETERS
continents = ["EU", "AF", "NA", "SA"]
keep_traits = ["HYP","FCT_HOD","FCT_AL","FCT_OL","FCT_SF","FCT_OT","FCT_CM"]
bool_traits = ["HYP:1", "HYP:2","HYP:3","FCT_HOD:1","FCT_HOD:2","FCT_HOD:3","FCT_AL","FCT_OL","FCT_SF","FCT_OT","FCT_CM"]
keep_ordfam = ["FAMILY", "ORDER"]

key_species = "TAXON"
NA_val = "NA"

files_thres_out = [{"ext": "_nbspc3+", "thres_type": "num", "thres_side": 0, "thres_col": "NB_SPC", "thres_min": 3}]
round_dgt = 3

### FUNCTIONS
def load_legend_bio(bio_legend_file):
    leg = {}
    with open(bio_legend_file) as fp:
        for line in fp:
            parts = line.strip().split("=")
            leg[parts[0].strip()] = parts[0].strip()+":"+parts[1].strip()
    return leg
            
        
def load_lines_bio(bio_file, remove_vars, key_var, trans_vars={}):
    lines_bio = {}
    key_col = None
    sep = ","
    with open(bio_file) as fp:
        for line in fp:
            parts = line.strip().split(sep)
            if key_col is None:
                key_col = parts.index(key_var)
                keep_cols = [key_col]+[k for (k,v) in enumerate(parts) if v not in remove_vars+[key_var]]
                lines_bio[None] = sep.join([trans_vars.get(parts[k], parts[k])  for k in keep_cols])+"\n"
            else:
                lines_bio[parts[key_col]] = sep.join([parts[k] for k in keep_cols])+"\n"
    return lines_bio

    
def load_traits(traits_file, keep_traits, bool_traits, key_species):
    data_traits = {}
    head_traits = None
    sep = "\t"
    with open(traits_file) as fp:
        for line in fp:
            parts = line.strip().split(sep)
            if head_traits is None:
                head_traits = dict([(v,k) for (k,v) in enumerate(parts)])
            else:
                if True:
                    values = []
                    for kv in bool_traits:
                        tmp = re.match("(?P<trait>.*):(?P<val>[0-9]+)$", kv)
                        if tmp is not None:
                            if parts[head_traits[tmp.group("trait")]] == NA_val:
                                print parts[head_traits[key_species]], kv, "MISSING"
                                values.append(0)
                            else:
                                values.append(1*(parts[head_traits[tmp.group("trait")]] == tmp.group("val")))
                        else:
                            if parts[head_traits[kv]] == NA_val:
                                print parts[head_traits[key_species]], kv, "MISSING"
                                values.append(0)
                            else:
                                values.append(int(parts[head_traits[kv]]))
                    data_traits[parts[head_traits[key_species]]] = values
                # except ValueError:
                #     print parts[head_traits[key_species]], "MISSING"
    return data_traits, head_traits
    
def aggregate_traits(occurence_file, agg_file, data_traits, head_traits, bool_traits, lines_bio=None, bio_file=None):
    data_occurence = {}
    head_occurence = None
    sep = ","
    if bio_file is not None and lines_bio is not None:
        flb = open(bio_file, "w")
    else:
        flb = None
    fo = open(agg_file, "w")
    with open(occurence_file) as fp:
        for line in fp:
            parts = line.strip().split(sep)
            if head_occurence is None:
                head_occurence = dict([(k,v) for (k,v) in enumerate(parts)])
                fo.write(",".join(["ID"]+["MEAN_%s" % t for t in bool_traits]+["NB_SPC"])+"\n")
                if flb is not None:
                    flb.write(lines_bio[None])
            elif lines_bio is None or parts[0] in lines_bio:
                try:
                    present = [head_occurence[i] for (i,v) in enumerate(parts) if v =="1"]
                except ValueError:
                    print line
                    pdb.set_trace()
                
                data_mat = numpy.array([data_traits[p] for p in present])
                if data_mat.shape[0] == 0:
                    fo.write(",".join([parts[0]]+["0" for t in bool_traits]+["0"])+"\n")
                else:
                    fo.write(",".join([parts[0]]+["%f" % t for t in data_mat.mean(axis=0)]+["%d" % data_mat.shape[0]])+"\n")
                if flb is not None:
                    flb.write(lines_bio[parts[0]])
    if flb is not None:
        flb.close()
    fo.close()
    
def filter_nbspc(files_in, files_thres_out):
    fps = [open(file_in) for file_in in files_in]
    
    heads = []
    head_lines = []
    for fp in fps:
        head_lines.append(fp.readline())
        heads.append(dict([(v,k) for (k,v) in enumerate(head_lines[-1].strip().split(","))]))

    checked = []
    for ooo in files_thres_out: 
        out = dict(ooo)
        if out["thres_side"] >= 0 and out["thres_side"] < len(heads) and out["thres_col"] in heads[out["thres_side"]]:
            out["colid"] = heads[out["thres_side"]][out["thres_col"]]
            out["fps"] = []
            out["fns"] = []
            ### EXCLUDE FILTER COLUMN OR NOT
            excl = None # out["colid"]

            for file_in in files_in:
                parts = file_in.split("_")
                parts[-2]+= out["ext"]
                fname = "_".join(parts)
                out["fps"].append(open(fname, "w"))
                out["fns"].append(fname)
            for li, l in enumerate(head_lines):
                if li == out["thres_side"]:
                    out["fps"][li].write(",".join([p for (pi, p) in \
                                                       enumerate(l.strip().split(",")) if pi != excl])+"\n")
                else:
                    # out["fps"][li].write(l)
                    # pdb.set_trace()
                    ## out["fps"][li].write(l.strip('\n') + ",bioA:abs_bio13-bio14,bioB:bio4_corr"+"\n")
                    out["fps"][li].write(l.strip('\n') + ",bioA:abs_bio13-bio14"+"\n")

            out["count_lines"] = 0
            checked.append(out)
       
    stop = False
    while not stop:
        lines = [fp.readline() for fp in fps]
        if numpy.prod([len(line) for line in lines]) == 0:
            stop = True
        else:
            for out in checked:
                inclus = False
                if out["thres_type"] == "num":
                    v = float(lines[out["thres_side"]].split(",")[out["colid"]])
                    inclus = ("thres_min" not in out or v >= out["thres_min"]) and \
                      ("thres_max" not in out or v <= out["thres_max"])

                elif out["thres_type"] == "cat":
                    v = lines[out["thres_side"]].split(",")[heads[out["thres_side"]][out["thres_col"]]]
                    inclus = (v == out["thres_val"])

                if inclus:
                    for li, l in enumerate(lines):
                        if li == out["thres_side"]:
                            out["fps"][li].write(",".join([p for (pi, p) in \
                                                                enumerate(l.strip().split(",")) if pi != excl])+"\n")
                        else:
                            # out["fps"][li].write(l)
                            # pdb.set_trace()
                            parts = l.strip().split(",")
                            valA = abs(float(parts[heads[li]['bio13:PWetM']]) - float(parts[heads[li]['bio14:PDryM']]))
                            # valB = float(parts[heads[li]['bio4:TSeason']])
                            # if valA < 232 and float(parts[heads[li]['bio7:TRngY']]) > 30:
                            #     valB *= 10
                            # out["fps"][li].write(l.strip('\n') + (",%d,%d" % (valA, valB)) +"\n")
                            out["fps"][li].write(l.strip('\n') + (",%f" % valA) +"\n")

                    out["count_lines"] += 1
                        
    for out in checked:
        for fp in out["fps"]:
            fp.close()
        if out["count_lines"] == 0:
            for fn in out["fns"]:
                os.remove(fn)
            print "EMPTY %s removed..." % (", ".join(out["fns"])) 
            
    for fp in fps:
        fp.close()
    return checked

def round_values(in_file, out_file, round_dgt):
    ### first check that no information will be lost
    with open(in_file) as fp:
        head = fp.readline().strip().split(",")
        cols = [i for i,p in enumerate(head) if re.match("MEAN_", p)]   
    D = numpy.loadtxt(in_file, delimiter=",", skiprows=2, usecols=cols)
    print ">>> CHECK FOR LOSS OF INFO (all values should be True)"
    print [numpy.unique(numpy.around(numpy.unique(D[:,i]), round_dgt)).shape[0] == numpy.unique(D[:,i]).shape[0] for i in range(D.shape[1])]

    ### then round values
    fo = open(out_file, "w")
    head = None
    fmt = "%."+str(round_dgt)+"f"
    with open(in_file) as fp:
        for line in fp:
            parts = line.strip().split(",")
            if head is None:
                head = parts
                fo.write(line)
            elif parts[0] == "enabled_col":
                fo.write(line)
            else:
                for i,p in enumerate(head):
                    if re.match("MEAN_", p):
                        parts[i] = fmt % numpy.around(float(parts[i]), round_dgt)
                fo.write(",".join(parts)+"\n")

def collect_all(files_in, tk, continents, suffixes, round_dgt):

    for suffix in suffixes:
        for ffi, file_in in enumerate(files_in):
            parts = file_in.split("_")
            parts[-2]+= suffix
            fname = "_".join(parts)
            
            fpo = open(fname % tk, "w")
            if ffi == 0:
                fname_splits = fname % (tk+"-splits")
                fpos = open(fname_splits, "w")
            head = False
            for continent in continents:
                if os.path.exists(fname % continent):
                    with open(fname % continent) as fp:
                        for li, line in enumerate(fp):
                            if li == 0:
                                if not head:                                    
                                    if ffi == 0:
                                        fpos.write(line.strip()+",folds_split_C\n")
                                        fpos.write(",".join(["enabled_col"]+ \
                                                            ["T" for i in range(len(line.strip().split(","))-2)]+["F,F\n"]))
                                    fpo.write(line)
                                    if ffi == 0:
                                        fpo.write(",".join(["enabled_col"]+ \
                                                            ["T" for i in range(len(line.strip().split(","))-1)])+"\n")
                                    else:
                                        fpo.write(",".join(["enabled_col"]+ \
                                                               ["T" for i in range(len(line.strip().split(","))-2)])+",F\n")


                                    head = True
                            else:
                              if ffi == 0:
                                  fpos.write(line.strip()+",F:%s\n" % continent)
                              fpo.write(line)
            if ffi == 0:
                fpos.close()
            fpo.close()

        parts = fname_splits.split(".")
        fname_rnd = ".".join(parts[:-1])+("_rounded%d." % round_dgt) + parts[-1]        
        round_values(fname_splits, fname_rnd, round_dgt)

def load_ordfam(traits_file, keep_ordfam, key_species):
    data_ordfam = {}
    head_ordfam = None
    sep = "\t"
    with open(traits_file) as fp:
        for line in fp:
            parts = line.strip().split(sep)
            if head_ordfam is None:
                head_ordfam = dict([(v,k) for (k,v) in enumerate(parts)])
            else:
                if True:
                    values = []
                    for kv in keep_ordfam:
                        if kv == "FAMILY":
                            for f,t in [("Galagonidae", "Galagidae"),
                                            ("Loridae", "Lorisidae"),
                                            ("Rhinoceratidae", "Rhinocerotidae")]:
                                if parts[head_ordfam[kv]] == f:
                                    parts[head_ordfam[kv]] = t
                        if parts[head_ordfam[kv]] == NA_val:
                            print parts[head_ordfam[key_species]], kv, "MISSING"
                            values.append(0)
                        else:
                            values.append(parts[head_ordfam[kv]])
                    data_ordfam[parts[head_ordfam[key_species]]] = values
                # except ValueError:
                #     print parts[head_ordfam[key_species]], "MISSING"                    
    return data_ordfam, head_ordfam
    
def aggregate_counts(occurence_file, data_ordfam, head_ordfam, keep_ordfam, lines_bio=None):
    data_occurence = {}
    head_occurence = None
    sep = ","
    counts = {}
    # keep_ordfam = [ss.replace("_Kari", "") for ss in keep_ordfam]
    for ck in [0,3]:
        counts[ck] = dict([("SITES",0)]+[(kk, {}) for kk in keep_ordfam])
    with open(occurence_file) as fp:
        for line in fp:
            parts = line.strip().split(sep)
            if head_occurence is None:
                head_occurence = dict([(k,v) for (k,v) in enumerate(parts)])
            elif lines_bio is None or parts[0] in lines_bio:
                try:
                    present = [head_occurence[i] for (i,v) in enumerate(parts) if v =="1"]
                except ValueError:
                    print line
                    pdb.set_trace()

                nb_spc = len(present)
                data_mat = [data_ordfam[p] for p in present]
                for ck in counts.keys():
                    if nb_spc >= ck:                        
                        counts[ck]["SITES"] += 1
                for i, cs in enumerate(map(set, zip(*data_mat))):
                    for ck in counts.keys():
                        if nb_spc >= ck:
                            for cc in cs:
                                counts[ck][keep_ordfam[i]][cc] = counts[ck][keep_ordfam[i]].get(cc, 0) + 1
    return counts


def make_counts_table(data_ordfam, continents, counts_all):    
    pairs = sorted(set([(ka, kb) for (kb,ka) in data_ordfam.values()]))

    table = """\\begin{table}[h]
\\caption{Number of sites from each continent containing taxa from the given order or family, after/before filtering out sites with fewer than three taxa.}\\label{fig:spc_counts}
\\vspace{2ex} \\centering
\\begin{tabular}{@{\\hspace*{3ex}}l@{\\hspace*{2ex}}ccr@{~/~}rc@{\\hspace*{2ex}}cr@{~/~}rc@{\\hspace*{2ex}}cr@{~/~}rc@{\\hspace*{2ex}}cr@{~/~}rc@{\\hspace*{3ex}}} \n\\toprule\n"""
    
    table += " & & "+ "&".join(["\\multicolumn{4}{c}{\\textsc{%s}}" % c for c in continents]) +" \\\\\n\\midrule\n"
    table += " & & & ".join(["Nb.\ sites" ] + ["%d & %d" % tuple([counts_all[continent][ck]["SITES"] for ck in [3,0]]) for continent in continents])+" & \\\\\n"
    for pi, pair in enumerate(pairs):    
        if pi == 0 or pairs[pi-1][0] != pair[0]:
            table += "[0.5em]\n"+" & & & ".join(["\\textbf{\\textit{%s}}" % pair[0]] + ["%d & %d" % tuple([counts_all[continent][ck]["ORDER"].get(pair[0], 0) for ck in [3,0]]) for continent in continents])+" & \\\\\n"
        table += " & & & ".join(["\\textit{%s}" % pair[1]] + ["%d & %d" % tuple([counts_all[continent][ck]["FAMILY"].get(pair[1], 0) for ck in [3,0]]) for continent in continents])+" & \\\\\n"
    table += """\\bottomrule\n\\end{tabular}\n\\end{table}"""
    return table

        
      
### MAIN
data_traits, head_traits = load_traits(traits_file, keep_traits, bool_traits, key_species)

bio_leg = load_legend_bio(bio_legend_file)
bio_leg.update({"lon_bio":"longitude","lat_bio":"latitude", "SITE": "ID"})
lines_bio = load_lines_bio(bio_file_all, ["CONT","NO_SPECIES","NO_ORDERS","NO_FAMILIES","GlobalID"], "SITE", bio_leg)

for continent in continents:
    aggregate_traits(occurence_file % continent, agg_file % continent, data_traits, head_traits, bool_traits, lines_bio, bio_file % continent)
    filter_nbspc([agg_file % continent, bio_file % continent], files_thres_out)
    
collect_all([agg_file, bio_file], "all", continents, suffixes=[fto["ext"] for fto in files_thres_out], round_dgt=round_dgt)

############# COMPUTING COUNTS
data_ordfam, head_ordfam = load_ordfam(traits_file, keep_ordfam, key_species)
counts_all = {}
for continent in continents:
    counts_all[continent] = aggregate_counts(occurence_file % continent, data_ordfam, head_ordfam, keep_ordfam, lines_bio)
    
table = make_counts_table(data_ordfam, continents, counts_all) 
with open(stats_file, "w") as fo:
    fo.write(table)
