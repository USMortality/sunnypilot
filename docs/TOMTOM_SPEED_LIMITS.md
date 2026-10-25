# Optional TomTom speed limits

OSM remains the matcher, topology/name source, and complete fallback. `mapd_manager`
remains the only `liveMapDataSP` publisher. TomTom is opt-in and changes neither the
message schema nor the planner/SLC acceptance interface.

## Configuration

Add `"speedLimitProvider": "tomtom"` to `/data/sunnypilot/slc.json`, preserving
the other settings in that file. Create it only if it does not already exist;
replacing it with just the provider selection resets lookahead and idle/N settings
to their defaults. The default provider is `osm`.
`tomtomMonthlyRequestLimit` optionally overrides the local 75,000 calendar-month
request guard. This is not a daily rate limit or a guarantee of the account's free
allowance; check the account's Snap to Roads entitlement separately.

Put the credential only in `/data/sunnypilot/provider-keys.env`:

    TOMTOM_API_KEY=...
    chmod 0600 /data/sunnypilot/provider-keys.env

The key is read in place and is never logged or copied. Do not add either file to
the repository or copy it to a device as part of development/testing.

## Behavior and limitations

The existing native mapd publishes its selected road geometry through
`MapCurvatures`. Python reads that geometry, computes vehicle progress and a
directed fingerprint, and submits a roughly 200–1,000 m corridor to synchronous
Snap to Roads. It includes headings when available and requests projected-point
status plus route geometry, IDs, confidence, traveled distance, form-of-way, and
maximum speed limits. No new native mapd publisher or `MapRoadCorridor` parameter
is required. The parser also accepts a richer corridor format, but native mapd
does not currently provide its confidence or continuation metadata through this
integration; route choice still relies on native mapd's selected geometry.

Results must cover and align with the directed OSM corridor, stay within lateral
and detour bounds, and meet confidence thresholds. A complete validated snapshot
provides both present and upcoming limits and geometry-derived transition distance.
Unknown present limits, explicitly ambiguous corridors, expiry, mismatch, timeout,
or budget exhaustion atomically retain OSM values. Fork ambiguity cannot be
independently detected when the native feed only supplies a selected polyline.
Requests use one background worker, connection/read timeouts, deduplication, and
exponential negative-result backoff.

The first available location and road geometry trigger a fetch immediately; no
vehicle movement is required. The request window follows the current position
along the road. If curvature nodes begin ahead of the vehicle, the current
position is included when it lies within 150 m of the first node and within 20 m
of the backward extension of the first road segment. Before each API request, the background worker verifies a trusted
TLS connection to TomTom. Offline waits do not consume the request budget or
increase failure backoff, and connectivity is retried every five seconds. Valid
cached limits remain usable offline; otherwise OSM supplies the fallback.
Once an API request is attempted, it counts against the local budget even if it
subsequently fails or times out, because delivery to the server is uncertain.

The SQLite file is `/data/sunnypilot/tomtom-cache.sqlite`, bounded to 2,048 entries. Entries contain
the normalized directed/versioned key, response geometry and speed sections,
provenance, fetch time, and expiry. Entries persist across drives and expire after
30 days.

Identical request windows reuse cached results across drives until expiry.
Request counts depend on available corridor length, route changes, validation
results, and connectivity; they are not fixed per kilometre.

## Diagnostics and source indication

Diagnostic files are disabled by default. Add `"tomtomDebugLogging": true` to
the existing config before starting mapd to enable the redacted `/tmp/tomtom_*`
request, response-summary, corridor, validation, and worker diagnostics.
`/tmp/tomtom_active` is always written as runtime status for the TT/OSM UI
indicator. Road names remain unprefixed. Heading normalization is intentional at
both boundaries: native mapd receives compass bearings, and the API client also
guards direct callers and invalid headings.

## Testing and bounded live validation

Run:

    pytest -q openpilot/sunnypilot/mapd/tests/test_tomtom_map_data.py openpilot/sunnypilot/selfdrive/controls/lib/speed_limit/tests
    python -m openpilot.sunnypilot.mapd.tools.validate_tomtom corridor.json

The script is dry-run by default. `--live` requires the key file, redacts the key,
performs one Snap to Roads call, records only status/cache/expiry/tracking header
evidence and a structural summary, and never exceeds one call. Compare its geometry
manually with a Calculate Route reconstruction for the same bounded points if the
development key is entitled to Routing; do not store either raw keyed URL or key.
