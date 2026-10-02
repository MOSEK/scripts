#!/usr/bin/env python3
from pathlib import Path
import os,sys
import argparse
import json
import platform
import sysconfig

A = argparse.ArgumentParser()
A.add_argument('--format','-f',default="brief",choices=['brief','plain','json'])
A.add_argument('--platform','-p',choices=['linux64x86','linuxaarch64','osxaarch64','win64x86'])

a = A.parse_args()

home = os.environ.get('HOME')
profile = os.environ.get('USERPROFILE')
localdata = os.environ.get('LOCALAPPDATA')
if home is not None: home = Path(home)
if profile is not None: profile = Path(profile)
if localdata is not None: localdata = Path(localdata)

if a.platform is not None:
    pfname = a.platform
elif sys.platform == 'linux':
    if platform.machine() in ['x86_64','AMD64']:
        pfname = 'linux64x86'
    elif platform.machine() in ['arm64','aarch64']:
        pfname = 'linuxaarch64'
    else:
        print("System/machine architecture not supported")
        sys.exit(1)
elif sys.platform == 'win32':
    if platform.machine() in ['x86_64','AMD64']:
        pfname = 'win64x86'
    else:
        print("System/machine architecture not supported")
        sys.exit(1)
elif sys.platform == 'darwin':
    if platform.machine() in ['arm64','aarch64']:
        pfname = 'osxaarch64'
    else:
        print("System/machine architecture not supported")
        sys.exit(1)
else:
    print("System not supported")
    sys.exit(1)

search = []
if home is not None:
    search.append(home)
    search.append(home.joinpath('.local'))
    search.append(home.joinpath('local'))
    search.append(home.joinpath('Applications'))
if profile is not None:
    search.append(profile)
    search.append(profile.joinpath('.local'))
    search.append(profile.joinpath('local'))
if localdata is not None:
    search.append(localdata)
if pfname == 'win64x86':
    mosekbin = f'mosek.exe'
else:
    mosekbin = f'mosek'

mosek_inst = []
mosek_in_path : list[Path] = []
mosek_distro_from_paths = []
mosek_origins = []
for p in search:
    base = p.joinpath('mosek')
    if base.exists():
        for v in base.iterdir():
            if v.is_dir():
                pfdir = v.joinpath('tools','platform',pfname)
                bindir = pfdir.joinpath('bin')
                if bindir.exists():
                    mosekfullpath = bindir.joinpath(mosekbin)
                    if mosekfullpath.exists():
                        mosek_inst.append(pfdir)

for p in os.environ['PATH'].split(os.pathsep):
    p = Path(p)
    if p.exists():
        mosekbinpath = p.joinpath(mosekbin)
        if mosekbinpath.exists():
            mosek_in_path.append(mosekbinpath)
if sys.platform != 'win32':
    for px in mosek_in_path:
        if px.is_symlink():
            p = px.resolve()
            if p.exists():
                mosek_origins.append((px,p.parent))
        else:
            mosek_origins.append((px,None))


mosek_inst = sorted(list({ str(p) for p in mosek_inst }))

if a.format == 'brief':
    print('# Installations:')
    for p in mosek_inst:
        print(p)
elif a.format == 'plain':
    print('Installations found:')
    for p in mosek_inst:
        print(f'\t{p}')
    print('MOSEK on the path:')
    for (px,p) in mosek_origins:
        if p is not None:
            print(f'\t{px} -> {p}')
        else:
            print(f'\t{px}')
elif a.format == 'json':

    d = {
        'installations' : mosek_inst,
        'mosek_in_path' : [ [ str(px),str(p) ] if p is not None else str(px) for  (px,p) in mosek_origins ]
    }
    print(json.dumps(d))
