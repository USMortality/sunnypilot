import pytest

from openpilot.sunnypilot.mapd.live_map_data.corridor import Corridor, closest_progress, fingerprint
from openpilot.sunnypilot.mapd.live_map_data.tomtom_cache import TomTomCache
from openpilot.sunnypilot.mapd.live_map_data.tomtom_map_data import MAX_REQUEST_POINTS, TomTomMapData, speed_ms


def line(n=8, lon=0.0):
  return [[i * .001, lon] for i in range(n)]


def corridor(points=None, continuations=None, progress=20, confidence=.9):
  points = points or line()
  return {"version": 1, "geometry": points, "progressM": progress, "confidence": confidence,
          "fingerprint": fingerprint(points), "continuations": continuations or []}


def result(points=None, speed=50, confidence=.9):
  points = points or line()
  return {"geometry": points, "sections": [
    {"start": 0, "end": 350, "speed": speed / 3.6 if speed else None, "confidence": confidence},
    {"start": 350, "end": 780, "speed": 30 / 3.6, "confidence": confidence}], "fetched": 1}


def test_fingerprint_is_directed_and_stable():
  points = line()
  assert fingerprint(points) == fingerprint([[round(x, 7), y] for x, y in points])
  assert fingerprint(points) != fingerprint(list(reversed(points)))


def test_corridor_rejects_tamper_and_bounds_forks():
  raw = corridor(continuations=[{"geometry": line(lon=i * .001)} for i in range(8)])
  assert len(Corridor.parse(raw).continuations) == 3
  raw["fingerprint"] = "wrong"
  with pytest.raises(ValueError):
    Corridor.parse(raw)


def test_adjacent_road_and_geometry_detour_rejected(tmp_path):
  adapter = TomTomMapData(cache=TomTomCache(str(tmp_path / "c"), "s"), key_path=str(tmp_path / "missing"))
  c = Corridor.parse(corridor())
  assert adapter._validate(result(), c)
  assert not adapter._validate(result(line(lon=.001)), c)
  assert not adapter._validate(result([[0, 0], [.02, .02], [.007, 0]]), c)


def test_confidence_direction_and_coverage_rejected(tmp_path):
  adapter = TomTomMapData(cache=TomTomCache(str(tmp_path / "c"), "s"), key_path=str(tmp_path / "missing"))
  c = Corridor.parse(corridor())
  assert not adapter._validate(result(list(reversed(line()))), c)
  assert not adapter._validate(result(confidence=.49), c)
  assert not adapter._validate(result(line(3)), c)


@pytest.mark.parametrize(("item", "expected"), [
  ({"value": 60, "unit": "kmph", "type": "Maximum"}, 60 / 3.6),
  ({"value": 60, "unit": "mph", "type": "Maximum"}, 60 * .44704),
  ({"value": 0, "unit": "kmph", "type": "Maximum"}, None),
  ({"value": 40, "unit": "kmph", "type": "Recommended"}, None),
])
def test_units_and_unknown_limits(item, expected):
  assert speed_ms(item) == expected


def test_transition_distance_and_unknown_current_fallback(tmp_path):
  adapter = TomTomMapData(cache=TomTomCache(str(tmp_path / "c"), "s"), key_path=str(tmp_path / "missing"))
  adapter.result = result()
  progress, _ = closest_progress(line(), [.002, 0])
  limits = adapter.limits([.002, 0])
  assert limits[0] == pytest.approx(50 / 3.6)
  assert limits[2] == pytest.approx(350 - progress, abs=2)
  adapter.result["sections"][0]["speed"] = None
  assert adapter.limits([.002, 0]) is None


def test_unknown_upcoming_section_falls_back_atomically(tmp_path):
  adapter = TomTomMapData(cache=TomTomCache(str(tmp_path / "c"), "s"), key_path=str(tmp_path / "missing"))
  adapter.result = result()
  adapter.result["sections"].insert(1, {"start": 300, "end": 350, "speed": None, "confidence": .9})
  assert adapter.limits([.002, 0]) is None


@pytest.mark.parametrize(("snap_result", "expected"), [
  ("Matched", True),
  ("matched", True),
  ("MaxDistanceExceeded", False),
  ("Snapped", False),
  ("FutureUnknownValue", False),
])
def test_only_matched_projection_is_valid(snap_result, expected):
  payload = {
    "route": [{
      "geometry": {"coordinates": [[0, 0], [0, .004]]},
      "properties": {"confidence": .9, "speedLimits": {"value": 50, "unit": "kmph", "type": "Maximum"}},
    }],
    "projectedPoints": [
      {"properties": {"snapResult": "Matched"}},
      {"properties": {"snapResult": snap_result}},
    ],
  }
  parsed = TomTomMapData._parse_response(payload, 2)
  assert parsed["projectedValid"] is expected
  assert parsed["sections"][0]["speed"] == pytest.approx(50 / 3.6)


