#!/usr/bin/env bash
# Rebuild the bundled ARM64 binary from the pinned upstream release and patch.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export GOENV=off
export GOFLAGS=
export GOEXPERIMENT=
export GOTOOLCHAIN="go$(cat "$script_dir/.go-version")"
if [[ "$(go env GOVERSION)" != "$GOTOOLCHAIN" ]]; then
  echo "mapd requires $GOTOOLCHAIN" >&2
  exit 1
fi
build_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir"' EXIT
git clone --quiet https://github.com/pfeiferj/openpilot-mapd.git "$build_dir"
git -C "$build_dir" checkout --quiet 46cd71ade6f630f1564c83bf1763f9d949a9ff30
git -C "$build_dir" apply --unidiff-zero "$script_dir/patches/road-geometry.patch"
cd "$build_dir"
go test ./...
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOARM64=v8.0 go build -buildvcs=false -trimpath -ldflags='-extldflags=-static -s -w' -o "$build_dir/mapd"
install -m 755 "$build_dir/mapd" "$script_dir/mapd.tmp"
mv -f "$script_dir/mapd.tmp" "$script_dir/mapd"
python3 - "$script_dir" <<'PY'
import hashlib
import os
import sys
from pathlib import Path

directory = Path(sys.argv[1])
digest = hashlib.sha256((directory / "mapd").read_bytes()).hexdigest()
temporary = directory / "mapd.sha256.tmp"
temporary.write_text(digest + "\n")
os.replace(temporary, directory / "mapd.sha256")
print(f"Bundled mapd SHA-256: {digest}")
PY
