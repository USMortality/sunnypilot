import concurrent.futures
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, mock_open

import pytest
import requests

from openpilot.sunnypilot.mapd.live_map_data import tomtom_map_data
from openpilot.sunnypilot.mapd.live_map_data.corridor import Corridor, closest_progress, extend_geometry_to_position, fingerprint
from openpilot.sunnypilot.mapd.live_map_data.tomtom_cache import TomTomCache
from openpilot.sunnypilot.mapd.live_map_data.tomtom_map_data import TomTomMapData, speed_ms


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
  assert TomTomMapData._parse_response(payload)["projectedValid"] is expected


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


def test_request_window_change_clears_active_result(tmp_path):
  adapter = TomTomMapData(cache=TomTomCache(str(tmp_path / "c"), "s"), key_path=str(tmp_path / "missing"))
  first = Corridor.parse(corridor(points=line(20), progress=100)).request_paths()[0]
  adapter.result = result()
  adapter.result_key = adapter._cache_key(first)

  adapter.update(corridor(points=line(20), progress=900), [.009, 0], now=1)

  assert adapter.result is None
  assert adapter.result_key is None


@pytest.mark.parametrize("raw", [
  corridor(confidence=.49),
  corridor(continuations=[{"geometry": [[.007, 0], [.012, 0]]}]),
])
def test_unreliable_or_ambiguous_corridor_does_not_request(tmp_path, raw):
  key_path = tmp_path / "keys"
  key_path.write_text("TOMTOM_API_KEY=test\n")
  adapter = TomTomMapData(cache=TomTomCache(str(tmp_path / "c"), "s"), key_path=str(key_path))
  adapter.update(raw, [0, 0], now=1)
  assert adapter.future is None


@pytest.fixture
def adapter(tmp_path, monkeypatch):
  key_path = tmp_path / "keys"
  key_path.write_text("TOMTOM_API_KEY=test+secret/key\n")
  provider = TomTomMapData(cache=TomTomCache(str(tmp_path / "cache"), "s"), key_path=str(key_path), internet_check=lambda: True)
  real_open = open
  monkeypatch.setattr(tomtom_map_data, "open", lambda path, mode="r": real_open(tmp_path / path.rsplit("/", 1)[-1], mode), raising=False)
  yield provider
  provider.executor.shutdown(wait=True)


def response_payload(limits):
  return {
    "route": [{"geometry": {"coordinates": [[lon, lat] for lat, lon in line()]},
               "properties": {"confidence": .95, "speedLimits": limits}}],
    "projectedPoints": [{"properties": {"snapResult": "Matched"}} for _ in line()],
  }


@pytest.mark.parametrize("limits", [
  {"value": 30, "unit": "kmph", "type": "Maximum"},
  [{"value": 30, "unit": "kmph", "type": "Maximum"}],
])
def test_fetch_parse_and_publish_limits(adapter, limits):
  response = Mock(status_code=200, text="response", headers={})
  response.json.return_value = response_payload(limits)
  adapter.request = Mock(return_value=response)
  raw = corridor()
  adapter.update(raw, [.002, 0], now=1)
  adapter.future.result(timeout=2)
  adapter.update(raw, [.002, 0], now=2)

  assert adapter.limits([.002, 0]) == pytest.approx((30 / 3.6, 0, 0))
  assert adapter.request.call_count == 1
  adapter.update(raw, [.002, 0], now=3)
  assert adapter.request.call_count == 1
  adapter.result = None
  adapter.update(raw, [.002, 0], now=4)
  assert adapter.result is not None  # Reloads the persisted response without another request.
  assert adapter.request.call_count == 1


@pytest.mark.parametrize("limits", [None, {}, [], {"value": 0, "unit": "kmph", "type": "Maximum"}])
def test_missing_speed_limit_falls_back(adapter, limits):
  adapter.result = adapter._parse_response(response_payload(limits))
  assert adapter.limits([.002, 0]) is None


