import json
from types import SimpleNamespace as NS
from unittest.mock import Mock, mock_open

import pytest
import numpy as np

from openpilot.common.constants import CV
from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit.decision_log import SpeedLimitDecisionLogger


@pytest.fixture
def audit():
  clock = [100.]
  events = []
  logger = SpeedLimitDecisionLogger(emit=lambda event, **data: events.append({"event": event, **data}),
                                    clock=lambda: clock[0], enabled=lambda: True)
  return logger, events, clock


def test_changes_are_throttled_but_heartbeats_update_context(audit):
  logger, events, clock = audit
  logger.log("slc_decision", "same", {"distance_m": 100})
  clock[0] += .1
  logger.log("slc_decision", "same", {"distance_m": 99})
  logger.log("slc_decision", "changed", {"distance_m": 98})
  assert len(events) == 1
  clock[0] += .5
  logger.log("slc_decision", "changed", {"distance_m": 90})
  assert events[-1]["trigger"] == "change"
  clock[0] += 5
  logger.log("slc_decision", "changed", {"distance_m": 50})
  assert len(events) == 3
  assert events[-1]["trigger"] == "heartbeat"
  assert events[-1]["distance_m"] == 50


def test_engagement_events_bypass_change_throttle(audit):
  logger, events, clock = audit
  logger.log("slc_application", "disengaged", {})
  clock[0] += .01
  logger.log("slc_application", "engaged", {"auto_accepted_on_engagement": True}, force=True)
  assert len(events) == 2
  assert events[-1]["auto_accepted_on_engagement"]
  clock[0] += .01
  logger.log("slc_application", "engaged", {"auto_accepted_on_engagement": True}, force=True)
  assert len(events) == 3  # Re-engagement must not disappear if the intervening disengagement was throttled.


def test_disabled_logging_does_not_build_context_and_can_reload(audit):
  logger, events, clock = audit
  enabled = [False]
  logger.enabled = lambda: enabled[0]
  build = Mock(side_effect=AssertionError("must not build disabled diagnostics"))
  logger.log("slc_decision", build, build)
  assert not events
  build.assert_not_called()
  enabled[0] = True
  clock[0] += 5
  logger.log("slc_decision", "enabled", {})
  assert len(events) == 1


def test_audit_handles_non_finite_values_and_backend_failures(audit):
  logger, events, clock = audit
  logger.log("slc_decision", "nonfinite", {"age": float("inf"), "position": [float("nan"), 8.]})
  assert events[-1]["age"] is None
  assert events[-1]["position"] == [None, 8.]
  json.dumps(events[-1], allow_nan=False)
  logger.emit = Mock(side_effect=OSError("logging unavailable"))
  clock[0] += 1
  logger.log("slc_decision", "failure", {})
  logger.log("slc_decision", "failure", {})
  assert logger.emit.call_count == 1
  logger.log("slc_application", "bad_context", lambda: 1 / 0)


@pytest.mark.parametrize('value', [True, False])
def test_numpy_boolean_is_logged_as_json_boolean(audit, value):
  logger, events, _ = audit
  logger.log('slc_decision', 'numpy_boolean', {'lower_lookahead_active': np.bool_(value)})
  assert json.loads(json.dumps(events[-1]))['lower_lookahead_active'] is value


@pytest.fixture
def resolver_context(monkeypatch, audit):
  from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit import speed_limit_resolver as module
  from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit.common import Policy

  logger, events, clock = audit
  params = Mock()
  values = {"SpeedLimitPolicy": int(Policy.map_data_only), "SpeedLimitOffsetType": 0, "SpeedLimitValueOffset": 0}
  params.get.side_effect = lambda key, **kwargs: values[key]
  params.get_bool.return_value = True
  monkeypatch.setattr(module, "Params", lambda: params)
  monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
  monkeypatch.setattr(module, "get_slc_lookahead_lower_limits", lambda: True)
  monkeypatch.setattr(module, "get_slc_lookahead_speed_factor_down", lambda: 5.)
  resolver = module.SpeedLimitResolver()
  resolver.decision_logger = logger

  class Messages(dict):
    pass

  sm = Messages(carStateSP=NS(speedLimit=0.), liveMapDataSP=NS(
    speedLimit=50 * CV.KPH_TO_MS, speedLimitValid=True, speedLimitAhead=30 * CV.KPH_TO_MS,
    speedLimitAheadValid=True, speedLimitAheadDistance=400., roadName="Test Road"))
  sm.logMonoTime = {"liveMapDataSP": int(clock[0] * 1e9), "carStateSP": int(clock[0] * 1e9)}
  sm.valid = {"liveMapDataSP": True, "carStateSP": True}
  return resolver, sm, events, clock


