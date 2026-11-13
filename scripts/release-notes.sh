#!/usr/bin/env bash
# Print the GitHub release notes (Markdown) for a packaged build.
#
#   scripts/release-notes.sh TAG BUILD STAGE
#
# STAGE is the unpacked package folder that scripts/package.sh made.
set -euo pipefail
[[ $# -eq 3 ]] || { sed -n '2,6p' "$0" >&2; exit 2; }
TAG=$1 BUILD=$2 STAGE=$3
VERSION=${TAG#v}
NAME=vortex-$VERSION-linux-x64
repo=${GITHUB_REPOSITORY:-McNayr/vortex-linux}
rev=${GITHUB_SHA:-main}
floor=$(grep -m1 '^minimum glibc' "$STAGE/BUILD-INFO.txt" | sed 's/^minimum glibc: /glibc /')
cat <<EOF
Unofficial native Linux build of [Vortex $VERSION](https://github.com/Nexus-Mods/Vortex/releases/tag/$TAG), the mod manager from Nexus Mods, built by GitHub Actions from the upstream tag (build $BUILD). Not affiliated with Nexus Mods.

### Install

\`\`\`bash
sha256sum -c $NAME.tar.xz.sha256
tar -xf $NAME.tar.xz -C ~/Applications   # or any folder you like
~/Applications/$NAME/install-desktop.sh   # app-menu entry, and nxm:// links open Vortex
~/Applications/$NAME/vortex.sh
\`\`\`

The full walkthrough, including the .NET 9 runtime and managing Steam games under Proton, is in the [setup guide](https://github.com/$repo/blob/main/docs/SETUP.md). You can also hand [this prompt](https://github.com/$repo/blob/main/docs/AGENT_PROMPT.md) to an AI coding agent and let it walk you through it.

### Needs

- x86-64 Linux with $floor or newer (check with \`ldd --version\`)
- the .NET 9 runtime (Vortex quits at startup without it)
- python3, and a desktop session (Wayland or X11)

### Linux fixes in this build

- FOMOD installers work wherever you unpack the folder: the native FOMOD module loads its library from its own folder ([Nexus-Mods/Vortex#23565](https://github.com/Nexus-Mods/Vortex/issues/23565)).
- Mod archives that store Windows-style folder names (\`archive\\pc\\mod\\...\`) unpack into real folders.

### Tested on

See the [compatibility table](https://github.com/$repo#compatibility). If it misbehaves on your distro, please [open an issue](https://github.com/$repo/issues/new/choose).

Source: [Vortex $TAG](https://github.com/Nexus-Mods/Vortex/tree/$TAG) (GPL-3.0) and [the build scripts at this commit](https://github.com/$repo/tree/$rev). \`BUILD-INFO.txt\` in the archive records the exact commits.
EOF
