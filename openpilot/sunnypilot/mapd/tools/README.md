# TomTom provider and telemetry

Provider settings live in `/data/sunnypilot/slc.json`. To disable OSM speed-limit substitution:

```json
{"speedLimitProvider":"tomtom","tomtomOsmFallbackEnabled":false}
```

Restart mapd_manager after changing provider policy. The publisher continues using validated TomTom results and their persistent cache, including during network failures while the current result remains usable. Without a usable TomTom result, it publishes no current map limit and no upcoming map limit. The SLC resolver's existing retained-target behavior remains in effect; a retained target is not presented as a freshly verified road limit. Vehicle-reported limits still follow the configured SLC source policy.

OSM continues supplying road geometry and names for matching. Setting `tomtomOsmFallbackEnabled` to `true` restores the validated OSM speed-limit fallback. Selecting `speedLimitProvider: "osm"` runs the existing OSM-only mode.

Audit observations distinguish active TomTom, OSM, and no usable provider. Last verified TomTom limit/time are provenance, not a replacement current map observation. The on-road source indicator keeps a TT label during TomTom-only gaps, using amber for retained provenance and gray when unavailable.

The opt-in telemetry bridge reads `/data/sunnypilot/slc-telemetry.json`. It uses the comma's existing runtime, exports fresh localization/GPS and SLC audit messages, and reads nearby unexpired persistent TomTom corridors without making additional provider API requests. Webapp source and deployment registration live in `~/dev/co/slc.e7ad.cc` and `~/dev/co/config.json`.
