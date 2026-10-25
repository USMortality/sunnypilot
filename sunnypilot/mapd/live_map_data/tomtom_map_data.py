import concurrent.futures
import json
import math
import os
import threading
import time
import uuid

import requests

from openpilot.sunnypilot.mapd.live_map_data.corridor import Corridor, closest_progress, distance_m, fingerprint, polyline_length
from openpilot.sunnypilot.mapd.live_map_data.tomtom_cache import TomTomCache

ENDPOINT = "https://api.tomtom.com/snapToRoads/1"
FIELDS = "{projectedPoints{geometry{coordinates},properties{snapResult}},route{geometry{coordinates},properties{id,speedLimits{value,unit,type},traveledDistance{value,unit},formOfWay,confidence}}}"


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
    self.lock = threading.Lock()
    self.result = None
    self.result_key = None
    self.retry_after = 0.0
    self.failures = 0

  def update(self, raw_corridor, position, heading=None, now=None):
    now = time.time() if now is None else now
    try:
      corridor = Corridor.parse(raw_corridor)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
      self.result = None
      return
    key = "snap-v1:" + corridor.fingerprint
    if self.future and self.future.done():
      try:
        value = self.future.result()
      except Exception:
        value = None
      self.future = None
      if value and self._validate(value, corridor):
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
    paths = corridor.request_paths()
    if paths and self.cache.allow_and_count("snapToRoads/1", self.monthly_limit, now):
      self.future = self.executor.submit(self._fetch, key, paths[0], heading)

  def _fetch(self, key, points, heading):
    body = {"points": []}
    for i, (lat, lon) in enumerate(points):
      props = {"heading": heading} if heading is not None and i < 2 else {}
      body["points"].append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": props})
    response = self.request(ENDPOINT, params={"key": self.key, "fields": FIELDS, "vehicleType": "PassengerCar", "measurementSystem": "metric"}, json=body, timeout=(3.0, 5.0))
    response.raise_for_status()
    parsed = self._parse_response(response.json())
    parsed["reference"] = points
    cache_control = response.headers.get("Cache-Control", "")
    # No cross-drive reuse unless an affirmative max-age is returned; no-cache/no-store remain session-only.
    persistent = "max-age=" in cache_control and "no-cache" not in cache_control and "no-store" not in cache_control
    ttl = 900.0
    if persistent:
      try:
        ttl = min(86400.0, float(cache_control.split("max-age=", 1)[1].split(",", 1)[0]))
      except ValueError:
        persistent = False
    parsed["expires"] = time.time() + ttl
    self.cache.put(key, "snap-v1", parsed, "response-header:" + cache_control[:120], ttl, persistent=persistent)
    return parsed

  @staticmethod
  def _parse_response(payload):
    geometry, sections = [], []
    offset = 0.0
    for element in payload.get("route", []):
      coords = element.get("geometry", {}).get("coordinates", [])
      points = [[float(lat), float(lon)] for lon, lat in coords]
      if len(points) < 2:
        continue
      props = element.get("properties", {})
      limit = next((speed_ms(x) for x in props.get("speedLimits", []) if speed_ms(x) is not None), None)
      length = polyline_length(points)
      sections.append({"start": offset, "end": offset + length, "speed": limit, "confidence": float(props.get("confidence", 0))})
      geometry.extend(points if not geometry else points[1:])
      offset += length
    projected = payload.get("projectedPoints", [])
    projected_valid = len(projected) >= 2 and all(
      str(point.get("properties", {}).get("snapResult", "")).lower() not in ("", "offroad", "notsnapped", "failed")
      for point in projected)
    return {"geometry": geometry, "sections": sections, "projectedValid": projected_valid, "fetched": time.time()}

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
      elif section["start"] > progress and section["speed"] is not None and section["speed"] != current:
        upcoming = (section["speed"], section["start"] - progress)
        break
    return (current, *upcoming) if current is not None else None
