# MAPD implementation by pfeiferj
https://github.com/pfeiferj/openpilot-mapd/releases/

The bundled v1.12.0 binary includes `patches/road-geometry.patch`. It publishes
`MapRoadGeometry` from the full current way and selected directed next ways,
before curvature smoothing drops the first and last two nodes. An unavailable
or disconnected continuation stops the polyline at the last known node while
preserving its valid prefix; an invalid current way still clears the geometry.
No road is extrapolated. Geometry copying gets a fresh bounded Cap'n Proto read
budget so earlier matcher traversals cannot discard the selected road.

The matcher bounding box uses the existing road-width distance threshold and
accounts for longitude scale at the current latitude. It does not increase
the final distance allowance or change the one-way heading checks. This fixes
recorded A5 lane positions rejected by a prefilter narrower than the road.
`MapCurvatures` and `MapTargetVelocities` calculations are unchanged; they use
the corrected current-way match.

Run `bash build.sh` with Go installed to test and rebuild the Linux ARM64 binary
from pinned upstream commit `46cd71ade6f630f1564c83bf1763f9d949a9ff30`.
The script selects Go 1.27.2 from `.go-version`, fixes the target and build flags,
and excludes Git checkout metadata from the executable. It updates `mapd.sha256`
alongside the binary after a successful build.

The installer and mapd manager verify this production checksum before recording
`v1.12.0-slc.1` as installed. A missing, corrupted, or unpatched binary is rejected
with a restore/rebuild instruction. No upstream binary is downloaded, including
when the stored version is missing or outdated. The checksum is shipped beside
the executable so this also works when test files are omitted from a release.
