#!/usr/bin/env python3
import argparse
import os,sys
from pathlib import Path
import tempfile
import urllib.request
import re
import platform
import shutil
import tarfile,zipfile
import subprocess



if 'HOME' in os.environ:
    home_dir = Path(os.environ['HOME'])
    home_local = home_dir.joinpath('.local')
    download_dir = home_dir.joinpath('Downloads')
elif 'USERPROFILE' in os.environ:
    home_dir = Path(os.environ['USERPROFILE'])
    download_dir = home_dir.joinpath('Downloads')
    if 'LOCALAPPDATA' in os.environ:
        home_local = Path(os.environ['LOCALAPPDATA'])
    else:
        home_local = home_dir
else:
    home_dir = None
    home_local = None
    download_dir = None

if 'PROGRAMFILES' in os.environ:
    global_path = Path(os.environ['PROGRAMFILES'])
else:
    global_path = Path('/opt')

if sys.platform == 'linux':
    if platform.machine() in ['AMD64','x86_64']: default_platform = 'linux64x86'
    else: default_platform = 'linuxaarch64'
    distro_ext = '.tar.bz2'
elif sys.platform == 'darwin':
    default_platform = 'osxaarch64'
    distro_ext = '.tar.bz2'
else: # sys.platform == 'win32':
    default_platform = 'win64x86'
    distro_ext = '.zip'

try:
    username = subprocess.check_output(['whoami']).split(b'/',1)[-1].decode('utf-8',errors='ignore').strip()
except:
    username = None

def majminver(s):
    o = re.match(r'([0-9]+)\.([0-9]+)(?:\.([0-9]+))?',s)
    if o is None:
        raise argparse.ArgumentError(None,"Invalid version string")
    elif o.group(3):
        return (int(o.group(1)),int(o.group(2)),int(o.group(3)))
    else:
        return (int(o.group(1)),int(o.group(2)))

A = argparse.ArgumentParser(description="""Download and install MOSEK""")
A.add_argument('--prefix','-p', help="Install to prefix, placing the 'mosek' directory at this location")
A.add_argument('--global','-g',default=False, action="store_true",help="Install globally. Requires root privileges. This installs to the 'Program Files' folder on Windows, otherwise to '/opt'")
A.add_argument('--user','-u',default=False, action="store_true", help=f"Install in current user's home directory {home_local}")
A.add_argument('--no-symlinks',default=False,action="store_true",help="Do not create global symlinks (Mac OS X and Linux)")
A.add_argument('--version', help="Select specific MOSEK version to download and install",type=majminver,metavar="N.N[.N]")
A.add_argument('--test',default=False,action="store_true",help="Basic installation test")
A.add_argument('--test-license',default=False,action="store_true",help="Basic test for availability of a license.")
A.add_argument('--dry-run','-x',default=False,action="store_true",help="Dry run - do not actually fetch or install anything")
A.add_argument('--platform',choices=['linux64x86','linuxaarch64','osx64x86','win64x86'],default=default_platform,help="Choose platform binary to install")

a = A.parse_args()

make_symlinks = False
global_install = False

if a.dry_run:
    print("=== DRY RUN",file=sys.stderr)

if   a.prefix is not None:
    make_symlinks = False
    install_prefix = Path(a.prefix)
    print(f"=== Install to prefix: {install_prefix}",file=sys.stderr)
elif a.user:
    make_symlinks = False
    install_prefix = home_dir
    print(f"=== Install to user directory: {install_prefix}",file=sys.stderr)
elif getattr(a,'global'):
    make_symlinks = not a.no_symlinks
    install_prefix = global_path
    global_install = True
    print(f"=== Install globally: {install_prefix}",file=sys.stderr)
elif username == 'root':
    make_symlinks = not a.no_symlinks
    install_prefix = global_path
    global_install = True
    print(f"=== Install globally: {install_prefix}",file=sys.stderr)
elif username == 'Administrator':
    make_symlinks = not a.no_symlinks
    install_prefix = global_path
    global_install = True
    print(f"=== Install globally: {install_prefix}",file=sys.stderr)
elif home is not None:
    make_symlinks = False
    install_prefix = home_dir
else:
    install_prefix = home_dir
    print(f"=== Install to user default: {install_prefix}",file=sys.stderr)

if install_prefix is None:
    print("=== Could not determine install prefix",file=sys.stderr)
    sys.exit(1)

install_prefix = install_prefix.absolute()

