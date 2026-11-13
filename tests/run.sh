#!/usr/bin/env bash
# Run every tests/test_*.sh and the Python tests; exit 1 if any fails.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
rc=0
for t in "$here"/test_*.sh; do
  echo "== $(basename "$t")"
  bash "$t" || rc=1
done
echo "== python tests"
python3 -m unittest discover -s "$here" -p 'test_*.py' || rc=1
exit "$rc"
