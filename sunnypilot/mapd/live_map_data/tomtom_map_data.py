import concurrent.futures
import json
import threading
import time
import uuid

import requests

from openpilot.sunnypilot.mapd.live_map_data.corridor import Corridor, closest_progress, distance_m, fingerprint, polyline_length
from openpilot.sunnypilot.mapd.live_map_data.tomtom_cache import TomTomCache

ENDPOINT = "https://api.tomtom.com/snapToRoads/1"
FIELDS = ("{projectedPoints{geometry{coordinates},properties{snapResult}}," +
          "route{geometry{coordinates},properties{id,speedLimits{value,unit,type}," +
          "traveledDistance{value,unit},formOfWay,confidence}}}")
MAX_REQUEST_POINTS = 100


def load_api_key(path="/data/sunnypilot/provider-keys.env"):
  try:
    with open(path) as f:
      for line in f:
        name, sep, value = line.strip().partition("=")
        if sep and name.strip() == "TOMTOM_API_KEY":
          return value.strip().strip("'\"")
  except OSError:
    pass
  return ""


def speed_ms(limit):
  if limit.get("type") != "Maximum" or not limit.get("value"):
    return None
  unit = str(limit.get("unit", "")).lower()
  factor = {"kmph": 1 / 3.6, "km/h": 1 / 3.6, "kph": 1 / 3.6, "mph": 0.44704}.get(unit)
  return float(limit["value"]) * factor if factor else None