@pytest.mark.parametrize("pending", [False, True])
def test_shifted_corridor_reuses_valid_result(adapter, pending):
  raw = corridor()
  key = adapter._cache_key(Corridor.parse(raw).request_paths()[0])
  value = result()
  value["reference"] = line()
  if pending:
    adapter.future_key = key
    adapter.future = concurrent.futures.Future()
    adapter.future.set_result(value)
  else:
    adapter.result, adapter.result_key = value, key
  shifted = corridor(points=[[lat + .00001, lon] for lat, lon in line()])
  adapter.request = Mock(side_effect=AssertionError("unnecessary request"))
  adapter.update(shifted, [.002, 0], now=2)

  assert adapter.result is value
  assert adapter.limits([.002, 0])[0] == pytest.approx(50 / 3.6)
  assert adapter.future is None
  adapter.request.assert_not_called()


def test_moving_window_reuses_overlap(adapter):
  value = result()
  value["reference"] = line()
  adapter.result, adapter.result_key = value, adapter._cache_key(line())
  adapter.update(corridor(points=line(12), progress=300), [.003, 0], now=2)
  assert adapter.result is value
  assert adapter.future is None


@pytest.mark.parametrize("points", [
  list(reversed(line())),
  line(lon=.001),
  line()[:4] + [[.004, .001], [.005, .002], [.006, .003]],
])
def test_changed_road_rejects_reuse(adapter, points):
  value = result()
  value["reference"] = line()  # Original reference remains valid even after the road changes.
  adapter.result, adapter.result_key = value, adapter._cache_key(line())
  adapter.key = ""  # Observe fallback without submitting a real request.
  adapter.update(corridor(points=points), [.002, 0], now=2)
  assert adapter.result is None
  assert adapter.result_key is None


def test_expired_result_not_reused(adapter):
  adapter.result = dict(result(), reference=line(), expires=1)
  adapter.result_key = adapter._cache_key(line())
  adapter.key = ""
  adapter.update(corridor(), [.002, 0], now=2)
  assert adapter.limits([.002, 0]) is None


def test_http_failure_redacts_both_logs(adapter, tmp_path):
  adapter.debug_logging = True
  response = requests.Response()
  response.status_code = 403
  response.url = "https://api.tomtom.com/snapToRoads/1?key=test%2Bsecret%2Fkey&fields=example"
  response._content = b'error echoing test+secret/key'
  adapter.request = Mock(return_value=response)
  adapter.update(corridor(), [.002, 0], now=1)
  with pytest.raises(requests.HTTPError):
    adapter.future.result(timeout=2)
  adapter.update(corridor(), [.002, 0], now=2)

  for name in ("tomtom_fetch", "tomtom_future_exc"):
    log = (tmp_path / name).read_text()
    assert "test+secret/key" not in log
    assert "test%2Bsecret%2Fkey" not in log
    assert "[REDACTED]" in log
  assert adapter.result is None
  assert adapter.failures == 1
  assert adapter.retry_after > 2


def test_unwritable_debug_log_does_not_fail_request(adapter, monkeypatch):
  adapter.debug_logging = True
  response = Mock(status_code=200, text="response")
  response.json.return_value = response_payload({"value": 30, "unit": "kmph", "type": "Maximum"})
  adapter.request = Mock(return_value=response)
  monkeypatch.setattr(tomtom_map_data, "open", Mock(side_effect=OSError("read-only")))
  fetched = adapter._fetch(adapter._cache_key(line()), line(), None)
  assert fetched["sections"][0]["speed"] == pytest.approx(30 / 3.6)


