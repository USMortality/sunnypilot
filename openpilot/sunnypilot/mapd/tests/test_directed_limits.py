"""Offline direction regressions for native OSM speed-limit data."""
import math
from unittest.mock import Mock

import pytest

from openpilot.sunnypilot.mapd.live_map_data.corridor import closest_progress, first_reversal_progress
from openpilot.sunnypilot.mapd.live_map_data.osm_map_data import OsmMapData
from openpilot.sunnypilot.navd.helpers import Coordinate


def test_heading_disambiguates_overlapping_opposite_carriageways():
  geometry = [[0, 0], [.005, 0], [.005, .0001], [0, .0001]]
  # GPS is nearer the opposite carriageway, but the vehicle is travelling north.
  position = [.002, .00008]
  assert closest_progress(geometry, position)[0] > 550
  assert closest_progress(geometry, position, heading=0)[0] < 230
  assert math.isinf(closest_progress([[.005, 0], [0, 0]], position, heading=0)[1])


def test_smooth_roundabout_is_not_an_abrupt_reversal():
  points = [[.001 * math.sin(i * math.pi / 12), .001 * math.cos(i * math.pi / 12)] for i in range(25)]
  assert math.isinf(first_reversal_progress(points))


def native_map(geometry, current=70 / 3.6, boundary=None):
  osm = OsmMapData.__new__(OsmMapData)
  osm.native_geometry = geometry
  osm.last_position = Coordinate(.002, 0)
  osm.last_bearing = 0.0
  osm.mem_params = Mock()
  osm.mem_params.get.side_effect = lambda key: {'MapSpeedLimit': current, 'NextMapSpeedLimit': boundary}.get(key)
  return osm


def test_native_opposite_direction_cannot_supply_current_or_upcoming():
  osm = native_map([[.004, .00005], [0, .00005]], boundary={'speedlimit': 100 / 3.6, 'latitude': .003, 'longitude': .00005})
  assert osm.get_current_speed_limit() == 0
  assert osm.get_next_speed_limit_and_distance() == (0, 0)


def test_native_boundary_behind_vehicle_is_not_upcoming():
  osm = native_map([[0, 0], [.005, 0]], boundary={'speedlimit': 50 / 3.6, 'latitude': .001, 'longitude': 0})
  assert osm.get_current_speed_limit() == pytest.approx(70 / 3.6)
  assert osm.get_next_speed_limit_and_distance() == (0, 0)


def test_native_forward_boundary_uses_along_route_distance():
  osm = native_map([[0, 0], [.005, 0]], boundary={'speedlimit': 50 / 3.6, 'latitude': .003, 'longitude': 0})
  limit, distance = osm.get_next_speed_limit_and_distance()
  assert limit == pytest.approx(50 / 3.6)
  assert distance == pytest.approx(111.2, abs=.2)
