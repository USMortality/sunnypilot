# Optional TomTom speed limits

OSM remains the matcher, topology/name source, and complete fallback. `mapd_manager`
remains the only `liveMapDataSP` publisher. TomTom is opt-in and changes neither the
message schema nor the planner/SLC acceptance interface.

## Configuration

Create `/data/sunnypilot/slc.json` with `"speedLimitProvider": "tomtom"` (the
default is `osm`). `tomtomMonthlyRequestLimit` optionally overrides the conservative
75,000 calendar-month guard, derived from the currently advertised 2,500/day
non-tile allowance rather than a quota for another TomTom product. Recheck the
account's current Snap to Roads entitlement before changing it.

Put the credential only in `/data/sunnypilot/provider-keys.env`:

    TOMTOM_API_KEY=...
    chmod 0600 /data/sunnypilot/provider-keys.env

The key is read in place and is never logged or copied. Do not add either file to
the repository or copy it to a device as part of development/testing.

## Behavior and limitations

The rebuilt pinned mapd publishes a directed OSM geometry, progress, a stable
geometry fingerprint, match confidence, and at most three plausible continuations
through the shared-memory `MapRoadCorridor` parameter. The Python worker submits a
roughly 500–1,000 m corridor to synchronous Snap to Roads with headings where
available and requests only projected-point status plus route geometry, IDs,
confidence, traveled distance, form-of-way, and maximum speed limits.

Results must cover and align with the directed OSM corridor, stay within lateral
and detour bounds, and meet confidence thresholds. A complete validated snapshot
provides both present and upcoming limits and geometry-derived transition distance.
Unknown present limits, ambiguity, forks not yet selected by OSM progress/matching,
expiry, mismatch, timeout, or budget exhaustion atomically retain OSM values.
Requests use one background worker, connection/read timeouts, deduplication, and
exponential negative-result backoff.

The bounded SQLite file is `/data/sunnypilot/tomtom-cache.sqlite`. Entries contain
the normalized directed/versioned key, response geometry and speed sections,
provenance, fetch time, and expiry. Cache reuse is drive/session scoped unless a
Snap to Roads response expressly supplies cacheable `max-age` directives. This is
intentional: endpoint-specific retention permission has not otherwise been
established. Terms and pricing can change; verify both before enabling broader reuse.

At 500–1,000 m per corridor, a 20 km first drive is approximately 20–40 successful
calls plus bounded retries. Reuse during the same drive should make an immediate
repeat approximately zero calls. A later drive remains 20–40 by default because
cross-drive retention is disabled without affirmative response-header evidence.

## Testing and bounded live validation

Run:

    pytest -q sunnypilot/mapd/tests sunnypilot/selfdrive/controls/lib/speed_limit/tests
    python sunnypilot/mapd/tools/validate_tomtom.py corridor.json

The script is dry-run by default. `--live` requires the key file, redacts the key,
performs one Snap to Roads call, records only status/cache/expiry/tracking header
evidence and a structural summary, and never exceeds two calls. Compare its geometry
manually with a Calculate Route reconstruction for the same bounded points if the
development key is entitled to Routing; do not store either raw keyed URL or key.
