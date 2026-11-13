# Vortex for Linux (unofficial builds)

Prebuilt native Linux packages of [Vortex](https://github.com/Nexus-Mods/Vortex), the mod manager from Nexus Mods. GitHub Actions builds each release from an official Vortex release tag and adds two Linux fixes. Vortex itself runs natively, without Wine; your games keep running through Proton as usual.

> **Unofficial.** Not made, endorsed or supported by Nexus Mods or Black Tree Gaming. Report problems with these builds here, not to Nexus Mods.

## Quick start

1. Install the .NET 9 runtime; Vortex quits at startup without it. This way needs no root and works on every distro:

   ```bash
   curl -sSL https://dot.net/v1/dotnet-install.sh -o dotnet-install.sh
   bash dotnet-install.sh --channel 9.0 --runtime dotnet --install-dir ~/.dotnet
   ```

2. Download `vortex-<version>-linux-x64.tar.xz` and its `.sha256` from [Releases](../../releases), then:

   ```bash
   sha256sum -c vortex-*-linux-x64.tar.xz.sha256
   mkdir -p ~/Applications
   tar -xf vortex-*-linux-x64.tar.xz -C ~/Applications
   ~/Applications/vortex-*-linux-x64/install-desktop.sh
   ```

3. Start **Vortex** from your app menu (or run `vortex.sh` in that folder), log in to Nexus Mods, and manage your game.

The [setup guide](docs/SETUP.md) covers each step in detail, plus Steam games under Proton, NTFS game drives, and fixes for common problems. If you'd rather have an AI coding agent walk you through it, give it [this prompt](docs/AGENT_PROMPT.md).

## What these builds add

- **FOMOD installers work from any folder.** Upstream packs the native FOMOD module with an absolute path into its build folder ([Nexus-Mods/Vortex#23565](https://github.com/Nexus-Mods/Vortex/issues/23565)). In a copied build, the module fails to load and FOMOD mods get installed unprocessed. In these builds, the module loads its library from its own folder.
- **Mods with Windows-style folder names unpack correctly.** Some archives store paths like `archive\pc\mod\file` with backslashes. The bundled 7-Zip is wrapped so those become real folders. Without the wrapper they fail on NTFS drives with "Invalid argument", and on Linux filesystems they unpack into files with backslashes in their names.
- **One archive for most distros.** The packages are built on Ubuntu 22.04, which keeps the glibc requirement low. Each release states its floor, and so does `BUILD-INFO.txt` in the archive.
- **Desktop integration.** `vortex.sh` hands `nxm://` links to Vortex and finds a .NET runtime in `~/.dotnet`. `install-desktop.sh` adds the app-menu entry and makes the "Mod Manager Download" buttons on nexusmods.com open Vortex.

## Compatibility

| Distro | Status |
| --- | --- |
| Omarchy (Arch Linux) | Tested by the maintainer |
| SteamOS 3 (Steam Deck, desktop mode) | An earlier build of the same Vortex version ran on a Steam Deck, with .NET in `~/.dotnet`; this package is not tested there yet |
| Ubuntu, Debian, Fedora, openSUSE, Bazzite, others | Built to work, not yet tested. Please [tell us how it goes](../../issues/new/choose) |

Reports from other distros are what moves a row to "tested". Use the **Distro report** issue form.

## Requirements

- x86-64 Linux with glibc at or above the release's floor (check with `ldd --version`)
- the .NET 9 runtime
- python3 (for the 7-Zip wrapper)
- a desktop session (Wayland or X11) with the usual Electron libraries (GTK 3, NSS, ALSA, libgbm); any desktop install has them

## Build it yourself

```bash
scripts/build-vortex.sh v2.10.1 ./vortex-src
scripts/package.sh ./vortex-src v2.10.1 ./out
```

[CONTRIBUTING.md](CONTRIBUTING.md) lists the toolchain and the tests. The CI recipe is [.github/workflows/build.yml](.github/workflows/build.yml). A local build records its build folder in Vortex's metadata, so share only CI builds.

## License

Vortex is GPL-3.0, and so are these scripts ([LICENSE](LICENSE)). Each release names the exact upstream tag and the commit of these scripts it was built from.
