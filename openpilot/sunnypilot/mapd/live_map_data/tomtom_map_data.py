import concurrent.futures
import json
import math
import re
import socket
import ssl
import time
import traceback
import uuid
from urllib.parse import quote

import requests

from openpilot.sunnypilot.mapd.live_map_data.corridor import (
  MAX_POSITION_DISTANCE_M, Corridor, closest_progress, distance_m, fingerprint, first_reversal_progress, point_at_progress, polyline_length,
)
from openpilot.sunnypilot.mapd.live_map_data.tomtom_cache import TomTomCache

ENDPOINT = "https://api.tomtom.com/snapToRoads/1"
FIELDS = ("{projectedPoints{geometry{coordinates},properties{snapResult}}," +
          "route{geometry{coordinates},properties{id,speedLimits{value,unit,type}," +
          "traveledDistance{value,unit},formOfWay,confidence}}}")
MIN_MATCH_CONFIDENCE = .5
MIN_ROUTE_LENGTH_M = 100.0
TARGET_AHEAD_DISTANCE_M = 500.0
REFRESH_BUFFER_DISTANCE_M = 200.0
REFRESH_REMAINING_DISTANCE_M = TARGET_AHEAD_DISTANCE_M + REFRESH_BUFFER_DISTANCE_M
MIN_REFRESH_EXTENSION_M = 100.0
MAX_ROUTE_DEVIATION_M = 25.0
ROUTE_SAMPLE_SPACING_M = 25.0
MIN_PROGRESS_COVERAGE = .65
PROGRESS_BACKTRACK_TOLERANCE_M = 2.0
START_COVERAGE_TOLERANCE_M = 40.0
END_COVERAGE_TOLERANCE_M = 120.0
MAX_DETOUR_RATIO = 1.35
MAX_DETOUR_EXTRA_M = 100.0
CACHE_TTL_S = 30 * 86400.0
MAX_SHORT_INCREASE_M = 75.0


def internet_available():
  """Verify TomTom is reachable over trusted TLS without sending an API request."""
  try:
    context = ssl.create_default_context()
    with socket.create_connection(("api.tomtom.com", 443), timeout=2.0) as connection:
      with context.wrap_socket(connection, server_hostname="api.tomtom.com"):
        return True
  except OSError:
    return False


