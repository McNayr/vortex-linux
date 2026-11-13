#!/usr/bin/env bash
# Tests for package/install-desktop.sh with a fake xdg-mime and a temporary home.
set -uo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d "${TMPDIR:-/tmp}/vortex-desktop-test.XXXXXX")
trap 'rm -rf "$T"' EXIT
pass=0; failn=0
t() { if eval "$2"; then pass=$((pass + 1)); echo "ok   - $1"; else failn=$((failn + 1)); echo "FAIL - $1"; fi; }

mkdir -p "$T/bin" "$T/state" "$T/home"
cat > "$T/bin/xdg-mime" <<'EOF'
#!/usr/bin/env bash
# fake: remembers `xdg-mime default ID MIME`, answers `xdg-mime query default MIME`
case "$1 $2" in
  "default "*) echo "$2" > "$FAKE_STATE/nxm" ;;
  "query default") cat "$FAKE_STATE/nxm" 2>/dev/null || true ;;
esac
EOF
chmod +x "$T/bin/xdg-mime"
export FAKE_STATE=$T/state HOME=$T/home XDG_DATA_HOME=$T/home/.local/share PATH="$T/bin:$PATH"
D=$XDG_DATA_HOME/applications/com.nexusmods.vortex.desktop
ICON=$XDG_DATA_HOME/icons/hicolor/256x256/apps/com.nexusmods.vortex.png

pkg() {  # a fake unpacked release at $1
  mkdir -p "$1"
  cp "$here/package/install-desktop.sh" "$here/package/vortex.sh" "$1/"
  printf 'png' > "$1/vortex.png"
}

pkg "$T/My Games/vortex"
bash "$T/My Games/vortex/install-desktop.sh" >"$T/out" 2>&1; rc=$?
t "install exits 0" '[[ $rc -eq 0 ]]'
t "the menu entry is written" '[[ -f $D ]]'
t "Exec quotes a path with spaces" 'grep -qxF "Exec=\"$T/My Games/vortex/vortex.sh\" %u" "$D"'
t "the entry handles nxm:// links" 'grep -qxF "MimeType=x-scheme-handler/nxm;" "$D"'
t "the icon is installed" '[[ $(cat "$ICON") == png ]]'
t "nxm:// links go to Vortex" '[[ $(cat "$T/state/nxm") == com.nexusmods.vortex.desktop ]]'
bash "$T/My Games/vortex/install-desktop.sh" --check >/dev/null; rc=$?
t "--check passes after install" '[[ $rc -eq 0 ]]'

pkg "$T/elsewhere"
bash "$T/elsewhere/install-desktop.sh" >/dev/null 2>&1
t "rerunning from a moved folder updates Exec" 'grep -qxF "Exec=\"$T/elsewhere/vortex.sh\" %u" "$D"'
bash "$T/My Games/vortex/install-desktop.sh" --check >/dev/null; rc=$?
t "--check from the old folder reports the stale entry" '[[ $rc -eq 1 ]]'

pkg "$T/bad\"quote"
bash "$T/bad\"quote/install-desktop.sh" >/dev/null 2>&1; rc=$?
t "a folder path with a double quote is refused, entry untouched" '[[ $rc -eq 2 ]] && grep -qxF "Exec=\"$T/elsewhere/vortex.sh\" %u" "$D"'

bash "$T/elsewhere/install-desktop.sh" --remove >/dev/null; rc=$?
t "--remove exits 0" '[[ $rc -eq 0 ]]'
t "--remove deletes the entry and the icon" '[[ ! -e $D && ! -e $ICON ]]'
bash "$T/elsewhere/install-desktop.sh" --check >/dev/null; rc=$?
t "--check fails after --remove" '[[ $rc -eq 1 ]]'
bash "$T/elsewhere/install-desktop.sh" --bogus >/dev/null 2>&1; rc=$?
t "an unknown option exits 2" '[[ $rc -eq 2 ]]'

echo "passed=$pass failed=$failn"
(( failn == 0 ))