class TomTomMapData:
  def __init__(self, cache=None, request=requests.post, key_path="/data/sunnypilot/provider-keys.env", monthly_limit=75000):
    self.key = load_api_key(key_path)
    self.cache = cache or TomTomCache(session_id=uuid.uuid4().hex)
    self.request = request
    self.monthly_limit = monthly_limit  # 2,500 non-tile requests/day * 30; endpoint-specific safety guard.
    self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="tomtom-snap")
    self.future = None
    self.future_key = None
    self.lock = threading.Lock()
    self.result = None
    self.result_key = None
    self.retry_after = 0.0
    self.failures = 0

  def update(self, raw_corridor, position, heading=None, now=None):
    now = time.time() if now is None else now  # noqa: TID251 — cache/retry timestamps require wall time.
    try:
      corridor = Corridor.parse(raw_corridor)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
      self.result = None
      return
    paths = corridor.request_paths()
    # A weak match or multiple plausible continuations cannot identify a directed carriageway atomically.
    if corridor.confidence < .5 or len(paths) != 1:
      self.result = None
      return
    key = self._cache_key(paths[0])
    if self.result_key != key:
      self.result = None
      self.result_key = None
    if self.future and self.future.done():
      completed_key = self.future_key
      try:
        value = self.future.result()
      except Exception:
        value = None
      self.future = None
      self.future_key = None
      if completed_key != key:
        self.result = None
      elif value and self._validate(value, corridor):
        self.result, self.result_key, self.failures = value, key, 0
      else:
        self.result = None
        self.failures += 1
        self.retry_after = now + min(300.0, 5.0 * 2 ** min(self.failures, 6))
    if self.result_key == key and self.result:
      if self.result.get("expires", now + 1) <= now:
        self.result = None
      else:
        progress, lateral = closest_progress(self.result["geometry"], position)
        if lateral <= 20 and polyline_length(self.result["geometry"]) - progress > 120:
          return
        self.result = None
    cached = self.cache.get(key, now)
    if cached and self._validate(cached, corridor):
      self.result, self.result_key = cached, key
      return
    if not self.key or self.future or now < self.retry_after:
      return
    if self.cache.allow_and_count("snapToRoads/1", self.monthly_limit, now):
      self.future_key = key
      self.future = self.executor.submit(self._fetch, key, paths[0], heading)

  @staticmethod
  def _cache_key(points):
    return "snap-v1:" + fingerprint(points)

  @staticmethod
  def _persistent_ttl(cache_control):
    directives = {}
    for directive in cache_control.split(","):
      name, separator, value = directive.strip().partition("=")
      directives[name.lower()] = value.strip().strip('"') if separator else None
    if "max-age" not in directives or "no-cache" in directives or "no-store" in directives:
      return None
    try:
      return min(86400.0, float(directives["max-age"]))
    except (TypeError, ValueError):
      return None

  def _fetch(self, key, points, heading):
    if not 2 <= len(points) <= MAX_REQUEST_POINTS:
      raise ValueError(f"Snap to Roads requires 2..{MAX_REQUEST_POINTS} points")
    body = {"points": []}
    for i, (lat, lon) in enumerate(points):
      props = {"heading": heading} if heading is not None and i < 2 else {}
      body["points"].append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": props})
    response = self.request(ENDPOINT,
                            params={"key": self.key, "fields": FIELDS, "vehicleType": "PassengerCar", "measurementSystem": "metric"},
                            json=body, timeout=(3.0, 5.0))
    response.raise_for_status()
    parsed = self._parse_response(response.json(), len(points))
    parsed["reference"] = points
    cache_control = response.headers.get("Cache-Control", "")
    # No cross-drive reuse unless an affirmative max-age is returned; no-cache/no-store remain session-only.
    persistent_ttl = self._persistent_ttl(cache_control)
    persistent = persistent_ttl is not None
    ttl = persistent_ttl if persistent else 900.0
    parsed["expires"] = time.time() + ttl  # noqa: TID251 — persisted expiry requires wall time.
    self.cache.put(key, "snap-v1", parsed, "response-header:" + cache_control[:120], ttl, persistent=persistent)
    return parsed

  @staticmethod
  def _parse_response(payload, expected_projected_points):
    geometry, sections = [], []
    offset = 0.0
    for element in payload.get("route", []):
      coords = element.get("geometry", {}).get("coordinates", [])
      points = [[float(lat), float(lon)] for lon, lat in coords]
      if len(points) < 2:
        continue
      props = element.get("properties", {})
      speed_limit = props.get("speedLimits")
      limit = speed_ms(speed_limit) if isinstance(speed_limit, dict) else None
      length = polyline_length(points)
      sections.append({"start": offset, "end": offset + length, "speed": limit, "confidence": float(props.get("confidence", 0))})
      geometry.extend(points if not geometry else points[1:])
      offset += length
    projected = payload.get("projectedPoints", [])
    projected_valid = expected_projected_points >= 2 and len(projected) == expected_projected_points and all(
      str(point.get("properties", {}).get("snapResult", "")).lower() == "matched"
      for point in projected)
    return {"geometry": geometry, "sections": sections, "projectedValid": projected_valid,
            "fetched": time.time()}  # noqa: TID251 — provenance records wall time.

  @staticmethod
  def _validate(result, corridor):
    points = result.get("geometry", [])
    sections = result.get("sections", [])
    if len(points) < 2 or not sections or polyline_length(points) < 300:
      return False
    if "projectedValid" in result and not result["projectedValid"]:
      return False
    reference = result.get("reference", corridor.geometry)
    # Direction, start/end coverage, detour, and carriageway alignment all fail closed.
    if distance_m(points[0], reference[0]) > 40 or distance_m(points[-1], reference[-1]) > 120:
      return False
    if polyline_length(points) > polyline_length(reference) * 1.35 + 100:
      return False
    for sample in reference[::max(1, len(reference) // 10)]:
      if closest_progress(points, sample)[1] > 25:
        return False
    return min((s["confidence"] for s in sections), default=0) >= .5

  def limits(self, position):
    if not self.result:
      return None
    progress, lateral = closest_progress(self.result["geometry"], position)
    if lateral > 20:
      return None
    current, upcoming = None, (0.0, 0.0)
    for section in self.result["sections"]:
      if section["start"] <= progress <= section["end"]:
        current = section["speed"]
      elif section["start"] > progress:
        if section["speed"] is None:
          return None
        if section["speed"] != current:
          upcoming = (section["speed"], section["start"] - progress)
          break
    return (current, *upcoming) if current is not None else None