if a.version is not None:
    if len(a.version) == 2:
        (major,minor) = a.version
        with urllib.request.urlopen(f'https://download.mosek.com/stable/{major}.{minor}/version') as r:
            mosekverstr = r.read().strip().decode('ascii',errors='ignore')
        mosekver2 = f'{major}.{minor}'
    else:
        (major,minor,build) = a.version
        mosekverstr = f'{major}.{minor}.{build}'
        mosekver2 = f'{major}.{minor}'
else:
    with urllib.request.urlopen(f'https://download.mosek.com/stable/latest/version') as r:
        mosekverstr = r.read().strip().decode('ascii',errors='ignore')
    mosekver2 = mosekverstr.rsplit('.',1)[0]

try: os.makedirs(str(install_prefix))
except: pass

mosek_base    = install_prefix.joinpath('mosek',mosekver2)
mosek_bin_dir = mosek_base.joinpath('tools','platform',a.platform,'bin')

print(f'=== Downloading MOSEK {mosekverstr}',file=sys.stderr)

if a.dry_run:
    print(f"=== Unpacking to {install_prefix}",file=sys.stderr)
else:
    with urllib.request.urlopen(f'https://download.mosek.com/stable/{mosekverstr}/mosektools{a.platform}{distro_ext}') as req:
        with tempfile.NamedTemporaryFile(prefix=f"mosektools{a.platform}-{mosekverstr}-",suffix=distro_ext,delete_on_close=False) as f:
            shutil.copyfileobj(req,f)
            f.flush()
            print(f"=== Unpacking to {install_prefix}",file=sys.stderr)
            f.close()
            if distro_ext == '.zip':
                with zipfile.ZipFile(f.name,'r') as zf:
                    zf.extractall(install_prefix)
            else:
                with tarfile.open(f.name) as zf:
                    zf.extractall(str(install_prefix))

# symlinks / linux and osx
if make_symlinks and global_install:
    if sys.platform == 'linux':
        print("=== Making global symlinks",file=sys.stderr)
        if not a.dry_run:
            os.symlink(mosek_bin_dir.joinpath('mosek'),   Path('/usr/bin/mosek'))
            os.symlink(mosek_bin_dir.joinpath('mosekcli'),Path('/usr/bin/mosekcli'))

            for path in [ mosek_bin_dir.joinpath(f'libmosek64.so.{mosekver2}'),
                          mosek_bin_dir.joinpath(f'libmosek64.so.{mosekver2}'),
                          mosek_bin_dir.joinpath('libmosekstable12.so'),
                          mosek_bin_dir.joinpath('libmosekstable12-link.so') ]:
                target = Path(f'/usr/lib').joinpath(path.name)
                if target.exists():
                    target.unlink()
                if path.exists():
                    os.symlink(path,target)

    elif sys.platform == 'darwin':
        if not a.dry_run:
            os.symlink(mosek_bin_dir.joinpath('mosek'),   Path('/usr/bin/mosek'))
            os.symlink(mosek_bin_dir.joinpath('mosekcli'),Path('/usr/bin/mosekcli'))

            for path in [ mosek_bin_dir.joinpath(f'libmosek64.{mosekver2}.dylib'),
                          mosek_bin_dir.joinpath(f'libmosek64.{mosekver2}.dylib'),
                          mosek_bin_dir.joinpath('libmosekstable12.dylib'),
                          mosek_bin_dir.joinpath('libmosekstable12-link.dylib') ]:
                target = Path(f'/usr/lib').joinpath(path.name)
                if target.exists():
                    target.unlink()
                if path.exists():
                    os.symlink(path,target)

# test
errors = []
if a.test:
    print(f'=== Test...',file=sys.stderr)
    if not not a.dry_run:
        mosekbin = mosek_bin_dir.joinpath('mosek')
        try: subprocess.check_call([ mosekbin,'-version'])
        except: errors.append(f'FAILED to execute mosek command line tool: {mosekbin}')

        if make_symlinks:
            try: subprocess.check_call([ 'mosek','-version' ])
            except: errors.append(f'FAILED to execute mosek command line tool via PATH')

if a.test_license:
    print(f'=== Test license...',file=sys.stderr)
    if not not a.dry_run:
        mosekbin = mosek_bin_dir.joinpath('mosekcli')
        try: subprocess.check_call([ mosekbin,'-read', mosek_base.joinpath('tools','examples','data','25fv47.mps')])
        except: errors.append(f'FAILED to solve problem with: {mosekbin}')
