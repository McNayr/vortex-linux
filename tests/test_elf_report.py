#!/usr/bin/env python3
"""Tests for scripts/elf-report.py on small libraries built with gcc and g++."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "elf-report.py")
TOOLS = shutil.which("gcc") and shutil.which("g++") and shutil.which("objdump")


def compile_lib(path, source, cxx=False):
    src = path + (".cpp" if cxx else ".c")
    with open(src, "w") as f:
        f.write(source)
    subprocess.run([("g++" if cxx else "gcc"), "-shared", "-fPIC", "-o", path, src], check=True)
    os.remove(src)


def report(folder):
    r = subprocess.run([sys.executable, SCRIPT, "--json", folder], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@unittest.skipUnless(TOOLS, "needs gcc, g++ and objdump")
class ElfReportTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="elf-report-")
        self.addCleanup(tmp.cleanup)
        self.app = tmp.name
        os.makedirs(os.path.join(self.app, "lib"))
        compile_lib(os.path.join(self.app, "lib", "c.so"),
                    '#include <stdio.h>\nvoid hello(void) { puts("hi"); }\n')
        compile_lib(os.path.join(self.app, "lib", "cxx.so"),
                    '#include <string>\nstd::string hello() { return std::string(40, \'x\'); }\n', cxx=True)

    def test_reports_the_glibc_and_libstdcxx_floors_and_where_they_come_from(self):
        rep = report(self.app)
        self.assertRegex(rep["glibc"], r"^2\.\d+(\.\d+)?$")
        self.assertIn(rep["glibc_from"], ("lib/c.so", "lib/cxx.so"))
        self.assertRegex(rep["glibcxx"], r"^3\.4(\.\d+)?$")
        self.assertEqual(rep["glibcxx_from"], "lib/cxx.so")
        self.assertEqual(rep["scanned"], 2)

    def test_skips_files_for_other_architectures_and_non_elf_files(self):
        arm = os.path.join(self.app, "lib", "arm.so")
        shutil.copy2(os.path.join(self.app, "lib", "c.so"), arm)
        with open(arm, "r+b") as f:          # e_machine = 183 (AArch64)
            f.seek(18)
            f.write((183).to_bytes(2, "little"))
        with open(os.path.join(self.app, "notes.txt"), "w") as f:
            f.write("text\n")
        rep = report(self.app)
        self.assertEqual(rep["scanned"], 2)
        self.assertEqual(rep["skipped_other_arch"], 1)

    def test_plain_output_is_one_line_for_build_info(self):
        r = subprocess.run([sys.executable, SCRIPT, self.app], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1, r.stdout)
        self.assertRegex(lines[0], r"^minimum glibc: 2\.\d+.*libstdc\+\+: GLIBCXX_3\.4")

    def test_empty_folder_reports_nothing_needed(self):
        empty = os.path.join(self.app, "empty")
        os.makedirs(empty)
        rep = report(empty)
        self.assertIsNone(rep["glibc"])
        self.assertEqual(rep["scanned"], 0)


if __name__ == "__main__":
    unittest.main()