class RequestBudgetExhausted(Exception):
  pass


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
  """Publishing-thread state; the worker only fetches results and writes the locked cache."""

  def __init__(self, cache=None, request=requests.post, key_path="/data/sunnypilot/provider-keys.env", monthly_limit=75000,
               internet_check=internet_available, debug_logging=False):
    self.key = load_api_key(key_path)
    self.cache = cache or TomTomCache(session_id=uuid.uuid4().hex, max_entries=2048)
    self.request = request
    self.internet_check = internet_check
    self.monthly_limit = monthly_limit  # Local calendar-month guard, independent of the account's entitlement.
    self.debug_logging = debug_logging
    self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="tomtom-snap")
    self.future = None
    self.future_key = None
    self.result = None
    self.heading = None
    self.result_key = None
    self.retry_after = 0.0
    self.failures = 0
    self.status_reason = "not_initialized"
    self.validation_reason = None
    self.last_failure_reason = None
    self.current_unlimited = False
    self.ahead_unlimited = False

  def update(self, raw_corridor, position, heading=None, now=None):
    self.heading = heading if heading is not None and math.isfinite(heading) else None
    now = time.time() if now is None else now  # noqa: TID251 — cache/retry timestamps require wall time.
    try:
      corridor = Corridor.parse(raw_corridor)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
      self.result = None
      self.status_reason = "invalid_corridor"
      return
    # A short directed path can still validate a cached current limit. The
    # minimum query length applies only to new API requests, not cache reuse.
    paths = corridor.request_paths(minimum_m=0.)
    fetch_paths = corridor.request_paths()
    self._debug_write("/tmp/tomtom_corridor", f"confidence: {corridor.confidence}\npaths: {len(paths)}\ngeometry_len: {len(corridor.geometry)}\n")
    # A weak match or multiple plausible continuations cannot identify a directed carriageway atomically.
    if corridor.confidence < MIN_MATCH_CONFIDENCE or len(paths) != 1:
      self.result = None
      self.status_reason = ("low_corridor_confidence" if corridor.confidence < MIN_MATCH_CONFIDENCE else
                            "insufficient_corridor" if not paths else "ambiguous_corridor")
      return
    key = self._cache_key(paths[0])
    if self.future and self.future.done():
      completed_key = self.future_key
      network_error = False
      budget_exhausted = False
      try:
        value = self.future.result()
      except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # Network errors (DNS, connectivity) - don't count as failure, retry soon
        value = None
        network_error = True
      except RequestBudgetExhausted:
        value = None
        budget_exhausted = True
      except Exception as e:
        value = None
        self._debug_write("/tmp/tomtom_future_exc", f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
      self.future = None
      self.future_key = None
      if network_error:
        # Poll for reconnection without spending quota or increasing failure backoff.
        self.retry_after = now + 5.0
        self.last_failure_reason = "network_unavailable_or_timeout"
      elif budget_exhausted:
        self.retry_after = now + 300.0
        self.last_failure_reason = "monthly_budget_exhausted"
      elif value and self._usable(value, corridor, paths[0], position, now):
        self.result, self.result_key, self.failures = value, completed_key, 0
        self.retry_after = 0.0
        self.last_failure_reason = None
      elif completed_key != key:
        # A completed request for a previous road must not delay fetching the new road.
        pass
      else:
        # A failed refill must not discard an older response that still passes
        # the current position/direction checks below.
        self.failures += 1
        self.retry_after = now + min(300.0, 5.0 * 2 ** min(self.failures, 6))
        self.last_failure_reason = "response_rejected" if value else "request_failed"
    if self.result and self._usable(self.result, corridor, paths[0], position, now):
      self.status_reason = "active_result"
      # Start replenishing before the desired 500 m horizon is exhausted.
      # A moving GPS/window key alone must not cause repeated overlapping calls.
      if not fetch_paths or key == self.result_key or not self._refresh_extends_coverage(paths[0], position):
        return
    else:
      self.result = None
      self.result_key = None
    cached = self.cache.get(key, now)
    if cached and self._usable(cached, corridor, paths[0], position, now):
      self.result, self.result_key = cached, key
      self.status_reason = "cache_hit"
      return
    if not fetch_paths:
      self.status_reason = "insufficient_corridor"
      return
    if not self.key or self.future or now < self.retry_after:
      self.status_reason = "missing_api_key" if not self.key else "fetch_pending" if self.future else "retry_backoff"
      return
    self.future_key = key
    self.future = self.executor.submit(self._fetch, key, paths[0], heading)
    self.status_reason = "fetch_pending"

  def _refresh_extends_coverage(self, path, position):
    geometry = self.result["geometry"]
    progress, _ = closest_progress(geometry, position, heading=self.heading)
    if polyline_length(geometry) - progress > REFRESH_REMAINING_DISTANCE_M:
      return False
    # Only fetch if native mapd now supplies a useful extension beyond the old
    # response. Short or jittering corridors cannot replenish a 500 m horizon.
    path_progress, _ = closest_progress(path, position, heading=self.heading)
    end_progress, lateral = closest_progress(path, geometry[-1], minimum_progress=path_progress)
    return lateral <= MAX_ROUTE_DEVIATION_M and polyline_length(path) - end_progress >= MIN_REFRESH_EXTENSION_M

  @staticmethod
  def _cache_key(points):
    # v2 preserves advisory-only German motorway sections as unrestricted.
    return "snap-v2:" + fingerprint(points)

  def _debug_write(self, path, message, mode="w"):
    if not self.debug_logging:
      return
    # requests exceptions include the keyed URL, and error bodies may echo it.
    message = re.sub(r"(?i)([?&]key=)[^\s&\"'<>]+", r"\1[REDACTED]", message)
    if self.key:
      message = message.replace(quote(self.key, safe=""), "[REDACTED]").replace(self.key, "[REDACTED]")
    try:
      with open(path, mode) as f:
        f.write(message)
    except OSError:
      pass

  def _usable(self, result, corridor, path, position, now):
    if result.get("expires", now + 1) <= now:
      self.validation_reason = "expired_response"
      return False
    if not self._validate(result, corridor):
      return False
    geometry = result["geometry"]
    progress, lateral = closest_progress(geometry, position, heading=self.heading)
    path_progress, path_lateral = closest_progress(path, position, heading=self.heading)
    remaining = min(polyline_length(geometry) - progress, polyline_length(path) - path_progress)
    if max(lateral, path_lateral) > MAX_POSITION_DISTANCE_M or remaining <= 0.0:
      self.validation_reason = ("vehicle_off_route" if max(lateral, path_lateral) > MAX_POSITION_DISTANCE_M else "route_ended")
      return False
    # Compare the shared road ahead, rather than requiring identical moving windows.
    # Monotonic progress rejects a reversal; lateral checks reject a changed branch.
    previous = progress
    steps = int(remaining / ROUTE_SAMPLE_SPACING_M) + 1
    for i in range(1, steps + 1):
      sample = point_at_progress(path, path_progress + remaining * i / steps)
      # A route can visit the same road more than once. Match within the next
      # plausible section instead of jumping to an earlier or much later visit.
      matched, lateral = closest_progress(geometry, sample, minimum_progress=max(0.0, previous - PROGRESS_BACKTRACK_TOLERANCE_M),
                                         maximum_progress=previous + remaining / steps * MAX_DETOUR_RATIO + MAX_ROUTE_DEVIATION_M)
      if lateral > MAX_ROUTE_DEVIATION_M or matched < previous - PROGRESS_BACKTRACK_TOLERANCE_M:
        self.validation_reason = "ordered_route_alignment_failed"
        return False
      previous = matched
    usable = previous - progress >= remaining * MIN_PROGRESS_COVERAGE
    self.validation_reason = None if usable else "insufficient_progress_coverage"
    if usable:
      # Never advertise an upcoming boundary beyond the topology validated on
      # this update, even if the cached response extends through a junction.
      self._validated_horizon = previous
    return usable

  def _fetch(self, key, points, heading):
    # Keep DNS/TLS checks off the publishing thread. Wi-Fi association alone does
    # not establish internet access (for example, a hotspot with no mobile data).
    if not self.internet_check():
      raise requests.exceptions.ConnectionError("TomTom internet connection unavailable")
    if not self.cache.allow_and_count("snapToRoads/1", self.monthly_limit):
      raise RequestBudgetExhausted
    # Also protect direct API-client callers that do not use OsmMapData's GPS path.
    heading = heading % 360.0 if heading is not None and math.isfinite(heading) else None
    body = {"points": []}
    for i, (lat, lon) in enumerate(points):
      props = {"heading": heading} if heading is not None and i < 2 else {}
      body["points"].append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": props})
    try:
      response = self.request(ENDPOINT,
                              params={"key": self.key, "fields": FIELDS, "vehicleType": "PassengerCar", "measurementSystem": "metric"},
                              json=body, timeout=(3.0, 5.0))
      self._debug_write("/tmp/tomtom_fetch", f"status: {response.status_code}\npoints: {len(points)}\nbody: {response.text[:1000]}\n")
      response.raise_for_status()
    except Exception as e:
      self._debug_write("/tmp/tomtom_fetch", f"exception: {type(e).__name__}: {e}\n", mode="a")
      raise
    parsed = self._parse_response(response.json())
    parsed["reference"] = points
    # Speed limits rarely change - cache for 30 days
    parsed["expires"] = time.time() + CACHE_TTL_S  # noqa: TID251 — persisted expiry requires wall time.
    self.cache.put(key, "snap-v2", parsed, "30d-cache", CACHE_TTL_S, persistent=True)
    if self.debug_logging:
      summary = (f"geometry: {len(parsed.get('geometry', []))}\nsections: {len(parsed.get('sections', []))}\n" +
                 f"projectedValid: {parsed.get('projectedValid')}\n")
      for s in parsed.get('sections', [])[:3]:
        summary += f"  section: speed={s.get('speed')}, conf={s.get('confidence')}\n"
      self._debug_write("/tmp/tomtom_parsed", summary)
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
      limits = props.get("speedLimits") or []
      if isinstance(limits, dict):
        limits = [limits]
      limit = next((speed for item in limits if (speed := speed_ms(item)) is not None), None)
      # A 130 km/h advisory without a maximum is the unrestricted motorway
      # case. Keep the sign separate from the requested advisory target.
      unlimited = limit is None and any(item.get("type") == "Recommended" and
                                       math.isclose(speed_ms({**item, "type": "Maximum"}) or 0., 130. / 3.6, abs_tol=.01) for item in limits)
      if unlimited:
        limit = 130. / 3.6
      length = polyline_length(points)
      sections.append({"start": offset, "end": offset + length, "speed": limit, "confidence": float(props.get("confidence", 0)),
                       "road_id": props.get("id"), "unlimited": unlimited})
      geometry.extend(points if not geometry else points[1:])
      offset += length
    projected = payload.get("projectedPoints", [])
    projected_valid = len(projected) >= 2 and all(
      str(point.get("properties", {}).get("snapResult", "")).lower() == "matched"
      for point in projected)
    return {"geometry": geometry, "sections": sections, "projectedValid": projected_valid,
            "fetched": time.time()}  # noqa: TID251 — provenance records wall time.

  def _validate(self, result, corridor):
    points = result.get("geometry", [])
    sections = result.get("sections", [])
    reason = None
    if len(points) < 2 or not sections or polyline_length(points) < MIN_ROUTE_LENGTH_M:
      reason = f"basic: pts={len(points)}, sections={len(sections)}, len={polyline_length(points) if len(points) >= 2 else 0:.0f}"
    elif "projectedValid" in result and not result["projectedValid"]:
      reason = "projectedValid=False"
    else:
      reference = result.get("reference", corridor.geometry)
      d_start = distance_m(points[0], reference[0])
      d_end = distance_m(points[-1], reference[-1])
      if d_start > START_COVERAGE_TOLERANCE_M or d_end > END_COVERAGE_TOLERANCE_M:
        reason = f"coverage: d_start={d_start:.0f}, d_end={d_end:.0f}"
      elif polyline_length(points) > polyline_length(reference) * MAX_DETOUR_RATIO + MAX_DETOUR_EXTRA_M:
        reason = f"detour: pts_len={polyline_length(points):.0f}, ref_len={polyline_length(reference):.0f}"
      else:
        for i, sample in enumerate(reference[::max(1, len(reference) // 10)]):
          lat_dist = closest_progress(points, sample)[1]
          if lat_dist > MAX_ROUTE_DEVIATION_M:
            reason = f"lateral: sample[{i}] lat_dist={lat_dist:.0f}"
            break
        if reason is None:
          min_conf = min((s["confidence"] for s in sections), default=0)
          if min_conf < MIN_MATCH_CONFIDENCE:
            reason = f"confidence: min={min_conf:.2f}"
    if reason:
      self.validation_reason = reason
      self._debug_write("/tmp/tomtom_validate", f"FAIL: {reason}\n")
      return False
    self.validation_reason = None
    return True

  def _limit_sections(self, horizon):
    # API road IDs split a speed zone into several elements. Judge the complete
    # run, so splitting a real longer zone cannot make it look like a spike.
    runs = []
    for section in self.result["sections"]:
      if (runs and runs[-1]["speed"] == section["speed"] and
          runs[-1].get("unlimited", False) == section.get("unlimited", False) and
          math.isclose(runs[-1]["end"], section["start"], abs_tol=.01)):
        runs[-1]["end"] = section["end"]
      else:
        runs.append(dict(section))
    filtered = [dict(run) for run in runs]
    for i in range(1, len(runs) - 1):
      before, run, after = runs[i - 1:i + 2]
      if (before["speed"] is not None and run["speed"] is not None and before["speed"] == after["speed"] and
          before.get("unlimited", False) == after.get("unlimited", False) and run["speed"] > before["speed"] and
          0. < run["end"] - run["start"] <= MAX_SHORT_INCREASE_M and run["end"] < horizon and
          math.isclose(before["end"], run["start"], abs_tol=.01) and math.isclose(run["end"], after["start"], abs_tol=.01)):
        # A short rise returning to the same lower limit is not worth an
        # acceleration/braking cycle. Raw cached provider data stays intact.
        filtered[i]["speed"] = before["speed"]
        filtered[i]["unlimited"] = before.get("unlimited", False)
    return filtered

  def limits(self, position):
    self.current_unlimited = self.ahead_unlimited = False
    if not self.result:
      return None
    progress, lateral = closest_progress(self.result["geometry"], position, heading=self.heading)
    validated_horizon = getattr(self, '_validated_horizon', math.inf)
    if lateral > MAX_POSITION_DISTANCE_M or progress >= min(polyline_length(self.result["geometry"]), validated_horizon):
      return None
    # Do not advertise limits reached only by an unobserved U-turn prediction.
    horizon = min(first_reversal_progress(self.result["geometry"], progress), validated_horizon)
    reference = self.result.get("reference", self.result["geometry"])
    reference_progress, _ = closest_progress(reference, position, heading=self.heading)
    reversal = first_reversal_progress(reference, reference_progress)
    if math.isfinite(reversal):
      matched, _ = closest_progress(self.result["geometry"], point_at_progress(reference, reversal),
                                    minimum_progress=progress, heading=self.heading)
      horizon = min(horizon, matched)
    current, upcoming = None, (0.0, 0.0)
    for section in self._limit_sections(horizon):
      if section["start"] <= progress <= section["end"]:
        current = section["speed"]
        self.current_unlimited = section.get("unlimited", False)
      elif section["start"] > progress:
        if section["start"] >= horizon:
          break
        if section["speed"] is None:
          # An unknown future section invalidates lookahead, not a known current
          # section. Never jump across the gap to advertise a later limit.
          break
        if section["speed"] != current:
          upcoming = (section["speed"], section["start"] - progress)
          self.ahead_unlimited = section.get("unlimited", False)
          break
    return (current, *upcoming) if current is not None else None
