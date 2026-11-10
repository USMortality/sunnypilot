"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import json
import math
import platform

from openpilot.cereal import log
from openpilot.common.params import Params
from openpilot.sunnypilot.mapd.live_map_data.base_map_data import BaseMapData
from openpilot.sunnypilot.mapd.live_map_data.corridor import (
  MAX_POSITION_DISTANCE_M, closest_progress, first_reversal_progress, road_geometry_window,
)
from openpilot.sunnypilot.navd.helpers import Coordinate
from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit.decision_log import SpeedLimitDecisionLogger, kph


class OsmMapData(BaseMapData):
  def __init__(self):
    super().__init__()
    self.mem_params = Params("/dev/shm/params") if platform.system() != "Darwin" else self.params
    self.native_geometry = []
    self.decision_logger = SpeedLimitDecisionLogger()

  def _log_observation(self, message) -> None:
    logger = getattr(self, "decision_logger", None)
    if logger is None:
      return

    def key():
      return (message.logMonoTime, message.valid, message.liveMapDataSP.speedLimitValid,
              kph(message.liveMapDataSP.speedLimit), message.liveMapDataSP.speedLimitAheadValid,
              kph(message.liveMapDataSP.speedLimitAhead), message.liveMapDataSP.roadName)
    logger.log("slc_observation", key, lambda: self._observation_snapshot(message))

  def _observation_snapshot(self, message):
    data = message.liveMapDataSP
    context = {
      "map_message_mono_time_ns": message.logMonoTime,
      "provider": "osm",
      "requested_provider": "osm",
      "message_valid": message.valid,
      "localizer_valid": self.localizer_valid,
      "position": {"latitude": self.last_position.latitude, "longitude": self.last_position.longitude} if self.last_position is not None else None,
      "heading_deg": self.last_bearing,
      "native_direction_valid": self._native_direction_valid(),
      "road_name": data.roadName,
      "current_kph": kph(data.speedLimit),
      "current_valid": data.speedLimitValid,
      "current_unlimited": bool(getattr(data, "speedLimitUnlimited", False)),
      "upcoming_kph": kph(data.speedLimitAhead),
      "upcoming_valid": data.speedLimitAheadValid,
      "upcoming_unlimited": bool(getattr(data, "speedLimitAheadUnlimited", False)),
      "upcoming_distance_m": data.speedLimitAheadDistance,
    }
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

    # A nearby opposite carriageway must not become the selected OSM limit.
    self.native_geometry = []
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
    except (OSError, ValueError, KeyError, TypeError):
      pass

  def _native_direction_valid(self):
    if not self.native_geometry or self.last_position is None or self.last_bearing is None:
      return False
    _, lateral = closest_progress(self.native_geometry, [self.last_position.latitude, self.last_position.longitude], heading=self.last_bearing)
    return lateral <= MAX_POSITION_DISTANCE_M

  def get_current_speed_limit(self) -> float:
    return float(self.mem_params.get("MapSpeedLimit") or 0.0) if self._native_direction_valid() else 0.0

  def get_current_road_name(self) -> str:
    return str(self.mem_params.get("RoadName") or "")

  def get_next_speed_limit_and_distance(self) -> tuple[float, float]:
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
