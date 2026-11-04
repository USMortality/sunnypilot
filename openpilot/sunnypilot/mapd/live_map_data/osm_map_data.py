"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import json
import math
import platform
import time

from openpilot.cereal import log
from openpilot.common.params import Params
from openpilot.sunnypilot.mapd.live_map_data.base_map_data import BaseMapData
from openpilot.sunnypilot.mapd.live_map_data.corridor import (
  MAX_POSITION_DISTANCE_M, closest_progress, first_reversal_progress, geometry_between, point_at_progress, polyline_length, road_geometry_window,
)
from openpilot.sunnypilot.navd.helpers import Coordinate
from openpilot.sunnypilot.mapd.live_map_data.tomtom_map_data import TARGET_AHEAD_DISTANCE_M, REFRESH_REMAINING_DISTANCE_M
from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit.decision_log import SpeedLimitDecisionLogger, kph


class OsmMapData(BaseMapData):
  def __init__(self, speed_limit_provider=None, osm_fallback_enabled=True):
    super().__init__()
    self.mem_params = Params("/dev/shm/params") if platform.system() != "Darwin" else self.params
    self.speed_limit_provider = speed_limit_provider
    self.provider_limits = None
    self.osm_fallback_enabled = osm_fallback_enabled
    self.last_tomtom_kph = None
    self.last_tomtom_seen_unix_s = None
    self.native_geometry = []
    self.decision_logger = SpeedLimitDecisionLogger()

  def _log_observation(self, message) -> None:
    logger = getattr(self, "decision_logger", None)
    if logger is None:
      return

    def key():
      return (message.logMonoTime, self.provider_limits is not None, message.valid, message.liveMapDataSP.speedLimitValid,
              kph(message.liveMapDataSP.speedLimit), message.liveMapDataSP.speedLimitAheadValid,
              kph(message.liveMapDataSP.speedLimitAhead), message.liveMapDataSP.roadName,
              self.speed_limit_provider.result_key if self.speed_limit_provider is not None else None,
              self.speed_limit_provider.status_reason if self.speed_limit_provider is not None else "osm_selected")
    logger.log("slc_observation", key, lambda: self._observation_snapshot(message))

  def _observation_snapshot(self, message):
    data = message.liveMapDataSP
    provider = self.speed_limit_provider
    result = provider.result if provider is not None else None

    def section_snapshot(section):
      position = point_at_progress(result["geometry"], section["start"])
      return {
        "start_m": section["start"], "end_m": section["end"], "limit_kph": kph(section["speed"]) if section["speed"] is not None else None,
        "confidence": section["confidence"], "road_id": section.get("road_id"),
        "start_position": {"latitude": position[0], "longitude": position[1]},
        "geometry": geometry_between(result["geometry"], section["start"], section["end"]),
      }
    context = {
      "map_message_mono_time_ns": message.logMonoTime,
      "provider": "tomtom" if self.provider_limits is not None else "none" if self._tomtom_only() else "osm",
      "requested_provider": "tomtom" if provider is not None else "osm",
      "osm_fallback_enabled": getattr(self, "osm_fallback_enabled", True),
      "last_tomtom_kph": getattr(self, "last_tomtom_kph", None),
      "last_tomtom_seen_unix_s": getattr(self, "last_tomtom_seen_unix_s", None),
      "message_valid": message.valid,
      "localizer_valid": self.localizer_valid,
      "position": {"latitude": self.last_position.latitude, "longitude": self.last_position.longitude} if self.last_position is not None else None,
      "heading_deg": self.last_bearing,
      "native_direction_valid": self._native_direction_valid(),
      "road_name": data.roadName,
      "current_kph": kph(data.speedLimit),
      "current_valid": data.speedLimitValid,
      "upcoming_kph": kph(data.speedLimitAhead),
      "upcoming_valid": data.speedLimitAheadValid,
      "upcoming_distance_m": data.speedLimitAheadDistance,
      "tomtom_status": provider.status_reason if provider is not None else "not_configured",
      "tomtom_validation": provider.validation_reason if provider is not None else None,
      "tomtom_last_failure": provider.last_failure_reason if provider is not None else None,
      "tomtom_failures": provider.failures if provider is not None else 0,
    }
    if result is not None and self.provider_limits is not None:
      position = [self.last_position.latitude, self.last_position.longitude]
      progress, _ = closest_progress(result["geometry"], position, heading=self.last_bearing)
      native_progress, _ = closest_progress(self.native_geometry, position, heading=self.last_bearing)
      context.update({
        "tomtom_target_ahead_m": TARGET_AHEAD_DISTANCE_M,
        "tomtom_refresh_threshold_m": REFRESH_REMAINING_DISTANCE_M,
        "tomtom_response_ahead_m": max(0., polyline_length(result["geometry"]) - progress),
        "native_corridor_ahead_m": max(0., polyline_length(self.native_geometry) - native_progress),
        "cache_key": provider.result_key,
        "fetched_age_s": time.time() - result["fetched"],  # noqa: TID251 — persisted cache provenance uses wall time.
        "response_expires_at_unix_s": result.get("expires"),
        "route_length_m": sum(s["end"] - s["start"] for s in result["sections"]),
        "section_count": len(result["sections"]),
        "sections": [section_snapshot(s) for s in result["sections"][:64]],
      })
    else:
      native_ahead = self.mem_params.get("NextMapSpeedLimit")
      if isinstance(native_ahead, dict) and native_ahead.get("speedlimit", 0) > 0:
        context["upcoming_position"] = {"latitude": native_ahead.get("latitude"), "longitude": native_ahead.get("longitude")}
    return context

  def update_location(self) -> None:
    location = self.sm['liveLocationKalman']
    self.localizer_valid = (location.status == log.LiveLocationKalman.Status.valid) and location.positionGeodetic.valid

    if self.localizer_valid:
      self.last_bearing = math.degrees(location.calibratedOrientationNED.value[2]) % 360.0
      self.last_position = Coordinate(location.positionGeodetic.value[0], location.positionGeodetic.value[1])

    if self.last_position is None:
      return

    params = {
      "latitude": self.last_position.latitude,
      "longitude": self.last_position.longitude,
    }

    if self.last_bearing is not None:
      params['bearing'] = self.last_bearing

    # mapd reads its position from the memory params as JSON, so write it for the mapd binary.
    # LastGPSPosition is registered as BYTES (ubloxd owns the persistent copy for pigeond),
    # so the JSON payload has to be encoded here.
    self.mem_params.put("LastGPSPosition", json.dumps(params).encode(), block=True)

    # Validate native fallback against the same directed geometry as TomTom.
    # A nearby opposite carriageway must not become a valid fallback limit.
    self.native_geometry = []
    corridor = ""
    try:
      # Curvature smoothing drops two nodes at each end. Use the complete
      # topology so sparse roads still cover the vehicle and the road ahead.
      # Keep compatibility with an unpatched native mapd.
      try:
        with open("/dev/shm/params/d/MapRoadGeometry") as f:
          road_points = json.load(f)
      except FileNotFoundError:
        with open("/dev/shm/params/d/MapCurvatures") as f:
          road_points = json.load(f)
      if road_points:
        geometry = [[pt["latitude"], pt["longitude"]] for pt in road_points]
        # Bound the message around the vehicle, rather than dropping the end
        # of a long way before locating the vehicle on it.
        geometry = road_geometry_window(geometry, [self.last_position.latitude, self.last_position.longitude], self.last_bearing)
        self.native_geometry = geometry
        progress, _ = closest_progress(geometry, [self.last_position.latitude, self.last_position.longitude], heading=self.last_bearing)
        corridor = json.dumps({"geometry": geometry, "progressM": progress, "confidence": 1.0})
    except (OSError, ValueError, KeyError, TypeError):
      pass
    if self.speed_limit_provider is not None:
      self.speed_limit_provider.update(corridor, [self.last_position.latitude, self.last_position.longitude], self.last_bearing)
      self.provider_limits = self.speed_limit_provider.limits([self.last_position.latitude, self.last_position.longitude])
      provider = self.speed_limit_provider
      if provider.debug_logging:
        provider._debug_write("/tmp/tomtom_debug", (f"corridor_len: {len(corridor)}\nresult: {provider.result is not None}\n" +
                              f"result_key: {provider.result_key}\nfuture: {provider.future is not None}\nfuture_key: {provider.future_key}\n" +
                              f"retry_after: {provider.retry_after}\nfailures: {provider.failures}\nlimits: {self.provider_limits}\n"))

  def _native_direction_valid(self):
    if not self.native_geometry or self.last_position is None or self.last_bearing is None:
      return False
    _, lateral = closest_progress(self.native_geometry, [self.last_position.latitude, self.last_position.longitude], heading=self.last_bearing)
    return lateral <= MAX_POSITION_DISTANCE_M

  def _tomtom_only(self):
    return self.speed_limit_provider is not None and not getattr(self, "osm_fallback_enabled", True)

  def get_current_speed_limit(self) -> float:
    if self.provider_limits is not None:
      if getattr(self, "localizer_valid", False) and self.sm['liveLocationKalman'].gpsOK:
        self.last_tomtom_kph = kph(self.provider_limits[0])
        self.last_tomtom_seen_unix_s = time.time()  # noqa: TID251 — retained provider provenance across telemetry hosts.
      # Runtime source status consumed by the UI indicator, independent of diagnostic logging.
      try:
        with open("/tmp/tomtom_active", "w") as f:
          f.write(f"TomTom: {self.provider_limits[0]:.1f} m/s\n")
      except OSError:
        pass
      return self.provider_limits[0]
    if self._tomtom_only():
      try:
        with open("/tmp/tomtom_active", "w") as f:
          f.write("TomTom retained" if getattr(self, "last_tomtom_kph", None) is not None else "TomTom unavailable")
      except OSError:
        pass
      # Do not invent a current limit. The SLC resolver already retains its
      # previous target when a fresh map candidate is unavailable.
      return 0.0
    # Using OSM fallback
    try:
      with open("/tmp/tomtom_active", "w") as f:
        f.write("OSM fallback\n")
    except OSError:
      pass
    return float(self.mem_params.get("MapSpeedLimit") or 0.0) if self._native_direction_valid() else 0.0

  def get_current_road_name(self) -> str:
    return str(self.mem_params.get("RoadName") or "")

  def get_next_speed_limit_and_distance(self) -> tuple[float, float]:
    if self.provider_limits is not None:
      return self.provider_limits[1], self.provider_limits[2]
    if self._tomtom_only():
      return 0.0, 0.0
    if not self._native_direction_valid():
      return 0.0, 0.0
    next_speed_limit_section_str = self.mem_params.get("NextMapSpeedLimit")
    next_speed_limit_section = next_speed_limit_section_str if next_speed_limit_section_str else {}
    next_speed_limit = next_speed_limit_section.get('speedlimit', 0.0)
    next_speed_limit_latitude = next_speed_limit_section.get('latitude')
    next_speed_limit_longitude = next_speed_limit_section.get('longitude')
    next_speed_limit_distance = 0.0

    if next_speed_limit_latitude is not None and next_speed_limit_longitude is not None:
      position = [self.last_position.latitude, self.last_position.longitude]
      progress, _ = closest_progress(self.native_geometry, position, heading=self.last_bearing)
      boundary, lateral = closest_progress(self.native_geometry, [next_speed_limit_latitude, next_speed_limit_longitude],
                                           minimum_progress=progress)
      if lateral > MAX_POSITION_DISTANCE_M or boundary <= progress or boundary >= first_reversal_progress(self.native_geometry, progress):
        return 0.0, 0.0
      next_speed_limit_distance = boundary - progress
    else:
      return 0.0, 0.0

    return next_speed_limit, next_speed_limit_distance
