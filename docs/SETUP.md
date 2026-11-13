# Setup guide

This guide takes you from nothing to a modded game: install the runtime Vortex needs, unpack Vortex, connect it to Nexus Mods, and point it at a Steam game that runs through Proton. Every command is meant to be copied as-is. Lines starting with `#` are comments.

Prefer an assistant? [AGENT_PROMPT.md](AGENT_PROMPT.md) is a prompt you can give an AI coding agent (Claude Code, Codex, Gemini CLI, and others). It walks you through this guide on your own machine.

- [1. What you need](#1-what-you-need)
- [2. The .NET 9 runtime](#2-the-net-9-runtime)
- [3. Download and unpack Vortex](#3-download-and-unpack-vortex)
- [4. App menu and nxm:// links](#4-app-menu-and-nxm-links)
- [5. First start](#5-first-start)
- [6. Manage a Steam game](#6-manage-a-steam-game)
- [7. Games on an NTFS (Windows) drive](#7-games-on-an-ntfs-windows-drive)
- [8. Update](#8-update)
- [9. Uninstall](#9-uninstall)
- [10. Troubleshooting](#10-troubleshooting)
- [11. Report a problem](#11-report-a-problem)

## 1. What you need

- **An x86-64 PC running Linux** with a desktop (Wayland or X11). Arm devices are not supported.
- **glibc at or above the release's floor.** Each release says which version it needs, for example "glibc 2.38". Check yours:

  ```bash
  ldd --version | head -n 1
  ```

  The current release needs glibc 2.38. Ubuntu 24.04, Debian 13, Fedora 39 and newer releases have it, and so do current SteamOS and rolling distros (Arch, Omarchy, CachyOS, EndeavourOS, openSUSE Tumbleweed). Ubuntu 22.04 and Debian 12 are too old.
- **python3.** Almost every distro has it; `python3 --version` tells you.
- **About 1 GB of disk** for Vortex, plus room for your mods.
- **A Nexus Mods account.** Free is fine.

## 2. The .NET 9 runtime

Vortex checks for .NET 9 when it starts, because its FOMOD installers need it. Without it, Vortex shows "Check failed: Vortex requires .NET Desktop Runtime 9 to be installed to run FOMOD mod installers", and its only button is **Quit Vortex**.

**Option A: no root, any distro (recommended, and the only option on SteamOS).** This installs .NET into `~/.dotnet`, where `vortex.sh` finds it on its own:

```bash
cd ~/Downloads
curl -sSL https://dot.net/v1/dotnet-install.sh -o dotnet-install.sh
bash dotnet-install.sh --channel 9.0 --runtime dotnet --install-dir ~/.dotnet
ls ~/.dotnet/shared/Microsoft.NETCore.App/   # should list a 9.0.x folder
```

**Option B: your distro's package.** This works when the distro ships .NET 9:

```bash
# Arch, Omarchy, CachyOS, EndeavourOS
sudo pacman -S --needed dotnet-runtime-9.0
# Fedora
sudo dnf install dotnet-runtime-9.0
```

On Ubuntu and Debian, .NET 9 comes from Microsoft's package repository or the Ubuntu .NET backports PPA, depending on the release. Option A is simpler there.

Check what you have with `dotnet --list-runtimes` (Option B) or the `ls` line above (Option A). You need a `Microsoft.NETCore.App 9.x` entry.

## 3. Download and unpack Vortex

From the [latest release](https://github.com/McNayr/vortex-linux/releases/latest), download both files:

- `vortex-<version>-linux-x64.tar.xz`
- `vortex-<version>-linux-x64.tar.xz.sha256`

Check the download, then unpack it:

```bash
cd ~/Downloads
sha256sum -c vortex-*-linux-x64.tar.xz.sha256       # must print ": OK"
mkdir -p ~/Applications
tar -xf vortex-*-linux-x64.tar.xz -C ~/Applications
ls ~/Applications                                     # vortex-<version>-linux-x64
```

Any folder works, including a second drive, and you can move the folder later. Avoid folder names that contain `"`, `` ` ``, `$`, `\` or `%`, because app-menu entries cannot hold them.

`BUILD-INFO.txt` in the folder records exactly what the package was built from.

## 4. App menu and nxm:// links

```bash
~/Applications/vortex-*-linux-x64/install-desktop.sh
```

This adds **Vortex** to your app menu. It also makes Vortex the handler for `nxm://` links, the **Mod Manager Download** buttons on nexusmods.com. It changes files in your home folder only:

- `~/.local/share/applications/com.nexusmods.vortex.desktop`
- the icon
- your default handler for `nxm://` links

Check it at any time with `--check`. If you move the folder, run the script again from its new place.

When you first click **Mod Manager Download**, your browser asks whether to open the link with an external app; allow it. Browsers installed as Flatpak or Snap sometimes cannot open such links at all. In that case, download the file manually ("Manual download") and drag it into Vortex's **Downloads** page.

## 5. First start

Start **Vortex** from the app menu. The first time, it is better to start it from a terminal, where errors are visible:

```bash
~/Applications/vortex-*-linux-x64/vortex.sh
```

Then:

1. Click **Log in** (top right) and finish the login in your browser.
2. Vortex keeps its settings, profiles and logs in `~/.config/Vortex`. The log is `~/.config/Vortex/vortex.log`.

Always start Vortex through `vortex.sh` or the menu entry, not the `vortex` binary itself. The script passes on `nxm://` links and finds .NET in `~/.dotnet`.

## 6. Manage a Steam game

Vortex runs natively; the game still runs through Proton. Vortex installs mods into the game's folder, and Steam starts the game as usual.

**Add the game.** Go to **Games**. Vortex looks for Steam games in Steam's library folders. If your game is not listed as found, search for it, then choose **Manage** → **Manually set location** and pick the game's folder, for example `~/.local/share/Steam/steamapps/common/<Game>` or `<your library>/steamapps/common/<Game>`. Steam installed as a Flatpak keeps its libraries under `~/.var/app/com.valvesoftware.Steam/`.

**Keep mods on the same drive as the game.** Vortex deploys mods by hardlinking them from its staging folder into the game folder, and hardlinks only work within one drive (one filesystem). In **Settings → Mods**:

- set **Mod Staging Folder** to a folder on the game's drive, for example `<your library>/vortex/{game}`
- pick **Hardlink Deployment** as the deployment method

If Vortex says "no deployment method available", the staging folder is on a different drive from the game. Downloads (**Settings → Downloads**) can live anywhere, but the game's drive is a good place for them too.

**Mod loaders through Proton.** Script extenders and loaders that ship a DLL (ASI loaders, Cyber Engine Tweaks, RED4ext and similar) need Wine to load their DLL instead of its own. Set this in the game's Steam **Properties → Launch Options**, naming the DLLs your loaders use:

```text
WINEDLLOVERRIDES="winmm,version=n,b" %command%
```

That example covers Cyberpunk 2077: RED4ext uses `winmm.dll` and Cyber Engine Tweaks uses `version.dll`. Many ASI loaders use `dinput8` instead. The mod's own page usually names the DLL.

**Start the game from Steam**, not from Vortex: Steam sets up Proton.

**Tested so far:** Cyberpunk 2077 with Cyber Engine Tweaks, RED4ext, redscript, ArchiveXL, TweakXL, Codeware and a large mod collection.

Some Vortex game extensions were written for Windows and assume Windows paths. For example, games whose load order lives in the Windows user folders may need extra steps. If a game misbehaves, please report it ([section 11](#11-report-a-problem)), naming the game and its Vortex extension.

## 7. Games on an NTFS (Windows) drive

Dual-booting with a Steam library on an NTFS drive works with these precautions.

- **Mount it with the kernel's `ntfs3` driver**, at a fixed path, from `/etc/fstab`. For example (replace the UUID with yours from `lsblk -f`):

  ```text
  UUID=XXXXXXXXXXXXXXXX  /mnt/games  ntfs3  uid=1000,gid=1000,windows_names,nofail  0 0
  ```

  `windows_names` stops Linux programs from creating file names that Windows cannot open. These builds wrap 7-Zip so mod archives with Windows-style folder names still unpack under that option.
- **Turn off Windows Fast Startup and hibernation.** While Windows is hibernated, the drive will not mount, or mounts read-only. In Windows, go to Control Panel → Power Options → "Choose what the power buttons do", then untick "Turn on fast startup".
- **Decompress the game folder if Windows compressed it.** Wine cannot run programs stored with NTFS or "CompactOS" compression (Windows' `compact` command, or tools like CompactGUI). A compressed game or mod loader fails to start, often with an unhelpful error. In Windows, decompress the game folder: CompactGUI's **Decompress** button, or in a Command Prompt opened in the game folder:

  ```text
  compact /u /s /a /i /q
  compact /u /exe /s /a /i /q
  ```
- **Keep Proton prefixes on a Linux filesystem if you can.** Prefixes (`steamapps/compatdata/<appid>`) on NTFS cause odd failures. With Steam closed, you can move `compatdata` to a Linux drive and leave a symlink in its place. Back up your saves first; they live inside the prefix.

## 8. Update

1. Download the new release, check it, and unpack it next to the old one.
2. Run the new folder's `install-desktop.sh`, so the menu entry points at it.
3. Start Vortex. Once it works, delete the old folder.

Your settings, profiles, staging and downloads stay where they are. Vortex's built-in updater is made for the Windows installer, so get new versions from this repository's releases.

## 9. Uninstall

1. In Vortex, **Mods → Purge** for each managed game. This takes the deployed mods out of the game folders.
2. Run `install-desktop.sh --remove`, then delete the Vortex folder.
3. Optional:
   - `~/.config/Vortex` (settings and profiles)
   - your staging and download folders (the mods themselves)
   - `~/.dotnet` (if nothing else uses it)

## 10. Troubleshooting

Start Vortex from a terminal (`vortex.sh`) to see errors, and look at `~/.config/Vortex/vortex.log`.

| What you see | Cause and fix |
| --- | --- |
| Vortex shows "Check failed: Vortex requires .NET Desktop Runtime 9" and only offers **Quit Vortex** | The .NET 9 runtime is missing, or Vortex cannot see it. Install it ([section 2](#2-the-net-9-runtime)). With Option A, start Vortex through `vortex.sh` or the menu entry, not the `vortex` binary. |
| Vortex does not start; the terminal says "The SUID sandbox helper binary was found, but is not configured correctly" or "No usable sandbox!" | Your distro blocks the user namespaces Electron's sandbox uses (Ubuntu 24.04 and newer do this through AppArmor). The safe fix is an AppArmor profile for Vortex; see [below](#electron-sandbox-on-ubuntu-2404-and-newer). The quick, less safe fix is `VORTEX_NO_SANDBOX=1 ./vortex.sh`. |
| `version 'GLIBC_2.xx' not found` | Your distro's glibc is older than the release's floor. Use a newer distro release, or build Vortex yourself on your system ([CONTRIBUTING.md](../CONTRIBUTING.md)). |
| "no deployment method available" | The staging folder is on a different drive from the game ([section 6](#6-manage-a-steam-game)). |
| Mod installs fail with "Invalid argument" or `errno=22` | Normally fixed by the 7-Zip wrapper in these builds. Check that you started `vortex.sh` from an unpacked release, then report it with the mod's name. |
| A FOMOD mod installs every option folder, or the log says "Failed to load native FOMOD module" | It should not happen with these builds; please report it. Include `ldd <folder>/resources/app.asar.unpacked/node_modules/@nexusmods/fomod-installer-native/build/Release/modinstaller.node`. |
| Mod loaders (CET, RED4ext, script extenders) do not load in game | Add the DLL overrides to the game's launch options ([section 6](#6-manage-a-steam-game)). Check the loader's own log in the game folder. |
| "Mod Manager Download" does nothing | Run `install-desktop.sh --check`. Browsers installed as Flatpak or Snap may not open `nxm://` links; download manually and drag the file into Vortex. |
| The game or a loader fails to start from an NTFS drive | The files may be compressed by Windows ([section 7](#7-games-on-an-ntfs-windows-drive)). |
| In a game on a scaled display (125%, 150%), clicks land beside the cursor | A display-scaling issue between Wayland and XWayland, not Vortex. Run the game at scale 1; how you do that depends on your desktop. |

### Electron sandbox on Ubuntu 24.04 and newer

Vortex is an Electron app, and Electron's sandbox needs unprivileged user namespaces. Ubuntu 24.04 and newer allow them only for programs with an AppArmor profile. Create one for Vortex; adjust the path if you unpacked somewhere other than `~/Applications`:

```bash
sudo tee /etc/apparmor.d/vortex-linux >/dev/null <<'EOF'
abi <abi/4.0>,
include <tunables/global>

profile vortex-linux /home/*/Applications/vortex-*-linux-x64/vortex flags=(unconfined) {
  userns,
  include if exists <local/vortex-linux>
}
EOF
sudo apparmor_parser -r /etc/apparmor.d/vortex-linux
```

The `/home/*` part matches any user's home folder. Then start Vortex normally. To check whether your system has the restriction:

```bash
cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns   # 1 = restricted
```

## 11. Report a problem

Open an issue with the [bug report form](https://github.com/McNayr/vortex-linux/issues/new/choose). If Vortex works on a distro not yet in the [compatibility table](../README.md#compatibility), the **Distro report** form is the place to say so. Include what the form asks for. Remove personal details from logs before you paste them: your user name in paths, your Nexus user name, and anything else private.

Problems that also happen with the official Windows Vortex belong upstream, at [Nexus-Mods/Vortex](https://github.com/Nexus-Mods/Vortex/issues).