def test_offline_wait_preserves_budget_and_reconnects_at_startup(adapter):
  adapter.internet_check = Mock(return_value=False)
  response = Mock(status_code=200, text="response")
  response.json.return_value = response_payload({"value": 30, "unit": "kmph", "type": "Maximum"})
  adapter.request = Mock(return_value=response)
  position = [.002, 0]

  adapter.update(corridor(), position, now=1)
  with pytest.raises(requests.ConnectionError):
    adapter.future.result(timeout=2)
  adapter.update(corridor(), position, now=2)
  adapter.request.assert_not_called()
  assert adapter.failures == 0
  assert adapter.cache.db.execute("SELECT count(*) FROM usage").fetchone()[0] == 0
  adapter.update(corridor(), position, now=3)
  assert adapter.future is None

  # No movement is required: first connectivity triggers the initial road fetch.
  adapter.internet_check.return_value = True
  adapter.update(corridor(), position, now=7)
  adapter.future.result(timeout=2)
  adapter.update(corridor(), position, now=8)
  assert adapter.limits(position)[0] == pytest.approx(30 / 3.6)
  assert adapter.request.call_count == 1
  assert adapter.cache.db.execute("SELECT count FROM usage").fetchone()[0] == 1


def test_offline_cache_still_supplies_speed_limit(adapter):
  adapter.internet_check = Mock(return_value=False)
  key = adapter._cache_key(Corridor.parse(corridor()).request_paths()[0])
  adapter.cache.put(key, "snap-v1", dict(result(), reference=line()), "test", 100, now=1)
  adapter.update(corridor(), [.002, 0], now=2)
  assert adapter.limits([.002, 0])[0] == pytest.approx(50 / 3.6)
  assert adapter.future is None
  adapter.internet_check.assert_not_called()


def test_budget_exhaustion_never_sends_request(adapter):
  adapter.monthly_limit = 0
  adapter.request = Mock(side_effect=AssertionError("quota exceeded"))
  adapter.update(corridor(), [.002, 0], now=1)
  with pytest.raises(tomtom_map_data.RequestBudgetExhausted):
    adapter.future.result(timeout=2)
  adapter.update(corridor(), [.002, 0], now=2)
  adapter.request.assert_not_called()
  assert adapter.failures == 0
  assert adapter.future is None


@pytest.mark.parametrize("error", [OSError("offline"), tomtom_map_data.ssl.SSLError("untrusted connection")])
def test_internet_probe_rejects_unreachable_endpoint(monkeypatch, error):
  connect = Mock(side_effect=error)
  monkeypatch.setattr(tomtom_map_data.socket, "create_connection", connect)
  assert not tomtom_map_data.internet_available()
  connect.assert_called_once_with(("api.tomtom.com", 443), timeout=2.0)


def test_internet_probe_requires_trusted_tls(monkeypatch):
  connect = MagicMock()
  context = MagicMock()
  monkeypatch.setattr(tomtom_map_data.socket, "create_connection", connect)
  monkeypatch.setattr(tomtom_map_data.ssl, "create_default_context", Mock(return_value=context))
  assert tomtom_map_data.internet_available()
  context.wrap_socket.assert_called_once_with(connect.return_value.__enter__.return_value, server_hostname="api.tomtom.com")


def test_initial_osm_update_requests_corridor_at_current_position(monkeypatch):
  from openpilot.sunnypilot.mapd.live_map_data import osm_map_data

  osm = osm_map_data.OsmMapData.__new__(osm_map_data.OsmMapData)
  osm.sm = {"liveLocationKalman": SimpleNamespace(
    status=osm_map_data.log.LiveLocationKalman.Status.valid,
    positionGeodetic=SimpleNamespace(valid=True, value=[.015, 0, 0]),
    calibratedOrientationNED=SimpleNamespace(value=[0, 0, 0]),
  )}
  osm.mem_params = Mock()
  osm.speed_limit_provider = Mock()
  osm.speed_limit_provider.limits.return_value = None
  points = [{"latitude": lat, "longitude": lon} for lat, lon in line(30)]
  monkeypatch.setattr(osm_map_data, "open", mock_open(read_data=json.dumps(points)), raising=False)
  osm.update_location()

  raw, position, heading = osm.speed_limit_provider.update.call_args.args
  assert position == [.015, 0]
  assert heading == 0
  current = Corridor.parse(raw)
  assert current.progress_m > 1600
  requested = current.request_paths()[0]
  assert requested[0][0] >= .014
  assert closest_progress(requested, position)[1] == pytest.approx(0)
  name, payload = osm.mem_params.put.call_args.args
  assert name == "LastGPSPosition"
  assert isinstance(payload, bytes)
  assert json.loads(payload)["latitude"] == .015