def test_logs_engagement_source_and_raw_candidates(resolver_context):
  resolver, sm, events, clock = resolver_context
  resolver.update(50 * CV.KPH_TO_MS, sm, current_only=True)
  event = events[-1]
  assert event["event"] == "slc_decision"
  assert event["reason"] == "engagement_current_limit_only"
  assert event["selected_source"] == "map"
  assert event["selected_kph"] == 50
  assert event["map_upcoming_kph"] == 30
  assert event["map_message_mono_time_ns"] == int(clock[0] * 1e9)
  assert not event["selected_invalid_map_message"]


def test_unlimited_map_uses_advisory_without_offset_and_preserves_sign(resolver_context):
  from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit.common import OffsetType
  resolver, sm, events, clock = resolver_context
  resolver.frame = 1  # Keep explicit offset settings for this update.
  resolver.offset_type, resolver.offset_value = OffsetType.fixed, 10
  sm['liveMapDataSP'].speedLimit = 130 * CV.KPH_TO_MS
  sm['liveMapDataSP'].speedLimitUnlimited = True
  resolver.update(100 * CV.KPH_TO_MS, sm)
  assert resolver.speed_limit_final * CV.MS_TO_KPH == pytest.approx(130)
  assert resolver.speed_limit_unlimited and resolver.speed_limit_last_unlimited
  assert events[-1]['selected_unlimited'] is True
  # An outage retains the sign, and a subsequent posted limit replaces it.
  sm['liveMapDataSP'].speedLimitValid = False
  resolver.update(100 * CV.KPH_TO_MS, sm)
  assert not resolver.speed_limit_unlimited and resolver.speed_limit_last_unlimited
  sm['liveMapDataSP'].speedLimitValid = True
  sm['liveMapDataSP'].speedLimitUnlimited = False
  sm['liveMapDataSP'].speedLimit = 120 * CV.KPH_TO_MS
  resolver.update(100 * CV.KPH_TO_MS, sm)
  assert not resolver.speed_limit_last_unlimited
  assert resolver.speed_limit_final * CV.MS_TO_KPH == pytest.approx(130)  # Ordinary +10 offset still applies.


def test_car_unlimited_sentinel_is_not_a_253_kph_target(resolver_context):
  from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit.common import Policy
  resolver, sm, _, _ = resolver_context
  resolver.frame, resolver.policy = 1, Policy.car_state_only
  sm['carStateSP'].speedLimit = 253 * CV.KPH_TO_MS
  resolver.update(100 * CV.KPH_TO_MS, sm)
  assert resolver.speed_limit_final * CV.MS_TO_KPH == pytest.approx(130)
  assert resolver.speed_limit_unlimited


def test_logs_separate_approach_without_changing_enforced_limit(resolver_context):
  resolver, sm, events, clock = resolver_context
  sm['liveMapDataSP'].speedLimitAheadDistance = 240.
  resolver.update(50 * CV.KPH_TO_MS, sm)
  assert events[-1]["approach_reason"] == "upcoming_awaiting_qualification"
  resolver._ahead_since = clock[0] - 2
  clock[0] += 1
  sm.logMonoTime["liveMapDataSP"] = int(clock[0] * 1e9)
  sm['liveMapDataSP'].speedLimitAheadDistance = 230.
  resolver.update(50 * CV.KPH_TO_MS, sm)
  assert events[-1]["ahead_qualified"]
  assert events[-1]["selected_kph"] == 50
  assert events[-1]["reason"] == "current_map_limit"
  assert events[-1]["approach_reason"] == "lower_lookahead_in_range"
  assert events[-1]["approach_target_kph"] == 30
  assert events[-1]["approach_distance_m"] > 0


def test_logs_stale_and_invalid_message_metadata(resolver_context):
  resolver, sm, events, clock = resolver_context
  sm.valid['liveMapDataSP'] = False
  resolver.update(50 * CV.KPH_TO_MS, sm, current_only=True)
  assert not events[-1]["map_message"]["valid"]
  assert events[-1]["selected_invalid_map_message"]
  clock[0] += 100
  resolver.update(50 * CV.KPH_TO_MS, sm)
  assert events[-1]["reason"] == "no_eligible_source"
  assert events[-1]["map_candidate_reason"] == "stale_map_message"


