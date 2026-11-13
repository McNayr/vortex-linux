#!/usr/bin/env python3
"""vortex-linux-7z-backslash-wrapper v1: Vortex's 7-Zip, taught to unpack Windows-style folder names.

Installed by scripts/install-7z-wrapper.sh in place of the 7-Zip binary
bundled with native Vortex (resources/app.asar.unpacked/node_modules/7z-bin/linux/7zzs);
the real binary is kept beside it as 7zzs.real.

Some mod archives store their folders Windows-style, with backslashes inside
the entry names ("archive\\pc\\mod\\example.archive"). Windows unpacks those
into folders. 7-Zip on Linux keeps each such name as one file name with
backslashes in it, which is wrong anywhere and is refused outright by NTFS
drives mounted with ntfs3's windows_names option: "Cannot open output file :
errno=22 : Invalid argument".

For a full extraction (7zzs x ARCHIVE -oDIR ...) of an archive that has such
entries, this runs the real 7-Zip on everything else, then writes each
backslash entry to its proper folder. Every other call goes straight to the
real 7-Zip, unchanged.
"""
import os
import subprocess
import sys
import tempfile
from typing import NoReturn

REAL = os.environ.get("VORTEX_7Z_REAL") or os.path.realpath(__file__) + ".real"


def passthrough(args) -> NoReturn:
    os.execv(REAL, [REAL] + args)


def parse(args):
    """(archive, outdir, file filters, password switches) for an 'x' command, else None."""
    if not args or args[0].lower() != "x":
        return None
    archive, outdir, files, pw = None, ".", [], []
    for a in args[1:]:
        if len(a) > 1 and a.startswith("-"):
            if a.startswith("-o"):
                outdir = a[2:]
            elif a.startswith("-p"):
                pw.append(a)
        elif archive is None:
            archive = a
        else:
            files.append(a)
    return None if archive is None else (archive, outdir, files, pw)


def list_entries(archive, pw):
    out = subprocess.run([REAL, "l", "-slt", "-ba", "-sccUTF-8", *pw, "--", archive],
                         capture_output=True, stdin=subprocess.DEVNULL)
    if out.returncode != 0:
        return None
    entries, cur = [], None
    for line in out.stdout.decode("utf-8", "surrogateescape").splitlines():
        if line.startswith("Path = "):
            cur = {"path": line[7:], "dir": False}
            entries.append(cur)
        elif cur is not None and (line == "Folder = +" or (line.startswith("Attributes = ") and line[13:14] == "D")):
            cur["dir"] = True
    return entries


def main():
    args = sys.argv[1:]
    parsed = parse(args)
    if parsed is None or parsed[2]:  # not a full extraction: leave it alone
        passthrough(args)
    archive, outdir, _files, pw = parsed
    entries = list_entries(archive, pw)
    bad = [e for e in entries or [] if "\\" in e["path"]]
    if not bad:
        passthrough(args)

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", errors="surrogateescape",
                                     suffix=".lst", delete=False) as f:
        f.write("".join(e["path"] + "\n" for e in bad))
        exclude = f.name
    try:
        rc = subprocess.call([REAL] + args + ["-scsUTF-8", "-x@" + exclude])
    finally:
        os.unlink(exclude)

    for e in bad:
        name = e["path"]
        parts = [p for p in name.replace("\\", "/").split("/") if p not in ("", ".")]
        if not parts or ".." in parts:
            print(f"ERROR: unsafe path in archive, skipped: {name}", file=sys.stderr)
            rc = max(rc, 2)
            continue
        target = os.path.join(outdir, *parts)
        if e["dir"] or name.endswith(("\\", "/")):
            os.makedirs(target, exist_ok=True)
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as out:
            r = subprocess.call([REAL, "x", "-so", "-spd", "-sccUTF-8", *pw, "--", archive, name],
                                stdout=out, stdin=subprocess.DEVNULL)
        if r != 0:
            print(f"ERROR: could not extract {name}", file=sys.stderr)
            rc = max(rc, r)
    sys.exit(rc)


if __name__ == "__main__":
    main()