@pytest.mark.parametrize("connected", [False, True])
def test_live_validation_gates_offline_and_redacts_http_errors(tmp_path, monkeypatch, connected):
  from openpilot.sunnypilot.mapd.tools import validate_tomtom

  points = tmp_path / "points.json"
  points.write_text(json.dumps(line()))
  monkeypatch.setattr("sys.argv", ["validate_tomtom", str(points), "--live"])
  monkeypatch.setattr(validate_tomtom, "load_api_key", lambda: "validation-secret")
  monkeypatch.setattr(validate_tomtom, "internet_available", lambda: connected)
  response = requests.Response()
  response.status_code = 403
  response.url = "https://api.tomtom.com/snapToRoads/1?key=validation-secret"
  request = Mock(return_value=response)
  monkeypatch.setattr(validate_tomtom.requests, "post", request)
  with pytest.raises(SystemExit) as error:
    validate_tomtom.main()
  assert "validation-secret" not in str(error.value)
  assert request.call_count == int(connected)


def test_initial_road_nodes_ahead_of_vehicle_include_current_limit(adapter):
  position = [-.00056, 0]  # About 62 m before the first curvature node.
  points = extend_geometry_to_position(line(), position)
  payload = response_payload({"value": 30, "unit": "kmph", "type": "Maximum"})
  payload["route"][0]["geometry"]["coordinates"] = [[lon, lat] for lat, lon in points]
  payload["projectedPoints"].append({"properties": {"snapResult": "Matched"}})
  response = Mock(status_code=200, text="response")
  response.json.return_value = payload
  adapter.request = Mock(return_value=response)

  adapter.update(corridor(points=points, progress=0), position, now=1)
  adapter.future.result(timeout=2)
  adapter.update(corridor(points=points, progress=0), position, now=2)

  assert points[0] == position
  assert adapter.limits(position)[0] == pytest.approx(30 / 3.6)
  assert adapter.request.call_args.kwargs["json"]["points"][0]["geometry"]["coordinates"] == [0, -.00056]


@pytest.mark.parametrize("position", [
  [-.00056, .001],  # Adjacent road, outside the lateral bound.
  [-.002, 0],  # Too far from the native matched road.
  [.002, 0],  # Already within the geometry.
])
def test_unrelated_or_already_covered_position_does_not_extend_geometry(position):
  points = line()
  assert extend_geometry_to_position(points, position) == points


@pytest.mark.parametrize(("heading", "expected"), [
  (-95.75120399499312, 264.2487960050069),
  (-180, 180),
  (-360, 0),
  (0, 0),
  (359.9, 359.9),
  (360, 0),
  (725, 5),
  (None, None),
  (float("nan"), None),
  (float("inf"), None),
])
def test_request_headings_are_valid_compass_degrees(adapter, heading, expected):
  response = Mock(status_code=200, text="response")
  response.json.return_value = response_payload({"value": 30, "unit": "kmph", "type": "Maximum"})

  def request(*args, **kwargs):
    for i, point in enumerate(kwargs["json"]["points"]):
      properties = point["properties"]
      if expected is None or i >= 2:
        assert "heading" not in properties
      else:
        assert 0 <= properties["heading"] < 360
        assert properties["heading"] == pytest.approx(expected)
    return response

  adapter.request = request
  value = adapter._fetch(adapter._cache_key(line()), line(), heading)
  assert value["sections"][0]["speed"] == pytest.approx(30 / 3.6)


