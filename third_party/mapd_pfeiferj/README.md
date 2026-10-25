# MAPD implementation by pfeiferj
https://github.com/pfeiferj/openpilot-mapd/releases/

The binary is built from tag `v1.12.0` (`46cd71ade6f630f1564c83bf1763f9d949a9ff30`).
The only source extension adds the memory param `MapRoadCorridor`; after `NextWays`
is computed it atomically writes version 1 JSON containing directed current-way
nodes, cumulative progress, `min(1, ConfidenceCounter/5)`, the SHA-256 of
six-decimal directed coordinates, and the first three directed `NextWays`.
Build command:

    GOOS=linux GOARCH=arm64 CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o mapd .
