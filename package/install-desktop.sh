#!/usr/bin/env bash
# Add Vortex to the app menu and make it open nxm:// links (the
# "Mod Manager Download" buttons on nexusmods.com).
#
#   ./install-desktop.sh            install, or refresh after moving this folder
#   ./install-desktop.sh --check    report only
#   ./install-desktop.sh --remove   take the menu entry and the icon out again
#
# Writes ~/.local/share/applications/com.nexusmods.vortex.desktop (the ID that
# Vortex's own nxm:// handling expects) and the icon. Needs no root.
set -euo pipefail
here=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)
data=${XDG_DATA_HOME:-$HOME/.local/share}
apps=$data/applications
icon_dir=$data/icons/hicolor/256x256/apps
id=com.nexusmods.vortex
desktop=$apps/$id.desktop
icon=$icon_dir/$id.png
launcher=$here/vortex.sh

entry() {
  cat <<EOF
[Desktop Entry]
Type=Application
Name=Vortex
GenericName=Mod Manager
Comment=Nexus Mods mod manager (unofficial native Linux build)
Exec="$launcher" %u
TryExec=$launcher
Icon=$id
Terminal=false
Categories=Game;
MimeType=x-scheme-handler/nxm;
StartupWMClass=vortex
EOF
}

check() {
  local rc=0 handler
  if [[ -f $desktop ]] && diff -q <(entry) "$desktop" >/dev/null; then
    echo "OK:   menu entry $desktop"
  else
    echo "INFO: menu entry missing, or it starts Vortex from another folder: $desktop"; rc=1
  fi
  handler=$(xdg-mime query default x-scheme-handler/nxm 2>/dev/null || true)
  if [[ $handler == "$id.desktop" ]]; then
    echo "OK:   nxm:// links open Vortex"
  else
    echo "INFO: nxm:// links open '${handler:-nothing}', not Vortex"; rc=1
  fi
  return "$rc"
}

remove() {
  rm -f -- "$desktop" "$icon"
  if command -v update-desktop-database >/dev/null; then update-desktop-database "$apps" 2>/dev/null || true; fi
  echo "removed $desktop and $icon"
  echo "nxm:// links do nothing until another app claims them. This folder and ~/.config/Vortex are untouched."
}

case ${1:-} in
  --check) check; exit $? ;;
  --remove) remove; exit 0 ;;
  "") ;;
  *) sed -n '2,10p' "$0" >&2; exit 2 ;;
esac

case $launcher in
  *[\"\`\$\\%]*)
    echo "install-desktop.sh: menu entries cannot hold this folder's path (it contains \" \` \$ \\ or %); move the folder and run this again: $here" >&2
    exit 2 ;;
esac
if [[ ! -x $launcher ]]; then
  echo "install-desktop.sh: $launcher is missing; unpack the whole release archive" >&2
  exit 2
fi
mkdir -p "$apps" "$icon_dir"
if [[ -f $here/vortex.png ]]; then install -m 0644 "$here/vortex.png" "$icon"; fi
entry > "$desktop.tmp" && mv -f "$desktop.tmp" "$desktop"
if command -v desktop-file-validate >/dev/null; then
  desktop-file-validate "$desktop" || echo "WARN: desktop-file-validate reported problems with $desktop" >&2
fi
if command -v update-desktop-database >/dev/null; then update-desktop-database "$apps" 2>/dev/null || true; fi
if command -v xdg-mime >/dev/null; then
  xdg-mime default "$id.desktop" x-scheme-handler/nxm
else
  echo "WARN: xdg-mime not found (package xdg-utils); nxm:// links will not open Vortex" >&2
fi
check || true
