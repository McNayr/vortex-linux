#!/usr/bin/env python3
"""Tests for scripts/7zzs-wrapper.py and scripts/install-7z-wrapper.sh, run against a real 7-Zip.

7-Zip comes from VORTEX_7Z_REAL (for example the 7zzs.real inside a packaged
build) or from 7zz on PATH; without one, the tests are skipped.
The archives are built with zipfile, which (on Linux) stores backslashes in
entry names as given, like the Windows-made mod archives that fail to unpack.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WRAPPER = os.path.join(ROOT, "scripts", "7zzs-wrapper.py")
INSTALLER = os.path.join(ROOT, "scripts", "install-7z-wrapper.sh")
# Optional: a writable folder on an NTFS drive mounted with ntfs3 and windows_names.
NTFS_DIR = os.environ.get("VORTEX_TEST_NTFS_DIR", "")


def is_elf(path):
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except OSError:
        return False


def real_7z() -> str:
    for p in (os.environ.get("VORTEX_7Z_REAL"), shutil.which("7zz")):
        if p and os.access(p, os.X_OK):
            return p
    return ""


REAL = real_7z()
WINDOWS_STYLE = {
    "archive\\pc\\mod\\example.archive.xl": b"xl",
    "archive\\pc\\mod\\example_face.archive": b"face",
    "r6/scripts/Example/ok.reds": b"ok",
    "readme.txt": b"readme",
}


def make_zip(path, entries, dirs=()):
    with zipfile.ZipFile(path, "w") as z:
        for d in dirs:
            info = zipfile.ZipInfo(d)
            info.create_system = 0          # MS-DOS host, like Windows tools
            info.external_attr = 0x10       # MS-DOS directory attribute
            z.writestr(info, b"")
        for name, data in entries.items():
            z.writestr(zipfile.ZipInfo(name), data)


def tree(root):
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            p = os.path.join(dirpath, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root)] = fh.read()
    return out


@unittest.skipUnless(REAL, "no 7-Zip found (set VORTEX_7Z_REAL or install 7zz)")
class WrapperTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.env = dict(os.environ, VORTEX_7Z_REAL=REAL)

    def wrap(self, *args):
        return subprocess.run(["python3", WRAPPER, *args], env=self.env, capture_output=True)

    def test_windows_style_names_unpack_into_folders(self):
        z = os.path.join(self.tmp, "windows-style.zip")
        make_zip(z, WINDOWS_STYLE, dirs=["archive\\pc\\"])
        out = os.path.join(self.tmp, "out")
        r = self.wrap("x", z, "-o" + out, "-y", "-bsp1", "-ssc-")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(tree(out), {
            "archive/pc/mod/example.archive.xl": b"xl",
            "archive/pc/mod/example_face.archive": b"face",
            "r6/scripts/Example/ok.reds": b"ok",
            "readme.txt": b"readme",
        })
        names = [n for _d, ds, fs in os.walk(out) for n in ds + fs]
        self.assertFalse([n for n in names if "\\" in n], names)

    def test_plain_7zip_gets_it_wrong_without_the_wrapper(self):
        z = os.path.join(self.tmp, "windows-style.zip")
        make_zip(z, WINDOWS_STYLE)
        out = os.path.join(self.tmp, "out")
        subprocess.run([REAL, "x", z, "-o" + out, "-y"], capture_output=True, check=True)
        self.assertIn("archive\\pc\\mod\\example.archive.xl", tree(out))   # one file name with backslashes

    def test_normal_archive_matches_plain_7zip(self):
        z = os.path.join(self.tmp, "normal.zip")
        make_zip(z, {"bin/x64/plugins/example.asi": b"asi", "red4ext/example.dll": b"dll"})
        a, b = os.path.join(self.tmp, "a"), os.path.join(self.tmp, "b")
        self.assertEqual(self.wrap("x", z, "-o" + a, "-y").returncode, 0)
        subprocess.run([REAL, "x", z, "-o" + b, "-y"], capture_output=True, check=True)
        self.assertEqual(tree(a), tree(b))

    def test_other_commands_pass_straight_through(self):
        z = os.path.join(self.tmp, "windows-style.zip")
        make_zip(z, WINDOWS_STYLE)
        mine = self.wrap("l", "-ba", "-slt", z)
        theirs = subprocess.run([REAL, "l", "-ba", "-slt", z], capture_output=True)
        self.assertEqual((mine.returncode, mine.stdout), (theirs.returncode, theirs.stdout))

    def test_unsafe_names_are_refused(self):
        z = os.path.join(self.tmp, "evil.zip")
        make_zip(z, {"..\\..\\evil.txt": b"evil", "fine.txt": b"fine"})
        out = os.path.join(self.tmp, "deep", "out")
        r = self.wrap("x", z, "-o" + out, "-y")
        self.assertEqual(r.returncode, 2)
        self.assertIn(b"unsafe path", r.stderr)
        self.assertEqual(tree(os.path.join(self.tmp, "deep")), {"out/fine.txt": b"fine"})

    @unittest.skipUnless(NTFS_DIR and os.access(NTFS_DIR, os.W_OK), "set VORTEX_TEST_NTFS_DIR to an ntfs3 folder")
    def test_unpacks_on_an_ntfs_drive_with_windows_names(self):
        z = os.path.join(self.tmp, "windows-style.zip")
        make_zip(z, WINDOWS_STYLE)
        with tempfile.TemporaryDirectory(dir=NTFS_DIR, prefix=".7z-wrapper-test-") as d:
            plain = subprocess.run([REAL, "x", z, "-o" + os.path.join(d, "plain"), "-y"], capture_output=True)
            self.assertNotEqual(plain.returncode, 0)                       # the original failure
            self.assertIn(b"Invalid argument", plain.stdout + plain.stderr)
            r = self.wrap("x", z, "-o" + os.path.join(d, "fixed"), "-y")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(tree(os.path.join(d, "fixed"))["archive/pc/mod/example.archive.xl"], b"xl")


@unittest.skipUnless(REAL and is_elf(REAL), "needs a 7-Zip ELF binary (set VORTEX_7Z_REAL or install 7zz)")
class InstallerTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.bin = os.path.join(tmp.name, "7zzs")
        shutil.copy2(REAL, self.bin)
        self.env = dict(os.environ, SEVENZ_BIN=self.bin)
        self.env.pop("VORTEX_7Z_REAL", None)

    def run_installer(self, mode):
        return subprocess.run(["bash", INSTALLER, mode], env=self.env, capture_output=True, text=True)

    def test_apply_check_rerun_revert(self):
        self.assertEqual(self.run_installer("--check").returncode, 1)
        r = self.run_installer("--apply")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(is_elf(self.bin + ".real"))
        self.assertFalse(is_elf(self.bin))
        self.assertEqual(self.run_installer("--check").returncode, 0)
        self.assertEqual(self.run_installer("--apply").returncode, 0)          # rerun keeps the real binary
        self.assertTrue(is_elf(self.bin + ".real"))
        z = os.path.join(os.path.dirname(self.bin), "c.zip")
        make_zip(z, WINDOWS_STYLE)
        out = os.path.join(os.path.dirname(self.bin), "out")
        r = subprocess.run([self.bin, "x", z, "-o" + out, "-y"], env=self.env, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)                           # the installed wrapper finds 7zzs.real itself
        self.assertIn("archive/pc/mod/example.archive.xl", tree(out))
        self.assertEqual(self.run_installer("--revert").returncode, 0)
        self.assertTrue(is_elf(self.bin))
        self.assertFalse(os.path.exists(self.bin + ".real"))

    def test_app_folder_argument_finds_the_bundled_7zip(self):
        app = os.path.join(os.path.dirname(self.bin), "app")
        target = os.path.join(app, "resources", "app.asar.unpacked", "node_modules", "7z-bin", "linux")
        os.makedirs(target)
        shutil.copy2(REAL, os.path.join(target, "7zzs"))
        env = dict(self.env)
        env.pop("SEVENZ_BIN")
        r = subprocess.run(["bash", INSTALLER, "--apply", app], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(is_elf(os.path.join(target, "7zzs.real")))

    def test_missing_app_folder_prints_usage(self):
        env = dict(self.env)
        env.pop("SEVENZ_BIN")
        r = subprocess.run(["bash", INSTALLER, "--apply"], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("APP", r.stderr)


if __name__ == "__main__":
    unittest.main()
