"""Regression for curvature endpoints missing ahead on sparse OSM ways."""
import pytest

from openpilot.sunnypilot.mapd.live_map_data.corridor import closest_progress, polyline_length, road_geometry_window


def test_sparse_road_keeps_forward_nodes_removed_by_curvature_smoothing():
  points = [[49.103, 8.47], [49.104, 8.47], [49.1044761, 8.4705139], [49.1048576, 8.4707902],
            [49.1051843, 8.4708363], [49.1058722, 8.4709448], [49.107, 8.4711], [49.11, 8.4714]]
  position, heading = [49.1065587, 8.471048], 6.57
  # Native curvature smoothing emits only these four interior nodes.
  old = points[2:-2]
  progress, lateral = closest_progress(old, position, heading=heading)
  assert lateral > 70
  assert progress == pytest.approx(polyline_length(old), abs=.1)

  geometry = road_geometry_window(points, position, heading)
  progress, lateral = closest_progress(geometry, position, heading=heading)
  assert lateral < 2
  assert polyline_length(geometry) - progress > 380
  assert geometry[-1] == pytest.approx(points[-1], abs=1e-6)


def test_window_locates_vehicle_before_truncating_long_way():
  points = [[i * .00001, 0] for i in range(2000)]
  position = [.018, 0]
  geometry = road_geometry_window(points, position, 0)
  progress, lateral = closest_progress(geometry, position, heading=0)
  assert len(geometry) <= 256
  assert lateral == pytest.approx(0)
  assert progress == pytest.approx(50, abs=.1)
  assert polyline_length(geometry) > progress + 140


def test_geometry_window_does_not_invent_a_forward_extension():
  points = [[0, 0], [.001, 0], [.002, 0]]
  assert road_geometry_window(points, [.003, 0], 0)[-1] == points[-1]
