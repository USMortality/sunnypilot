#!/usr/bin/env bash
# Rebuild the bundled ARM64 binary from the pinned upstream release and patch.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
build_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir"' EXIT
git clone --quiet https://github.com/pfeiferj/openpilot-mapd.git "$build_dir"
git -C "$build_dir" checkout --quiet 46cd71ade6f630f1564c83bf1763f9d949a9ff30
git -C "$build_dir" apply "$script_dir/patches/road-geometry.patch"
cd "$build_dir"
go test ./...
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -trimpath -ldflags='-extldflags=-static -s -w' -o "$script_dir/mapd"
