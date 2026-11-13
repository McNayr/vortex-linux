#!/usr/bin/env python3
"""Make a packaged Vortex build movable: point native modules at their own folder.

Vortex's FOMOD installer module (modinstaller.node) is packed with an absolute
RUNPATH into the build tree, where it finds ModInstaller.Native.so. A copied or
moved build then fails to load it ("Failed to load native FOMOD module ...
cannot open shared object file") unless the build tree is still there
(upstream issue Nexus-Mods/Vortex#23565). The library already sits next to
the module in the package, so $ORIGIN is enough.

  vortex-relocate.py --check DIST    list ELF files with an absolute RUNPATH (exit 1 if any)
  vortex-relocate.py --apply DIST    point them at $ORIGIN (original kept as <file>.relocate-orig)
  vortex-relocate.py --revert DIST   put the originals back

Exit codes: 0 done or clean, 1 --check found absolute paths, 2 --apply refused,
3 patchelf missing.

--apply refuses, and changes nothing, when a library a module needs is neither
next to it nor a system library: $ORIGIN would then break loading in place.
The new file replaces the old one by rename, so a running Vortex keeps the
module it already loaded. Needs patchelf.
"""
import argparse
import os
import shutil
import subprocess
import sys

PATCHELF = os.environ.get("PATCHELF") or shutil.which("patchelf") or os.path.expanduser("~/.local/bin/patchelf")
BACKUP = ".relocate-orig"
TEMP = ".relocating"


def is_elf(path):
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except OSError:
        return False


def runpath_of(path):
    r = subprocess.run([PATCHELF, "--print-rpath", path], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def absolute_runpaths(dist):
    """Yield (path, runpath) for ELF files under dist whose RUNPATH/RPATH names an absolute directory."""
    for root, dirs, files in os.walk(dist):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(root, name)
            if name.endswith((BACKUP, TEMP)) or os.path.islink(path) or not is_elf(path):
                continue
            runpath = runpath_of(path)
            if any(entry.startswith("/") for entry in runpath.split(":")):
                yield path, runpath


def needed_libs(path):
    r = subprocess.run([PATCHELF, "--print-needed", path], capture_output=True, text=True, check=True)
    return r.stdout.split()


def system_libs():
    """Names the dynamic loader finds without a RUNPATH: the ldconfig cache plus the standard folders."""
    names = set()
    try:
        cache = subprocess.run(["ldconfig", "-p"], capture_output=True, text=True).stdout
        names.update(line.split()[0] for line in cache.splitlines()[1:] if line.strip())
    except OSError:
        pass
    for folder in ("/usr/lib", "/lib", "/usr/lib64", "/lib64", "/usr/lib/x86_64-linux-gnu", "/lib/x86_64-linux-gnu"):
        if os.path.isdir(folder):
            names.update(os.listdir(folder))
    return names


def apply(dist):
    found = list(absolute_runpaths(dist))
    system = system_libs()
    problems = []
    for path, _ in found:
        folder = os.path.dirname(path)
        missing = [lib for lib in needed_libs(path)
                   if lib not in system and not os.path.exists(os.path.join(folder, lib))]
        if missing:
            problems.append(f"{os.path.relpath(path, dist)} needs {', '.join(missing)}, which is not next to it")
    if problems:
        print("refusing to relocate; nothing changed:", *problems, sep="\n  ", file=sys.stderr)
        return 2
    for path, runpath in found:
        if not os.path.exists(path + BACKUP):
            shutil.copy2(path, path + BACKUP)
        shutil.copy2(path, path + TEMP)
        subprocess.run([PATCHELF, "--set-rpath", "$ORIGIN", path + TEMP], check=True)
        os.replace(path + TEMP, path)
        print(f"{os.path.relpath(path, dist)}: RUNPATH {runpath} -> $ORIGIN")
    if not found:
        print("nothing to relocate")
    return 0


def revert(dist):
    restored = 0
    for root, dirs, files in os.walk(dist):
        for name in sorted(files):
            backup = os.path.join(root, name)
            if name.endswith(BACKUP) and is_elf(backup):
                os.replace(backup, backup[: -len(BACKUP)])
                print(f"restored {os.path.relpath(backup[: -len(BACKUP)], dist)}")
                restored += 1
    if not restored:
        print("nothing to revert")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", metavar="DIST")
    mode.add_argument("--apply", metavar="DIST")
    mode.add_argument("--revert", metavar="DIST")
    args = ap.parse_args(argv)
    if not (os.path.isfile(PATCHELF) and os.access(PATCHELF, os.X_OK)):
        print(f"patchelf not found at {PATCHELF} (install patchelf)", file=sys.stderr)
        return 3
    if args.apply:
        return apply(args.apply)
    if args.revert:
        return revert(args.revert)
    found = list(absolute_runpaths(args.check))
    for path, runpath in found:
        print(f"{os.path.relpath(path, args.check)}: RUNPATH {runpath}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
