import hashlib
import json
import math
from dataclasses import dataclass

EARTH_RADIUS_M = 6371000.0


def distance_m(a, b):
  lat1, lat2 = math.radians(a[0]), math.radians(b[0])
  dlat, dlon = lat2 - lat1, math.radians(b[1] - a[1])
  h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
  return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def polyline_length(points):
  return sum(distance_m(a, b) for a, b in zip(points, points[1:], strict=False))


def normalized_geometry(points):
  return [[round(float(p[0]), 6), round(float(p[1]), 6)] for p in points]


def fingerprint(points, forward=True):
  directed = normalized_geometry(points if forward else list(reversed(points)))
  canonical = ";".join(f"{lat:.6f},{lon:.6f}" for lat, lon in directed)
  return hashlib.sha256(canonical.encode()).hexdigest()


def closest_progress(points, position):
  """Return along-line progress and lateral distance using a local equirectangular projection."""
  if len(points) < 2:
    return 0.0, math.inf
  lat0 = math.radians(position[0])
  scale_x = EARTH_RADIUS_M * math.cos(lat0) * math.pi / 180
  scale_y = EARTH_RADIUS_M * math.pi / 180
  px, py = (position[1] - points[0][1]) * scale_x, (position[0] - points[0][0]) * scale_y
  best_dist, best_progress, walked = math.inf, 0.0, 0.0
  for a, b in zip(points, points[1:], strict=False):
    ax, ay = (a[1] - points[0][1]) * scale_x, (a[0] - points[0][0]) * scale_y
    bx, by = (b[1] - points[0][1]) * scale_x, (b[0] - points[0][0]) * scale_y
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2)) if seg2 else 0.0
    d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
    seg = math.sqrt(seg2)
    if d < best_dist:
      best_dist, best_progress = d, walked + t * seg
    walked += seg
  return best_progress, best_dist


@dataclass(frozen=True)
class Corridor:
  fingerprint: str
  geometry: list
  progress_m: float
  confidence: float
  continuations: list

  @classmethod
  def parse(cls, raw):
    data = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
    points = data["geometry"]
    if data.get("version") != 1 or not (2 <= len(points) <= 256):
      raise ValueError("invalid corridor")
    points = normalized_geometry(points)
    expected = fingerprint(points, True)
    if data.get("fingerprint") != expected:
      raise ValueError("corridor fingerprint mismatch")
    continuations = data.get("continuations", [])[:3]
    return cls(expected, points, max(0.0, float(data.get("progressM", 0))),
               float(data.get("confidence", 0)), continuations)

  def request_paths(self, minimum_m=500.0, maximum_m=1000.0, maximum_points=100):
    base = self.geometry
    paths = []
    for branch in self.continuations:
      pts = normalized_geometry(branch.get("geometry", []))
      if len(pts) >= 2 and distance_m(base[-1], pts[0]) <= 30:
        paths.append(base + pts[1:])
    if not paths:
      paths.append(base)
    answer = []
    for path in paths[:4]:
      # Keep the tail around the vehicle and a bounded look-ahead.
      start = max(0.0, self.progress_m - 50.0)
      walked, selected = 0.0, []
      for a, b in zip(path, path[1:], strict=False):
        seg = distance_m(a, b)
        if walked + seg >= start and walked <= self.progress_m + maximum_m:
          if not selected:
            selected.append(a)
          selected.append(b)
        walked += seg
      if len(selected) >= 2 and polyline_length(selected) >= minimum_m * .7:
        if len(selected) > maximum_points:
          # Snap to Roads accepts at most 100 points. Preserve the complete
          # request extent while sampling dense corridor geometry uniformly.
          last = len(selected) - 1
          selected = [selected[round(i * last / (maximum_points - 1))] for i in range(maximum_points)]
        answer.append(selected)
    return answer
