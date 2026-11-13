#!/usr/bin/env bash
# Tests for package/vortex.sh with a fake Vortex binary.
set -uo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d "${TMPDIR:-/tmp}/vortex-launcher-test.XXXXXX")
trap 'rm -rf "$T"' EXIT
pass=0; failn=0
t() { if eval "$2"; then pass=$((pass + 1)); echo "ok   - $1"; else failn=$((failn + 1)); echo "FAIL - $1"; fi; }

mkdir -p "$T/pkg" "$T/home" "$T/links"
cp "$here/package/vortex.sh" "$T/pkg/"
cat > "$T/pkg/vortex" <<'EOF'
#!/usr/bin/env bash
printf '[%s]' "$@"; echo " DOTNET_ROOT=${DOTNET_ROOT:-}"
EOF
chmod +x "$T/pkg/vortex"
export HOME=$T/home
unset DOTNET_ROOT VORTEX_NO_SANDBOX VORTEX_BIN
L=$T/pkg/vortex.sh

out=$(bash "$L"); t "no arguments pass through as none" '[[ $out == "[] DOTNET_ROOT=" ]]'
out=$(bash "$L" 'nxm://cyberpunk2077/mods/107/files/1?key=a&expires=1')
t "an nxm link becomes --download <link>" '[[ $out == "[--download][nxm://cyberpunk2077/mods/107/files/1?key=a&expires=1] DOTNET_ROOT=" ]]'
out=$(bash "$L" --some-flag value); t "other arguments pass through unchanged" '[[ $out == "[--some-flag][value] DOTNET_ROOT=" ]]'
out=$(VORTEX_NO_SANDBOX=1 bash "$L" x); t "VORTEX_NO_SANDBOX=1 adds --no-sandbox" '[[ $out == "[--no-sandbox][x] DOTNET_ROOT=" ]]'

mkdir -p "$HOME/.dotnet/shared/Microsoft.NETCore.App/8.0.11"
printf '#!/bin/sh\n' > "$HOME/.dotnet/dotnet"; chmod +x "$HOME/.dotnet/dotnet"
out=$(bash "$L"); t "~/.dotnet with only .NET 8 is left alone" '[[ $out == "[] DOTNET_ROOT=" ]]'
mkdir -p "$HOME/.dotnet/shared/Microsoft.NETCore.App/9.0.11"
out=$(bash "$L"); t "~/.dotnet with .NET 9 becomes DOTNET_ROOT" '[[ $out == "[] DOTNET_ROOT=$HOME/.dotnet" ]]'
out=$(DOTNET_ROOT=/opt/dotnet bash "$L"); t "a DOTNET_ROOT already set wins" '[[ $out == "[] DOTNET_ROOT=/opt/dotnet" ]]'

ln -s "$L" "$T/links/vortex"
out=$(bash "$T/links/vortex" a); t "a symlink to vortex.sh finds the app next to the real script" '[[ $out == "[a] DOTNET_ROOT=$HOME/.dotnet" ]]'

VORTEX_BIN="$T/missing" bash "$L" >/dev/null 2>"$T/err"; rc=$?
t "a missing app exits 1 and says why" '[[ $rc -eq 1 ]] && grep -q "unpack" "$T/err"'

echo "passed=$pass failed=$failn"
(( failn == 0 ))
