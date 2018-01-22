import os, re

CHANGELOG_FILE = os.path.split(os.path.dirname(__file__))[0]+"/CHANGELOG"

def getVersion():
    version = None
    changes = []
    if os.path.isfile(CHANGELOG_FILE):
        with open(CHANGELOG_FILE) as fp:        
            for line in fp:
                tmp = re.match("^v(?P<version>[0-9\.]*)$", line)
                if tmp is not None:
                    if version is None:
                        version = tmp.group("version")
                    else:
                        return version, changes
                elif version is not None and len(line.strip("[\n\*\- ]")) > 0:
                    changes.append(line.strip("[\n\*\- ]"))
                    
    return "", []

def getExtLinks(cv):

    return {'contact_email': ("%s"+cv["MAINTAINER_EMAIL"], None) , #cv["MAINTAINER_EMAIL"]),
            'project_url': (cv["PROJECT_URL"]+"%s", cv["PROJECT_NAME"]),
            'code_url': (cv["CODE_URL"]+"%s", cv["PACKAGE_NAME"]),
            'pdf_link': (cv["PDFS_URL"]+"%s", "pdf"),
            'data_link': (cv["DATA_URL"]+"%s", "prepared dataset"),
            'src_release': (cv["DOWNLOAD_URL"]+"?loc="+cv["CODE_LOC"]+"&file="+cv["PACKAGE_NAME"]+"-"+cv["SPEC_RELEASE"]+"%s",
                            cv["PROJECT_NAME"]+" (v"+cv["SPEC_RELEASE"]+") "),
            'deb_release': (cv["DOWNLOAD_URL"]+"?loc="+cv["CODE_LOC"]+"&file="+cv["PACKAGE_NAME"]+"_"+cv["SPEC_RELEASE"]+"_all%s",
                            cv["PROJECT_NAME"]+" (v"+cv["SPEC_RELEASE"]+") "),
            'mac_release': (cv["DOWNLOAD_URL"]+"?loc="+cv["CODE_MAC_LOC"]+"&file="+cv["PROJECT_NAME"]+"%s",
                            cv["PROJECT_NAME"]+" (v"+cv["VERSION_MAC"]+") "),
            'win_release': (cv["DOWNLOAD_URL"]+"?loc="+cv["CODE_LOC"]+"&file=install_"+cv["PROJECT_NAMELOW"]+"_"+cv["SPEC_RELEASE"]+"%s",
                            cv["PROJECT_NAME"]+" (v"+cv["SPEC_RELEASE"]+") ")
            }


            # 'src_release': (cv["CODE_URL"]+cv["PACKAGE_NAME"]+"-"+cv["SPEC_RELEASE"]+"%s",
            #                 cv["PROJECT_NAME"]+" (v"+cv["SPEC_RELEASE"]+") "),
            # 'deb_release': (cv["CODE_URL"]+cv["PACKAGE_NAME"]+"_"+cv["SPEC_RELEASE"]+"_all%s",
            #                 cv["PROJECT_NAME"]+" (v"+cv["SPEC_RELEASE"]+") "),
            # 'mac_release': (cv["CODE_MAC_URL"]+cv["PROJECT_NAME"]+"%s",
            #                 cv["PROJECT_NAME"]+" (v"+cv["VERSION_MAC"]+") "),
            # 'win_release': (cv["CODE_URL"]+"install_"+cv["PROJECT_NAMELOW"]+"_"+cv["SPEC_RELEASE"]+"%s",
            #                 cv["PROJECT_NAME"]+" (v"+cv["SPEC_RELEASE"]+") ")



version, changes = getVersion()

home_eg = "https://members.loria.fr/EGalbrun/"
home_siren = "http://siren.gforge.inria.fr/"

common_variables = {
    "PROJECT_NAME": "Siren",
    "PROJECT_NAMELOW": "siren",
    "PACKAGE_NAME": "python-siren",
    "MAIN_FILENAME": "exec_siren.py",
    "VERSION": version,
    "VERSION_MAC": "3.0.0",
    "VERSION_MAC_UNDERSC": "",
    "LAST_CHANGES_LIST": changes,
    "LAST_CHANGES_STR": "    * " + "\n    * ".join(changes),
    "LAST_CHANGES_DATE": "Tue, 3 Jan 2017 10:00:00 +0100",
    "PROJECT_AUTHORS": "Esther Galbrun and Pauli Miettinen",
    "MAINTAINER_NAME": "Esther Galbrun",
    "MAINTAINER_LOGIN": "egalbrun",
    "MAINTAINER_EMAIL": "esther.galbrun@inria.fr",
    "PDFS_URL": home_eg+"resources/",
    "DATA_URL": home_eg+"resources/",
    "PROJECT_URL": home_siren,
    "CODE_URL": home_siren+"/code/",
    "CODE_MAC_URL": "http://www.cs.helsinki.fi/u/pamietti/data/siren/",
    "DOWNLOAD_URL": home_siren+"php/download.php",
    "CODE_LOC": "1",
    "CODE_MAC_LOC": "2",
    "PROJECT_DESCRIPTION": "Interactive Redescription Mining",
    "PROJECT_DESCRIPTION_LINE": "Siren is an interactive tool for visual and interactive redescription mining.",
    "PROJECT_DESCRIPTION_LONG": """This provides the ReReMi redescription mining algorithm and the Siren interface for interactive mining and visualization of redescriptions.""",
    "COPYRIGHT_YEAR_FROM": "2012",
    "COPYRIGHT_YEAR_TO": "2017"}

#    "DOWNLOAD_URL": "http://www.loria.fr/~egalbrun/log/download.php",

