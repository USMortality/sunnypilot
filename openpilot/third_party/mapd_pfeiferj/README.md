# MAPD implementation by pfeiferj
https://github.com/pfeiferj/openpilot-mapd/releases/

The bundled v1.12.0 binary includes `patches/road-geometry.patch`. It publishes
`MapRoadGeometry` from the full current way and selected directed next ways,
before curvature smoothing drops the first and last two nodes. Disconnected
ways invalidate the geometry; no road is extrapolated. `MapCurvatures` and
`MapTargetVelocities` are unchanged.

Run `bash build.sh` with Go installed to test and rebuild the Linux ARM64 binary
from pinned upstream commit `46cd71ade6f630f1564c83bf1763f9d949a9ff30`.
When updating mapd, reapply the patch and rebuild instead of replacing the
bundled binary with an unpatched upstream release.
