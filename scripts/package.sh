#!/usr/bin/env bash
# Turn a Vortex build into the release archive.
#
#   scripts/package.sh SRC TAG OUT
#
# SRC is the Vortex checkout after scripts/build-vortex.sh (it holds
# dist/linux-unpacked); TAG is its release tag, for example v2.10.1.
# Copies the build to OUT/vortex-<version>-linux-x64, applies the Linux fixes
# (the 7-Zip wrapper, the movable FOMOD module), adds the launcher, the
# desktop installer, the icon, the GPL text and BUILD-INFO.txt, checks the
# result, then writes OUT/vortex-<version>-linux-x64.tar.xz and its .sha256.
# The build in SRC is not changed.
set -euo pipefail
here=$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)
usage() { sed -n '2,12p' "$0" >&2; exit 2; }
[[ $# -eq 3 ]] || usage
SRC=$1 TAG=$2 OUT=$3
[[ $TAG =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "package.sh: not a release tag: $TAG" >&2; exit 2; }
VERSION=${TAG#v}
NAME=vortex-$VERSION-linux-x64
DIST=$SRC/dist/linux-unpacked
STAGE=$OUT/$NAME
[[ -x $DIST/vortex ]] || { echo "package.sh: no Vortex build at $DIST" >&2; exit 2; }
[[ ! -e $STAGE && ! -e $OUT/$NAME.tar.xz ]] || { echo "package.sh: $OUT already holds $NAME; use an empty folder" >&2; exit 2; }

mkdir -p "$OUT"
cp -a "$DIST" "$STAGE"
bash "$here/scripts/install-7z-wrapper.sh" --apply "$STAGE"
python3 "$here/scripts/vortex-relocate.py" --apply "$STAGE"
find "$STAGE" -name '*.relocate-orig' -type f -delete
install -m 755 "$here/package/vortex.sh" "$here/package/install-desktop.sh" "$STAGE/"
install -m 644 "$SRC/assets/images/vortex.png" "$STAGE/vortex.png"
install -m 644 "$SRC/LICENSE.md" "$STAGE/LICENSE-Vortex.md"

python3 "$here/scripts/vortex-relocate.py" --check "$STAGE" >/dev/null || { echo "package.sh: an absolute RUNPATH is left" >&2; exit 1; }
bash "$here/scripts/install-7z-wrapper.sh" --check "$STAGE" >/dev/null || { echo "package.sh: the 7-Zip wrapper is not in place" >&2; exit 1; }

upstream=$(git -C "$SRC" rev-parse HEAD 2>/dev/null || echo unknown)
scripts_rev=$(git -C "$here" rev-parse HEAD 2>/dev/null || echo unknown)
repo=${GITHUB_REPOSITORY:-McNayr/vortex-linux}
{
  echo "Vortex $VERSION for Linux, unofficial build (not affiliated with Nexus Mods)"
  echo "upstream: https://github.com/Nexus-Mods/Vortex/tree/$TAG (commit $upstream)"
  echo "build scripts: https://github.com/$repo/tree/$scripts_rev"
  if [[ -n ${GITHUB_RUN_ID:-} ]]; then echo "CI run: ${GITHUB_SERVER_URL:-https://github.com}/$repo/actions/runs/$GITHUB_RUN_ID"; fi
  echo "built: $(date -u '+%Y-%m-%d %H:%M UTC')"
  echo "Linux fixes: FOMOD module loads its library from its own folder (Nexus-Mods/Vortex#23565); 7-Zip unpacks Windows-style folder names"
  python3 "$here/scripts/elf-report.py" "$STAGE"
  echo "also needs: x86-64, the .NET 9 runtime, python3, a desktop session"
} > "$STAGE/BUILD-INFO.txt"

if [[ -z ${GITHUB_ACTIONS:-} ]] && grep -r -l -a -F -- "$HOME/" "$STAGE" >/dev/null 2>&1; then
  echo "package.sh: WARNING: this package mentions $HOME (build metadata). Fine for yourself; publish only CI builds." >&2
fi

tar -C "$OUT" --owner=0 --group=0 --numeric-owner --sort=name -cf - "$NAME" | xz -T0 -6 > "$OUT/$NAME.tar.xz"
(cd "$OUT" && sha256sum "$NAME.tar.xz" > "$NAME.tar.xz.sha256")
echo "$OUT/$NAME.tar.xz"
