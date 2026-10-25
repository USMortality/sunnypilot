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
from openpilot.sunnypilot.mapd.live_map_data.corridor import closest_progress, extend_geometry_to_position
from openpilot.sunnypilot.navd.helpers import Coordinate


class OsmMapData(BaseMapData):
  def __init__(self, speed_limit_provider=None):
    super().__init__()
    self.mem_params = Params("/dev/shm/params") if platform.system() != "Darwin" else self.params
    self.speed_limit_provider = speed_limit_provider
    self.provider_limits = None

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

    if self.speed_limit_provider is not None:
      # Build corridor from MapCurvatures (road geometry from native mapd)
      # Read directly from shm file to avoid param key registration issues
      try:
        with open("/dev/shm/params/d/MapCurvatures") as f:
          curvatures = json.load(f)
        if curvatures:
          geometry = [[pt["latitude"], pt["longitude"]] for pt in curvatures]
          geometry = extend_geometry_to_position(geometry, [self.last_position.latitude, self.last_position.longitude])
          progress, _ = closest_progress(geometry, [self.last_position.latitude, self.last_position.longitude])
          corridor = json.dumps({"geometry": geometry, "progressM": progress, "confidence": 1.0})
        else:
          corridor = ""
      except (OSError, json.JSONDecodeError, KeyError, TypeError):
        corridor = ""
      self.speed_limit_provider.update(corridor, [self.last_position.latitude, self.last_position.longitude], self.last_bearing)
      self.provider_limits = self.speed_limit_provider.limits([self.last_position.latitude, self.last_position.longitude])
      provider = self.speed_limit_provider
      if provider.debug_logging:
        provider._debug_write("/tmp/tomtom_debug", (f"corridor_len: {len(corridor)}\nresult: {provider.result is not None}\n" +
                              f"result_key: {provider.result_key}\nfuture: {provider.future is not None}\nfuture_key: {provider.future_key}\n" +
                              f"retry_after: {provider.retry_after}\nfailures: {provider.failures}\nlimits: {self.provider_limits}\n"))

  def get_current_speed_limit(self) -> float:
    if self.provider_limits is not None:
      # Runtime source status consumed by the UI indicator, independent of diagnostic logging.
      try:
        with open("/tmp/tomtom_active", "w") as f:
          f.write(f"TomTom: {self.provider_limits[0]:.1f} m/s\n")
      except OSError:
        pass
      return self.provider_limits[0]
    # Using OSM fallback
    try:
      with open("/tmp/tomtom_active", "w") as f:
        f.write("OSM fallback\n")
    except OSError:
      pass
    return float(self.mem_params.get("MapSpeedLimit") or 0.0)

  def get_current_road_name(self) -> str:
    return str(self.mem_params.get("RoadName") or "")

  def get_next_speed_limit_and_distance(self) -> tuple[float, float]:
    if self.provider_limits is not None:
      return self.provider_limits[1], self.provider_limits[2]
    next_speed_limit_section_str = self.mem_params.get("NextMapSpeedLimit")
    next_speed_limit_section = next_speed_limit_section_str if next_speed_limit_section_str else {}
    next_speed_limit = next_speed_limit_section.get('speedlimit', 0.0)
    next_speed_limit_latitude = next_speed_limit_section.get('latitude')
    next_speed_limit_longitude = next_speed_limit_section.get('longitude')
    next_speed_limit_distance = 0.0

    if next_speed_limit_latitude and next_speed_limit_longitude:
      next_speed_limit_coordinates = Coordinate(next_speed_limit_latitude, next_speed_limit_longitude)
      next_speed_limit_distance = (self.last_position or Coordinate(0, 0)).distance_to(next_speed_limit_coordinates)

    return next_speed_limit, next_speed_limit_distance
