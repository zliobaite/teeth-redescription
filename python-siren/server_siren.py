#!/usr/bin/env python
import getopt, sys, os

from siren.work.classWorkServer import WorkServer

if __name__ == '__main__':
    args = {}
    if len(sys.argv) > 1:
        args = dict([(k.strip("-"), v) for (k,v) in getopt.getopt(sys.argv[1:], "", ["portnum=", "authkey=", "max_k=", "chroot=","setuid=","setgid="])[0]])
    for k in ["portnum", "max_k", "setuid", "setgid"]:
        if k in args:
            try:
                args[k] = int(args[k])
            except ValueError:
                del args[k]
    if "setuid" in args:
	if "setgid" in args:
		# We need to drop GID before we drop UID
		os.setgid(args.pop("setgid"))
        os.setuid(args.pop("setuid"))
    else: # setuid not in args
	if "setgid" in args:
		os.setgid(args.pop("setgid"))
    if "chroot" in args:
        os.chroot(args.pop("chroot"))
    WorkServer(**args)
