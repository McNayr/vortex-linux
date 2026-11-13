#!/usr/bin/env python3
"""Report the oldest system an unpacked Linux app can run on.

  elf-report.py DIR          one line: the minimum glibc and libstdc++ versions
  elf-report.py --json DIR   details as JSON, including the file that sets each minimum

Reads the version references ("required from libc.so.6: GLIBC_2.34") of every
x86-64 ELF file under DIR with objdump from binutils. ELF files for other
architectures (some npm packages ship prebuilt arm or Android modules) are
skipped.
"""
import argparse
import json
import os
import re
import struct
import subprocess
import sys

X86_64 = 62
VERSION = re.compile(r"\b(GLIBC|GLIBCXX|CXXABI)_(\d+(?:\.\d+)*)\b")


def elf_machine(path):
    """e_machine of an ELF file, or None for anything else."""
    try:
        with open(path, "rb") as f:
            head = f.read(20)
    except OSError:
        return None
    if len(head) < 20 or head[:4] != b"\x7fELF":
        return None
    order = "<" if head[5] == 1 else ">"
    return struct.unpack(order + "H", head[18:20])[0]


def requirements(path):
    """[(family, version tuple)] from the file's "Version References" section."""
    out = subprocess.run(["objdump", "-p", path], capture_output=True, text=True, errors="replace").stdout
    found, inside = [], False
    for line in out.splitlines():
        if line.startswith("Version References:"):
            inside = True
            continue
        if inside:
            if line and not line[0].isspace():
                break
            for family, version in VERSION.findall(line):
                found.append((family, tuple(int(x) for x in version.split("."))))
    return found


def scan(root):
    best, scanned, other = {}, 0, 0
    for dirpath, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(dirpath, name)
            if os.path.islink(path):
                continue
            machine = elf_machine(path)
            if machine is None:
                continue
            if machine != X86_64:
                other += 1
                continue
            scanned += 1
            for family, version in requirements(path):
                if family not in best or version > best[family][0]:
                    best[family] = (version, os.path.relpath(path, root))
    return best, scanned, other


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("dir")
    args = ap.parse_args(argv)
    best, scanned, other = scan(args.dir)

    def version(family):
        return ".".join(map(str, best[family][0])) if family in best else None

    def source(family):
        return best[family][1] if family in best else None

    report = {
        "glibc": version("GLIBC"), "glibc_from": source("GLIBC"),
        "glibcxx": version("GLIBCXX"), "glibcxx_from": source("GLIBCXX"),
        "cxxabi": version("CXXABI"),
        "scanned": scanned, "skipped_other_arch": other,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        line = f"minimum glibc: {report['glibc'] or 'none'}"
        if report["glibcxx"]:
            line += f" (libstdc++: GLIBCXX_{report['glibcxx']})"
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
