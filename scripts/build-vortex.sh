#!/usr/bin/env bash
# Build native Linux Vortex from the official repository at a release tag.
#
#   scripts/build-vortex.sh TAG SRC
#
# Clones Nexus-Mods/Vortex at TAG into SRC (or uses a clone already at TAG),
# installs dependencies with the pnpm version the tag pins, stamps the release
# version, packages with electron-builder (Linux target) and verifies the
# asar. Output: SRC/dist/linux-unpacked; then run scripts/package.sh.
#
# Needs: git, python3 (with setuptools on Python 3.12+), a C/C++ toolchain,
# the fontconfig headers (libfontconfig1-dev / fontconfig-devel), the Node
# version in the tag's package.json "engines", the pinned pnpm, the .NET 9 SDK.
set -euo pipefail
[[ $# -eq 2 ]] || { sed -n '2,14p' "$0" >&2; exit 2; }
TAG=$1 SRC=$2
[[ $TAG =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "build-vortex.sh: not a release tag: $TAG" >&2; exit 2; }
VERSION=${TAG#v}
REPO=${VORTEX_REPO:-https://github.com/Nexus-Mods/Vortex.git}

if [[ ! -d $SRC/.git ]]; then
  git clone --branch "$TAG" --depth 1 "$REPO" "$SRC"
elif [[ $(git -C "$SRC" describe --tags --exact-match 2>/dev/null) != "$TAG" ]]; then
  echo "build-vortex.sh: $SRC is not a clean clone of $TAG; use an empty folder" >&2
  exit 2
fi
git -C "$SRC" log -1 --format='source: %H %cI'

want=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["packageManager"].split("@")[1].split("+")[0])' "$SRC/package.json")
have=$(pnpm --version 2>/dev/null || echo none)
if [[ $have != "$want" ]]; then
  echo "build-vortex.sh: $TAG pins pnpm $want, found $have (npm install -g pnpm@$want)" >&2
  exit 2
fi
for tool in dotnet node python3; do
  command -v "$tool" >/dev/null || { echo "build-vortex.sh: $tool not found" >&2; exit 2; }
done
echo "node $(node --version), pnpm $have, dotnet $(dotnet --version)"

export NX_DAEMON=false NX_NO_CLOUD=true npm_config_python=${npm_config_python:-$(command -v python3)}
# electron-builder hardlinks instead of copying when it detects CI, and then fails
# with EEXIST where two unpack rules place the same file (winapi-bindings); copy
# like a local build does.
export USE_HARD_LINKS=false
cd "$SRC"
pnpm install --frozen-lockfile
# src/main/package.json holds the placeholder version 1.0.0 until a release stamps it.
pnpm -F @vortex/main version "$VERSION" --no-git-tag-version --no-git-checks --allow-same-version
NODE_ENV=production pnpm nx run @vortex/main:package:nosign --outputStyle=stream
# The verifier defaults to the Windows output (dist/win-unpacked); point it at Linux.
pnpm exec node scripts/verify-packaged-asar.mjs --asar dist/linux-unpacked/resources/app.asar
git restore src/main/package.json
ls -l dist/linux-unpacked/vortex
