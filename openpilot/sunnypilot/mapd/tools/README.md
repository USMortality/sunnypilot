# SLC telemetry bridge

The opt-in telemetry bridge reads `/data/sunnypilot/slc-telemetry.json` and
uploads fresh location samples and structured SLC decision events to the
configured HTTPS endpoint. It uses the comma's existing Python runtime and
does not make map-provider requests. Remove the configuration file to disable
the bridge.

The bridge and dashboard source are maintained outside this repository in
`~/dev/co/slc.e7ad.cc` and `~/dev/co/config.json`.
