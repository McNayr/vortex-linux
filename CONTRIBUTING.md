# Contributing

Distro reports, bug reports and fixes are welcome. Please use the [issue forms](https://github.com/McNayr/vortex-linux/issues/new/choose). Problems that also happen in the official Windows Vortex belong upstream at [Nexus-Mods/Vortex](https://github.com/Nexus-Mods/Vortex/issues).

## How a release is made

1. The `build` workflow runs by hand (**Actions → build → Run workflow**). It takes an upstream release tag (for example `v2.10.1`) and a build number (`1` for the first build of that version, then `2` and so on for rebuilds with fixed scripts).
2. On Ubuntu 22.04 it clones that tag of [Nexus-Mods/Vortex](https://github.com/Nexus-Mods/Vortex) and builds it (`scripts/build-vortex.sh`).
3. `scripts/package.sh` applies the Linux fixes and checks them, then writes the archive and its checksum.
4. The workflow tests the packaged 7-Zip wrapper, then creates a **draft** release named `<tag>-linux.<build>`.
5. A maintainer downloads the draft on a real system and checks it: Vortex starts, the FOMOD module loads, a mod installs and deploys. Then the release is published.

## Build locally

You need:

- git, python3 (plus setuptools on Python 3.12 and newer), and a C/C++ toolchain
- the fontconfig development headers (`libfontconfig1-dev` on Debian and Ubuntu, `fontconfig-devel` on Fedora, `fontconfig` on Arch)
- the Node.js version in the tag's `package.json` (`engines.node`), and the pnpm version in its `packageManager` field
- the .NET 9 SDK
- patchelf, xz, binutils (`objdump`)

```bash
scripts/build-vortex.sh v2.10.1 ./vortex-src     # clone the tag and build it (takes a while)
scripts/package.sh ./vortex-src v2.10.1 ./out     # out/vortex-2.10.1-linux-x64.tar.xz
```

A local build records your build folder (and with it your user name) in Vortex's metadata, and `package.sh` warns about it. Use local builds yourself, and publish only CI builds.

## Tests

```bash
bash tests/run.sh
```

The tests use gcc, g++, patchelf and objdump, plus a real 7-Zip for the wrapper tests: `7zz` on PATH, or `VORTEX_7Z_REAL=/path/to/7zz`. Tests whose tools are missing are skipped. One wrapper test needs a writable folder on an NTFS drive mounted with `ntfs3` and `windows_names`, set as `VORTEX_TEST_NTFS_DIR`.

What each part covers:

| File | What it does | Tests |
| --- | --- | --- |
| `scripts/vortex-relocate.py` | Points native modules with an absolute RUNPATH at `$ORIGIN`; refuses if a needed library is not next to them | `test_vortex_relocate.py` |
| `scripts/7zzs-wrapper.py`, `scripts/install-7z-wrapper.sh` | 7-Zip wrapper that unpacks Windows-style folder names into folders | `test_7z_wrapper.py` |
| `scripts/elf-report.py` | Reports the package's minimum glibc and libstdc++ | `test_elf_report.py` |
| `scripts/package.sh` | Stages, fixes, checks and archives a build | `test_package.py` |
| `package/vortex.sh` | Launcher: `nxm://` links, `~/.dotnet`, optional `--no-sandbox` | `test_launcher.sh` |
| `package/install-desktop.sh` | App-menu entry and `nxm://` handler | `test_install_desktop.sh` |

Please add or update a test with each change.

## Pull requests

- Keep them small, one topic each.
- Run `bash tests/run.sh` before you push; CI runs the same tests.
- Don't commit logs, build output, or anything with your user name, home folder path or machine details in it.
- Contributions are licensed GPL-3.0, like the rest of the repository.
