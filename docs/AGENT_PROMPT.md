# Let an AI agent set it up for you

You can hand this prompt to an AI coding agent that runs on your computer and can use a terminal, for example Claude Code, Codex CLI or Gemini CLI. The agent reads the setup guide, checks your system, explains each step, and does the safe parts for you. It stops and asks before anything that needs your password or changes your system.

How to use it:

1. Install and start an agent of your choice in a terminal (see the agent's own instructions).
2. Copy everything in the box below and paste it as your first message.
3. Answer its questions. You type passwords yourself, in your terminal, never in the chat.

````text
Help me install the unofficial native Linux build of Vortex (the Nexus Mods
mod manager) from https://github.com/McNayr/vortex-linux on this computer,
and set it up to manage my game(s).

First, read the setup guide:
https://raw.githubusercontent.com/McNayr/vortex-linux/main/docs/SETUP.md
Follow it; it is the source of truth. Work through it one step at a time.

Rules:
- Before you change anything, check my system with read-only commands and
  summarize what you found: distro and version (/etc/os-release), CPU
  architecture (uname -m), glibc version (ldd --version), desktop session
  (XDG_SESSION_TYPE, XDG_CURRENT_DESKTOP), python3, any .NET runtimes
  (dotnet --list-runtimes, ~/.dotnet), whether Steam is installed natively
  or as a Flatpak and where its libraries are (libraryfolders.vdf), the
  filesystem of each game library (findmnt -T <path>), and whether
  /proc/sys/kernel/apparmor_restrict_unprivileged_userns exists and is 1.
  Then tell me which release fits and whether anything blocks it (for
  example a glibc older than the release needs).
- Get the release from the GitHub releases of McNayr/vortex-linux. Download
  both the .tar.xz and its .sha256, run sha256sum -c, and stop if it does
  not print OK.
- Do everything you can without root yourself: the .NET 9 runtime goes in
  ~/.dotnet with Microsoft's dotnet-install.sh, Vortex in a folder I agree
  to (default ~/Applications), and install-desktop.sh for the menu entry.
- Never run sudo yourself and never ask for my password. If a step needs
  root (a distro package, an AppArmor profile, /etc/fstab), show me the
  exact command, explain what it does, and let me run it in my own terminal.
- Ask before you delete, move or overwrite anything outside the new Vortex
  folder. Never touch game files, saves, or Proton prefixes
  (steamapps/compatdata) unless I agree, and back up first.
- On a Steam Deck or another immutable distro (SteamOS, Bazzite), use only
  the no-root paths. Do not disable the read-only system.
- Once Vortex starts, walk me through the settings in the guide's
  "Manage a Steam game" section: the staging folder on the same drive as
  the game, hardlink deployment, and launch options for mod loaders.
  I click through Vortex myself; you tell me what to set.
- If something fails, use the guide's troubleshooting table, read
  ~/.config/Vortex/vortex.log, and explain the cause before you try a fix.
  Don't loop on the same failing command.
- Keep my privacy: don't paste logs or system details anywhere online. If
  I want to report a problem or a working distro, draft the issue text
  for me with my user name, home folder path, and other personal details
  replaced, and I will submit it myself.

At the end, tell me: what you installed and where, what changed outside
that folder, how to update or remove Vortex later, and anything left for
me to do.
````

Agents can make mistakes. Read what yours suggests, especially commands that need your password, before you run them.