@pytest.mark.parametrize("returned_count", [1, 3])
def test_projection_count_must_match_submitted_points(returned_count):
  payload = {
    "projectedPoints": [
      {"properties": {"snapResult": "Matched"}}
      for _ in range(returned_count)
    ],
  }
  assert not TomTomMapData._parse_response(payload, 2)["projectedValid"]


@pytest.mark.parametrize(("cache_control", "expected"), [
  ("max-age=3600", 3600),
  ("public, max-age=3600, s-maxage=7200", 3600),
  ("s-maxage=7200", None),
  ("max-age=3600, no-store", None),
])
def test_only_exact_max_age_allows_persistent_cache(cache_control, expected):
  assert TomTomMapData._persistent_ttl(cache_control) == expected


def test_cache_session_expiry_persistence_and_budget(tmp_path):
  path = str(tmp_path / "cache")
  cache = TomTomCache(path, "drive-a", max_entries=2)
  cache.put("a", "v1", {"a": 1}, "test", 10, now=1)
  assert cache.get("a", now=2) == {"a": 1}
  assert cache.get("a", now=12) is None
  assert TomTomCache(path, "drive-b").get("a", now=2) is None
  cache.put("p", "v1", {"p": 1}, "max-age", 10, now=1, persistent=True)
  assert TomTomCache(path, "drive-b").get("p", now=2) == {"p": 1}
  assert cache.allow_and_count("snap", 1, now=1)
  assert not cache.allow_and_count("snap", 1, now=1)


def test_invalid_corridor_clears_atomically(tmp_path):
  adapter = TomTomMapData(cache=TomTomCache(str(tmp_path / "c"), "s"), key_path=str(tmp_path / "missing"))
  adapter.result = result()
  adapter.update("{}", [0, 0])
  assert adapter.result is None


def test_request_window_changes_cache_key_with_progress():
  first = Corridor.parse(corridor(points=line(20), progress=100)).request_paths()[0]
  later = Corridor.parse(corridor(points=line(20), progress=900)).request_paths()[0]
  assert TomTomMapData._cache_key(first) != TomTomMapData._cache_key(later)


def test_single_continuation_replaces_unextended_base_candidate():
  raw = corridor(points=line(5), continuations=[{"geometry": [[.004, 0], [.008, 0]]}])
  paths = Corridor.parse(raw).request_paths()

  assert len(paths) == 1
  assert paths[0][-1] == [.008, 0]


def test_request_path_is_sampled_to_provider_limit():
  points = [[i * .00004, 0] for i in range(256)]
  full_path = Corridor.parse(corridor(points=points, progress=50)).request_paths(maximum_points=256)[0]
  path = Corridor.parse(corridor(points=points, progress=50)).request_paths()[0]

  assert len(path) == MAX_REQUEST_POINTS
  assert path[0] == full_path[0]
  assert path[-1] == full_path[-1]


def test_fetch_rejects_more_than_provider_limit(tmp_path):
  adapter = TomTomMapData(cache=TomTomCache(str(tmp_path / "c"), "s"), key_path=str(tmp_path / "missing"))
  with pytest.raises(ValueError, match="2..100 points"):
    adapter._fetch("key", line(MAX_REQUEST_POINTS + 1), None)


def test_request_window_change_reuses_active_result_with_remaining_coverage(tmp_path):
  adapter = TomTomMapData(cache=TomTomCache(str(tmp_path / "c"), "s"), key_path=str(tmp_path / "missing"))
  first = Corridor.parse(corridor(points=line(20), progress=100)).request_paths()[0]
  adapter.result = result(line(20))
  adapter.result_key = adapter._cache_key(first)

  adapter.update(corridor(points=line(20), progress=900), [.009, 0], now=1)

  assert adapter.result is not None
  assert adapter.result_key == adapter._cache_key(first)


def test_request_window_change_rejects_result_for_different_continuation(tmp_path):
  adapter = TomTomMapData(cache=TomTomCache(str(tmp_path / "c"), "s"), key_path=str(tmp_path / "missing"))
  old_path = line(20)
  adapter.result = result(old_path)
  adapter.result_key = adapter._cache_key(old_path)
  changed = corridor(points=line(10), progress=900, continuations=[
    {"geometry": [[.009, 0], [.014, .003], [.019, .003]]},
  ])

  adapter.update(changed, [.009, 0], now=1)

  assert adapter.result is None
  assert adapter.result_key is None


@pytest.mark.parametrize("raw", [
  corridor(confidence=.49),
  corridor(continuations=[
    {"geometry": [[.007, 0], [.012, 0]]},
    {"geometry": [[.007, 0], [.012, .001]]},
  ]),
])
def test_unreliable_or_ambiguous_corridor_does_not_request(tmp_path, raw):
  key_path = tmp_path / "keys"
  key_path.write_text("TOMTOM_API_KEY=test\n")
  adapter = TomTomMapData(cache=TomTomCache(str(tmp_path / "c"), "s"), key_path=str(key_path))
  adapter.update(raw, [0, 0], now=1)
  assert adapter.future is None
