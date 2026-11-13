#!/usr/bin/env bash
# Put scripts/7zzs-wrapper.py in front of the 7-Zip bundled with a native
# Vortex build, so mod archives with Windows-style folder names
# ("archive\pc\mod\x") unpack into folders instead of failing (see the
# wrapper's docstring).
#
#   install-7z-wrapper.sh --check  APP   exit 0 if the current wrapper is installed
#   install-7z-wrapper.sh --apply  APP   install or refresh it (safe to rerun)
#   install-7z-wrapper.sh --revert APP   put the plain 7-Zip back
#
# APP is the unpacked Vortex folder (the one holding the `vortex` binary).
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
mode=${1:-}
app=${2:-}
if [[ -z ${SEVENZ_BIN:-} && -z $app ]]; then sed -n '2,12p' "$0" >&2; exit 2; fi
BIN=${SEVENZ_BIN:-$app/resources/app.asar.unpacked/node_modules/7z-bin/linux/7zzs}
WRAP=$here/scripts/7zzs-wrapper.py
MARK='vortex-linux-7z-backslash-wrapper v1'

is_wrapper() { grep -qF "$MARK" "$1" 2>/dev/null; }
is_elf() { [[ -f $1 ]] && [[ $(head -c 4 "$1" | od -An -tx1 | tr -d ' \n') == 7f454c46 ]]; }

case $mode in
  --check)
    if is_wrapper "$BIN" && is_elf "$BIN.real"; then
      if cmp -s "$WRAP" "$BIN"; then echo "OK: 7-Zip wrapper installed ($BIN)"; exit 0; fi
      echo "WARN: 7-Zip wrapper installed but older than $WRAP (rerun --apply)"; exit 1
    fi
    echo "NOT INSTALLED: $BIN is the plain 7-Zip"; exit 1 ;;
  --apply)
    [[ -e $BIN ]] || { echo "FAIL: $BIN missing (not a Vortex build?)"; exit 2; }
    if ! is_wrapper "$BIN"; then
      is_elf "$BIN" || { echo "FAIL: $BIN is neither 7-Zip nor the wrapper; left alone"; exit 2; }
      mv -f "$BIN" "$BIN.real"
    fi
    is_elf "$BIN.real" || { echo "FAIL: $BIN.real is not 7-Zip"; exit 2; }
    install -m 755 "$WRAP" "$BIN.wrapper-tmp"
    mv -f "$BIN.wrapper-tmp" "$BIN"
    echo "OK: 7-Zip wrapper installed at $BIN (real 7-Zip kept as $BIN.real)" ;;
  --revert)
    if ! is_wrapper "$BIN"; then echo "not installed"; exit 0; fi
    is_elf "$BIN.real" || { echo "FAIL: $BIN.real missing or not 7-Zip"; exit 1; }
    mv -f "$BIN.real" "$BIN"
    echo "reverted: $BIN is the plain 7-Zip again" ;;
  *)
    sed -n '2,12p' "$0" >&2; exit 2 ;;
esac
