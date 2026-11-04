import pytest

from openpilot.sunnypilot.mapd.live_map_data.corridor import distance_m, geometry_between


def test_section_geometry_preserves_road_bends_and_interpolates_boundaries():
  points = [[49., 8.], [49.001, 8.], [49.001, 8.002]]
  first, second = distance_m(*points[:2]), distance_m(*points[1:])
  section = geometry_between(points, first / 2, first + second / 2)
  assert section[0] == pytest.approx([49.0005, 8.])
  assert section[1] == points[1]
  assert section[2] == pytest.approx([49.001, 8.001])


def test_sections_clip_at_road_ends_and_do_not_bridge_unknown_gaps():
  points = [[49., 8.], [49.001, 8.]]
  assert geometry_between(points, -10, 1000) == points
  assert geometry_between(points, 80, 40) == []
  assert geometry_between(points, 1000, 2000) == []
  assert geometry_between([], 0, 10) == []
