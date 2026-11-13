#!/usr/bin/env python3
"""End-to-end test for scripts/package.sh on a fake Vortex build.

The fake build has the pieces packaging touches: the `vortex` binary, the
bundled 7-Zip, and a FOMOD module whose RUNPATH points into a build tree.
"""
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PACKAGE = os.path.join(ROOT, "scripts", "package.sh")
PATCHELF = shutil.which("patchelf") or os.path.expanduser("~/.local/bin/patchelf")
TOOLS = shutil.which("gcc") and os.path.exists(PATCHELF) and shutil.which("objdump") and shutil.which("xz")
TRUE = shutil.which("true") or "/usr/bin/true"


def fake_vortex(src):
    """A Vortex checkout after the build: SRC/dist/linux-unpacked plus the files packaging copies."""
    dist = os.path.join(src, "dist", "linux-unpacked")
    unpacked = os.path.join(dist, "resources", "app.asar.unpacked", "node_modules")
    sevenz = os.path.join(unpacked, "7z-bin", "linux")
    fomod = os.path.join(unpacked, "@nexusmods", "fomod-installer-native", "build", "Release")
    build = os.path.join(src, "src", "main", "dist", "fomod")
    for d in (sevenz, fomod, build, os.path.join(src, "assets", "images")):
        os.makedirs(d)
    shutil.copy2(TRUE, os.path.join(dist, "vortex"))
    shutil.copy2(TRUE, os.path.join(sevenz, "7zzs"))
    dep_c, main_c = os.path.join(build, "dep.c"), os.path.join(build, "main.c")
    with open(dep_c, "w") as f:
        f.write("int dep(void) { return 42; }\n")
    with open(main_c, "w") as f:
        f.write("int dep(void);\nint answer(void) { return dep(); }\n")
    gcc = ["gcc", "-shared", "-fPIC", "-Wl,--enable-new-dtags"]
    subprocess.run(gcc + ["-o", os.path.join(build, "ModInstaller.Native.so"), dep_c], check=True)
    subprocess.run(["ln", "-s", "ModInstaller.Native.so", os.path.join(build, "libModInstaller.Native.so")], check=True)
    subprocess.run(gcc + ["-o", os.path.join(build, "modinstaller.node"), main_c, "-L" + build,
                          "-l:ModInstaller.Native.so", "-Wl,-rpath," + build], check=True)
    for name in ("ModInstaller.Native.so", "modinstaller.node"):
        shutil.copy2(os.path.join(build, name), fomod)
    with open(os.path.join(src, "assets", "images", "vortex.png"), "wb") as f:
        f.write(b"\x89PNG fake")
    with open(os.path.join(src, "LICENSE.md"), "w") as f:
        f.write("GNU GENERAL PUBLIC LICENSE (fake)\n")
    return fomod


@unittest.skipUnless(TOOLS and TRUE, "needs gcc, patchelf, objdump and xz")
class PackageTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="package-")
        self.addCleanup(tmp.cleanup)
        self.src = os.path.join(tmp.name, "vortex")
        self.out = os.path.join(tmp.name, "out")
        self.fomod = fake_vortex(self.src)

    def package(self, tag="v9.9.9", src=None):
        return subprocess.run(["bash", PACKAGE, src or self.src, tag, self.out], capture_output=True, text=True)

    def test_writes_the_archive_and_its_checksum(self):
        r = self.package()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        archive = os.path.join(self.out, "vortex-9.9.9-linux-x64.tar.xz")
        self.assertTrue(os.path.isfile(archive))
        check = subprocess.run(["sha256sum", "-c", "vortex-9.9.9-linux-x64.tar.xz.sha256"],
                               cwd=self.out, capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_archive_layout_and_ownership(self):
        self.assertEqual(self.package().returncode, 0)
        with tarfile.open(os.path.join(self.out, "vortex-9.9.9-linux-x64.tar.xz")) as t:
            members = t.getmembers()
        names = {m.name for m in members}
        top = "vortex-9.9.9-linux-x64"
        for f in ("vortex", "vortex.sh", "install-desktop.sh", "vortex.png", "LICENSE-Vortex.md", "BUILD-INFO.txt"):
            self.assertIn(f"{top}/{f}", names)
        self.assertTrue(all(n == top or n.startswith(top + "/") for n in names))
        self.assertFalse([n for n in names if n.endswith(".relocate-orig")])
        sevenz = f"{top}/resources/app.asar.unpacked/node_modules/7z-bin/linux/7zzs"
        self.assertIn(sevenz + ".real", names)
        self.assertEqual({(m.uid, m.gid, m.uname, m.gname) for m in members}, {(0, 0, "", "")})
        launcher = next(m for m in members if m.name == f"{top}/vortex.sh")
        self.assertTrue(launcher.mode & 0o111)

    def test_fixes_are_applied_in_the_staged_copy_only(self):
        self.assertEqual(self.package().returncode, 0)
        staged = os.path.join(self.out, "vortex-9.9.9-linux-x64", "resources", "app.asar.unpacked", "node_modules",
                              "@nexusmods", "fomod-installer-native", "build", "Release", "modinstaller.node")
        rp = subprocess.run([PATCHELF, "--print-rpath", staged], capture_output=True, text=True).stdout.strip()
        self.assertEqual(rp, "$ORIGIN")
        original = os.path.join(self.fomod, "modinstaller.node")
        rp = subprocess.run([PATCHELF, "--print-rpath", original], capture_output=True, text=True).stdout.strip()
        self.assertTrue(rp.startswith("/"), rp)   # the build itself is left alone

    def test_build_info_names_the_version_and_the_glibc_floor(self):
        self.assertEqual(self.package().returncode, 0)
        with open(os.path.join(self.out, "vortex-9.9.9-linux-x64", "BUILD-INFO.txt")) as f:
            info = f.read()
        self.assertIn("v9.9.9", info)
        self.assertRegex(info, r"minimum glibc: 2\.\d+")

    def test_refuses_to_overwrite_and_needs_a_build(self):
        self.assertEqual(self.package().returncode, 0)
        self.assertEqual(self.package().returncode, 2)
        shutil.rmtree(self.out)
        self.assertEqual(self.package(src=os.path.join(self.src, "nope")).returncode, 2)
        self.assertEqual(self.package(tag="2.10.1").returncode, 2)


if __name__ == "__main__":
    unittest.main()
