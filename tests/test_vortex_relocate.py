#!/usr/bin/env python3
"""Tests for scripts/vortex-relocate.py on small real ELF libraries built with gcc.

The fixture mirrors Vortex's FOMOD module: libmain.so needs libdep.so and finds it
through an absolute RUNPATH into a build tree; the packaged copy holds both files
side by side, like app.asar.unpacked/.../build/Release/ holds modinstaller.node
and ModInstaller.Native.so.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "vortex-relocate.py")
PATCHELF = shutil.which("patchelf") or os.path.expanduser("~/.local/bin/patchelf")
TOOLS = shutil.which("gcc") and os.path.exists(PATCHELF)


def run(*args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)


def build_fixture(root):
    """Return (build dir, dist dir, package dir) under root."""
    build = os.path.join(root, "build")
    os.makedirs(build)
    dep_c = os.path.join(build, "dep.c")
    main_c = os.path.join(build, "main.c")
    with open(dep_c, "w") as f:
        f.write("int dep(void) { return 42; }\n")
    with open(main_c, "w") as f:
        f.write("int dep(void);\nint answer(void) { return dep(); }\n")
    gcc = ["gcc", "-shared", "-fPIC", "-Wl,--enable-new-dtags"]
    subprocess.run(gcc + ["-o", os.path.join(build, "libdep.so"), dep_c], check=True)
    subprocess.run(gcc + ["-o", os.path.join(build, "libmain.so"), main_c,
                          "-L" + build, "-ldep", "-Wl,-rpath," + build], check=True)
    dist = os.path.join(root, "dist")
    pkg = os.path.join(dist, "resources", "pkg", "build", "Release")
    os.makedirs(pkg)
    for name in ("libdep.so", "libmain.so"):
        shutil.copy2(os.path.join(build, name), pkg)
    # Left alone: an ELF that already uses $ORIGIN, and a file that is not an ELF.
    subprocess.run(gcc + ["-o", os.path.join(pkg, "liborigin.so"), dep_c, "-Wl,-rpath,$ORIGIN"], check=True)
    with open(os.path.join(dist, "notes.txt"), "w") as f:
        f.write("not an ELF\n")
    return build, dist, pkg


def runpath(path):
    return subprocess.run([PATCHELF, "--print-rpath", path], capture_output=True, text=True).stdout.strip()


def load_answer(lib):
    """Load lib in a fresh Python and call answer(); return its output, or the loader error."""
    r = subprocess.run([sys.executable, "-c", "import ctypes, sys; print(ctypes.CDLL(sys.argv[1]).answer())", lib],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else r.stderr


def move_away(root, dist, build):
    """Move the package somewhere else and delete the build tree, like copying it to another machine."""
    moved = os.path.join(root, "elsewhere")
    shutil.move(dist, moved)
    shutil.rmtree(build)
    return os.path.join(moved, "resources", "pkg", "build", "Release", "libmain.so")


def read(path):
    with open(path, "rb") as f:
        return f.read()


@unittest.skipUnless(TOOLS, "needs gcc and patchelf")
class CheckTest(unittest.TestCase):
    def test_check_lists_a_library_with_an_absolute_runpath(self):
        with tempfile.TemporaryDirectory(prefix="relocate-") as root:
            build, dist, _ = build_fixture(root)
            r = run("--check", dist)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("resources/pkg/build/Release/libmain.so", r.stdout)
            self.assertIn(build, r.stdout)
            self.assertNotIn("liborigin.so", r.stdout)
            self.assertNotIn("notes.txt", r.stdout)


@unittest.skipUnless(TOOLS, "needs gcc and patchelf")
class ApplyTest(unittest.TestCase):
    def test_apply_points_the_module_at_its_own_folder(self):
        with tempfile.TemporaryDirectory(prefix="relocate-") as root:
            _, dist, pkg = build_fixture(root)
            r = run("--apply", dist)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(runpath(os.path.join(pkg, "libmain.so")), "$ORIGIN")
            self.assertEqual(run("--check", dist).returncode, 0)

    def test_moved_package_fails_to_load_without_apply(self):
        """Fixture check: the moved package reproduces the bug."""
        with tempfile.TemporaryDirectory(prefix="relocate-") as root:
            build, dist, _ = build_fixture(root)
            self.assertIn("libdep.so", load_answer(move_away(root, dist, build)))

    def test_moved_package_loads_once_applied(self):
        with tempfile.TemporaryDirectory(prefix="relocate-") as root:
            build, dist, _ = build_fixture(root)
            run("--apply", dist)
            self.assertEqual(load_answer(move_away(root, dist, build)), "42")

    def test_apply_keeps_the_original_next_to_it(self):
        with tempfile.TemporaryDirectory(prefix="relocate-") as root:
            _, dist, pkg = build_fixture(root)
            lib = os.path.join(pkg, "libmain.so")
            original = read(lib)
            run("--apply", dist)
            self.assertEqual(read(lib + ".relocate-orig"), original)

    def test_apply_swaps_in_a_new_file(self):
        """A running Vortex keeps the module it already loaded: the old inode is never rewritten."""
        with tempfile.TemporaryDirectory(prefix="relocate-") as root:
            _, dist, pkg = build_fixture(root)
            lib = os.path.join(pkg, "libmain.so")
            before = os.stat(lib).st_ino
            run("--apply", dist)
            self.assertNotEqual(os.stat(lib).st_ino, before)


@unittest.skipUnless(TOOLS, "needs gcc and patchelf")
class SafetyTest(unittest.TestCase):
    def test_apply_refuses_when_a_needed_library_is_not_next_to_the_module(self):
        with tempfile.TemporaryDirectory(prefix="relocate-") as root:
            _, dist, pkg = build_fixture(root)
            os.remove(os.path.join(pkg, "libdep.so"))
            lib = os.path.join(pkg, "libmain.so")
            original = read(lib)
            r = run("--apply", dist)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("libdep.so", r.stderr)
            self.assertEqual(read(lib), original)
            self.assertFalse(os.path.exists(lib + ".relocate-orig"))

    def test_revert_restores_the_original(self):
        with tempfile.TemporaryDirectory(prefix="relocate-") as root:
            _, dist, pkg = build_fixture(root)
            lib = os.path.join(pkg, "libmain.so")
            original = read(lib)
            run("--apply", dist)
            r = run("--revert", dist)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(read(lib), original)
            self.assertFalse(os.path.exists(lib + ".relocate-orig"))

    def test_revert_leaves_other_tools_backups_alone(self):
        """Only ELF backups are this tool's; another tool's .relocate-orig file stays put."""
        with tempfile.TemporaryDirectory(prefix="relocate-") as root:
            _, dist, _ = build_fixture(root)
            other = os.path.join(dist, "notes.txt.relocate-orig")
            with open(other, "w") as f:
                f.write("another tool's backup\n")
            run("--revert", dist)
            self.assertTrue(os.path.exists(other))


class ToolTest(unittest.TestCase):
    def test_missing_patchelf_is_reported(self):
        with tempfile.TemporaryDirectory(prefix="relocate-") as root:
            dist = os.path.join(root, "dist")
            os.makedirs(dist)
            env = dict(os.environ, PATCHELF=os.path.join(root, "no-patchelf"))
            r = subprocess.run([sys.executable, SCRIPT, "--check", dist], capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
            self.assertIn("patchelf", r.stderr)


if __name__ == "__main__":
    unittest.main()
