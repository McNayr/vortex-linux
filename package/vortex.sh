#!/usr/bin/env bash
# Start Vortex from this folder.
#
#   ./vortex.sh [ARGS...]
#
# - An nxm:// link (the "Mod Manager Download" buttons on nexusmods.com)
#   becomes `--download <link>`; a running Vortex takes it over.
# - When the .NET 9 runtime is installed only in ~/.dotnet (the no-root
#   install, for example on SteamOS), DOTNET_ROOT points there, so Vortex's
#   startup check finds it.
# - VORTEX_NO_SANDBOX=1 adds --no-sandbox. Only for systems that block
#   Electron's sandbox and have no AppArmor profile for it (see docs/SETUP.md).
set -euo pipefail
here=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)
bin=${VORTEX_BIN:-$here/vortex}
if [[ ! -x $bin ]]; then
  echo "vortex.sh: $bin is missing; unpack the whole release archive and start vortex.sh from inside it" >&2
  exit 1
fi
if [[ -z ${DOTNET_ROOT:-} && -x $HOME/.dotnet/dotnet ]] && compgen -G "$HOME/.dotnet/shared/Microsoft.NETCore.App/9.*" >/dev/null; then
  export DOTNET_ROOT=$HOME/.dotnet
fi
args=()
if [[ ${VORTEX_NO_SANDBOX:-} == 1 ]]; then args+=(--no-sandbox); fi
for a in "$@"; do
  if [[ $a == nxm://* ]]; then args+=(--download "$a"); else args+=("$a"); fi
done
exec "$bin" ${args[@]+"${args[@]}"}