@pytest.fixture
def assist(monkeypatch):
  from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit import speed_limit_assist as module
  from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit.common import Mode

  params = Mock()
  params.get.return_value = int(Mode.assist)
  params.get_bool.return_value = True
  monkeypatch.setattr(module, "Params", lambda: params)
  monkeypatch.setattr(module, "set_speed_limit_assist_availability", lambda *args: None)
  return module.SpeedLimitAssist(NS(openpilotLongitudinalControl=True, pcmCruise=False), NS())


def test_application_logs_auto_accept_and_actual_limiting_source(assist, audit):
  from openpilot.sunnypilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlannerSP, LongitudinalPlanSource
  from openpilot.sunnypilot.selfdrive.selfdrived.events import EventsSP

  logger, events, clock = audit
  assist.update(True, False, 40 * CV.KPH_TO_MS, 0, 90 * CV.KPH_TO_MS,
                50 * CV.KPH_TO_MS, 51 * CV.KPH_TO_MS, True, 0, EventsSP())
  planner = LongitudinalPlannerSP.__new__(LongitudinalPlannerSP)
  planner.sla = assist
  planner.resolver = NS(decision_context={"resolver_frame": 7, "selected_source": "map", "map_message_mono_time_ns": 123},
                        speed_limit_final_last=51 * CV.KPH_TO_MS, last_decision_event_ns=456)
  planner.source = LongitudinalPlanSource.speedLimitAssist
  planner.output_v_target = 51 * CV.KPH_TO_MS
  planner.decision_logger = logger
  planner._log_speed_limit_application(90 * CV.KPH_TO_MS)
  assert events[-1]["auto_accepted_on_engagement"]
  assert events[-1]["reason"] == "current_limit_auto_accepted_on_engagement"
  assert events[-1]["target_kph"] == 51
  assert events[-1]["slc_controls_target"]
  assert events[-1]["map_message_mono_time_ns"] == 123
  assert events[-1]["resolver_decision_mono_time_ns"] == 456

  clock[0] += 1
  assist.update(True, False, 40 * CV.KPH_TO_MS, 0, 90 * CV.KPH_TO_MS,
                50 * CV.KPH_TO_MS, 51 * CV.KPH_TO_MS, True, 0, EventsSP())
  planner.source = LongitudinalPlanSource.cruise
  planner.output_v_target = 30 * CV.KPH_TO_MS
  planner._log_speed_limit_application(30 * CV.KPH_TO_MS)
  assert events[-1]["planner_target_kph"] == 30
  assert events[-1]["target_kph"] == 51
  assert not events[-1]["slc_controls_target"]


def test_application_records_confirmation_reason_before_tracking_updates(assist):
  from openpilot.sunnypilot.selfdrive.selfdrived.events import EventsSP

  for limit in [80, 30]:
    assist.update(True, False, 80 * CV.KPH_TO_MS, 0, 90 * CV.KPH_TO_MS,
                  limit * CV.KPH_TO_MS, (limit + 1) * CV.KPH_TO_MS, True, 0, EventsSP())
  snapshot = assist.decision_snapshot()
  assert snapshot['state'] == 'preActive'
  assert snapshot['reason'] == 'suspicious_drop_requires_confirmation'
  assert snapshot['suspicious_drop_confirmation']
  assert not snapshot['auto_accepted_on_engagement']
  assist.update(True, False, 30 * CV.KPH_TO_MS, 0, 31 * CV.KPH_TO_MS,
                30 * CV.KPH_TO_MS, 31 * CV.KPH_TO_MS, True, 0, EventsSP())
  assert assist.decision_snapshot()['reason'] == 'confirmed_with_set_speed'