def test_repeated_road_segment_does_not_look_like_a_reversal(adapter):
  points = [[0, 0], [.002, 0], [.002, .001], [.002, 0], [.004, 0]]
  value = dict(result(points=points), reference=points)
  adapter.result, adapter.result_key = value, adapter._cache_key(points)
  adapter.update(corridor(points=points), [.0005, 0], now=2)
  assert adapter.result is value
  assert adapter.future is None
  assert adapter.limits([.0005, 0])[0] == pytest.approx(50 / 3.6)


def test_progress_window_selects_next_visit_to_repeated_road():
  points = [[0, 0], [.002, 0], [.002, .001], [.002, 0], [.004, 0]]
  position = [.002, .0005]
  first, _ = closest_progress(points, position)
  later, lateral = closest_progress(points, position, minimum_progress=first + 50)
  assert later > first + 50
  assert lateral == pytest.approx(0, abs=.1)


@pytest.mark.parametrize("enabled", [False, True])
def test_diagnostics_are_opt_in(adapter, tmp_path, enabled):
  assert adapter.debug_logging is False
  adapter.debug_logging = enabled
  response = Mock(status_code=200, text="response")
  response.json.return_value = response_payload({"value": 30, "unit": "kmph", "type": "Maximum"})
  adapter.request = Mock(return_value=response)
  adapter.update(corridor(), [.002, 0], now=1)
  adapter.future.result(timeout=2)
  adapter.update(corridor(), [.002, 0], now=2)
  assert adapter.limits([.002, 0])[0] == pytest.approx(30 / 3.6)
  assert not adapter._validate(result(line(lon=.001)), Corridor.parse(corridor()))
  for name in ("tomtom_corridor", "tomtom_fetch", "tomtom_parsed", "tomtom_validate"):
    assert (tmp_path / name).exists() is enabled


def test_single_pending_worker_is_not_submitted_twice(adapter):
  pending = concurrent.futures.Future()
  adapter.executor.shutdown(wait=True)
  adapter.executor = Mock()
  adapter.executor.submit.return_value = pending
  adapter.update(corridor(), [.002, 0], now=1)
  adapter.update(corridor(), [.002, 0], now=2)
  adapter.executor.submit.assert_called_once()
  assert adapter.future is pending


def test_network_failure_after_probe_counts_attempt_without_failure_backoff(adapter):
  adapter.request = Mock(side_effect=requests.ConnectionError("connection dropped after probe"))
  adapter.update(corridor(), [.002, 0], now=1)
  with pytest.raises(requests.ConnectionError):
    adapter.future.result(timeout=2)
  adapter.update(corridor(), [.002, 0], now=2)
  assert adapter.request.call_count == 1
  assert adapter.cache.db.execute("SELECT count FROM usage").fetchone()[0] == 1
  assert adapter.failures == 0
  assert adapter.retry_after == 7


def test_source_indicator_status_works_without_diagnostics(adapter, tmp_path, monkeypatch):
  from openpilot.sunnypilot.mapd.live_map_data import osm_map_data

  real_open = open
  monkeypatch.setattr(osm_map_data, "open", lambda path, mode="r": real_open(tmp_path / path.rsplit("/", 1)[-1], mode), raising=False)
  osm = osm_map_data.OsmMapData.__new__(osm_map_data.OsmMapData)
  osm.speed_limit_provider = adapter
  osm.mem_params = Mock()
  osm.mem_params.get.side_effect = lambda key: {"RoadName": "Test Road", "MapSpeedLimit": "8.33"}.get(key)
  osm.provider_limits = (50 / 3.6, 0, 0)
  assert not adapter.debug_logging
  assert osm.get_current_speed_limit() == pytest.approx(50 / 3.6)
  assert (tmp_path / "tomtom_active").read_text().startswith("TomTom:")
  assert osm.get_current_road_name() == "Test Road"
  osm.provider_limits = None
  assert osm.get_current_speed_limit() == pytest.approx(8.33)
  assert (tmp_path / "tomtom_active").read_text().strip() == "OSM fallback"
  assert osm.get_current_road_name() == "Test Road"