def test_map_observation_records_location_provider_and_correlation_id(audit, monkeypatch):
  from openpilot.sunnypilot.mapd.live_map_data import osm_map_data
  from openpilot.sunnypilot.navd.helpers import Coordinate

  logger, events, clock = audit
  osm = osm_map_data.OsmMapData.__new__(osm_map_data.OsmMapData)
  osm.sm = {'liveLocationKalman': NS(gpsOK=True)}
  osm.pm = Mock()
  osm.mem_params = Mock()
  osm.mem_params.get.side_effect = lambda key: {
    'RoadName': 'Test Road', 'MapSpeedLimit': 50 * CV.KPH_TO_MS,
    'NextMapSpeedLimit': {'speedlimit': 30 * CV.KPH_TO_MS, 'latitude': 48., 'longitude': 8.002},
  }.get(key)
  osm.last_position = Coordinate(48., 8.)
  osm.native_geometry = [[48., 8.], [48., 8.004]]
  osm.last_bearing = 90.
  osm.localizer_valid = True
  osm.decision_logger = logger
  osm.publish()
  published = osm.pm.send.call_args.args[1]
  event = events[-1]
  assert event['event'] == 'slc_observation'
  assert event['provider'] == 'osm'
  assert event['position'] == {'latitude': 48., 'longitude': 8.}
  assert event['map_message_mono_time_ns'] == published.logMonoTime
  clock[0] += 1
  osm.last_position = Coordinate(48.0002, 8.)
  osm.publish()
  assert len(events) == 2
  assert events[-1]['position']['latitude'] == 48.0002
  assert events[-1]['map_message_mono_time_ns'] == osm.pm.send.call_args.args[1].logMonoTime


def test_exports_only_slc_events_and_preserves_timestamps():
  from openpilot.sunnypilot.tools.slc_decisions import decision_events

  class Message:
    logMonoTime = 123

    def __init__(self, text):
      self.logMessage = text

    def which(self):
      return 'logMessage'

  messages = [Message('invalid json'), Message(json.dumps({'msg': 'ordinary message'})),
              Message(json.dumps({'msg': {'event': 'slc_application', 'reason': 'current_limit_auto_accepted_on_engagement'}}))]
  events = list(decision_events(messages))
  assert len(events) == 1
  assert events[0]['log_message_mono_time_ns'] == 123
  assert events[0]['reason'] == 'current_limit_auto_accepted_on_engagement'


@pytest.mark.parametrize(('ego_kph', 'pcm_cruise', 'expected', 'reason'), [
  (10., False, 40., 'ego_or_configured_initial_speed'),
  (60., False, 60., 'ego_or_configured_initial_speed'),
  (10., True, 30., 'factory_cruise_owns_initialization'),
])
def test_initial_cruise_logs_configured_vs_factory_speed(audit, ego_kph, pcm_cruise, expected, reason):
  from openpilot.selfdrive.car.cruise import VCruiseHelper

  logger, events, clock = audit
  helper = VCruiseHelper.__new__(VCruiseHelper)
  helper.CP = NS(pcmCruise=pcm_cruise)
  helper.CP_SP = NS(pcmCruiseSpeed=True)
  helper.v_cruise_kph = 30.
  helper.v_cruise_kph_last = 30.
  helper.has_speed_limit = True
  helper.speed_limit_final_last_kph = 50.
  helper.params = Mock()
  helper.params.get.return_value = 3
  helper.decision_logger = logger
  state = NS(vEgo=ego_kph * CV.KPH_TO_MS, cruiseState=NS(speed=30 * CV.KPH_TO_MS), buttonEvents=[])
  helper.initialize_v_cruise(state, 40)
  assert helper.v_cruise_kph == expected
  assert events[-1]['reason'] == reason
  assert events[-1]['configured_initial_kph'] == 40
  assert events[-1]['cruise_setting_kph'] == expected
  assert events[-1]['slc_target_kph'] == 50


def test_exports_real_compressed_rlog(tmp_path, monkeypatch, capsys):
  import zstandard
  from openpilot.cereal import messaging
  from openpilot.sunnypilot.tools import slc_decisions

  message = messaging.new_message(None, valid=True, logMessage=json.dumps({'msg': {
    'event': 'slc_application', 'decision_mono_time_ns': 123, 'map_message_mono_time_ns': 456,
    'reason': 'current_limit_auto_accepted_on_engagement', 'auto_accepted_on_engagement': True,
  }}))
  rlog = tmp_path / 'rlog.zst'
  rlog.write_bytes(zstandard.compress(message.to_bytes()))
  output = tmp_path / 'decisions.jsonl'
  monkeypatch.setattr('sys.argv', ['slc_decisions', str(rlog), '--output', str(output)])
  slc_decisions.main()
  events = [json.loads(line) for line in output.read_text().splitlines()]
  assert len(events) == 1
  assert events[0]['map_message_mono_time_ns'] == 456
  assert events[0]['log_message_mono_time_ns'] == message.logMonoTime
  assert json.loads(capsys.readouterr().err)['engagement_auto_accepts'] == 1
