"""Exercise current-limit enforcement and the separate coast target together."""
from types import SimpleNamespace as NS

import pytest

from openpilot.common.params import Params
from openpilot.selfdrive.car.cruise import V_CRUISE_UNSET
from openpilot.sunnypilot.selfdrive.controls.lib import longitudinal_planner as planner_module
from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit import speed_limit_assist as assist_module
from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit import speed_limit_resolver as resolver_module
from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit.common import Policy, OffsetType
from openpilot.sunnypilot.selfdrive.selfdrived.events import EventsSP


@pytest.fixture
def boundary_planner(tmp_path, monkeypatch):
  params = Params(str(tmp_path))
  for key, value in {"SpeedLimitMode": 3, "SpeedLimitPolicy": 1, "SpeedLimitOffsetType": 0, "SpeedLimitValueOffset": 0}.items():
    params.put(key, value, block=True)
  params.put_bool("IsMetric", True, block=True)
  for module in (resolver_module, assist_module):
    monkeypatch.setattr(module, 'Params', lambda: params)
    monkeypatch.setattr(module, 'time', NS(monotonic=lambda: clock[0]))
  clock = [100.]
  planner = planner_module.LongitudinalPlannerSP.__new__(planner_module.LongitudinalPlannerSP)
  planner.resolver = resolver_module.SpeedLimitResolver()
  planner.resolver.update_params = lambda: None
  planner.resolver.policy = Policy.map_data_only
  planner.resolver.offset_type = OffsetType.off
  planner.resolver.lookahead_lower_limits = True
  planner.resolver.lookahead_speed_factor_down = 4.
  planner.resolver.lookahead_speed_factor_up = 4.
  planner.sla = assist_module.SpeedLimitAssist(NS(brand='hyundai', openpilotLongitudinalControl=True, pcmCruise=False), NS(pcmCruiseSpeed=False))
  planner.events_sp = EventsSP()
  unavailable = NS(output_v_target=V_CRUISE_UNSET, output_a_target=0.)
  planner.scc = NS(update=lambda *args: None, vision=unavailable, map=unavailable)
  class Messages(dict):
    logMonoTime = {}
  sm = Messages(carState=NS(vCruiseCluster=108.), carStateSP=NS(speedLimit=0.),
                carControl=NS(longActive=True, cruiseControl=NS(override=False)),
                liveMapDataSP=NS(speedLimit=30., speedLimitValid=True, speedLimitAhead=20., speedLimitAheadValid=True,
                                 speedLimitAheadDistance=150.))
  sm.logMonoTime = {}
  def observe(second, distance, current=30., upcoming=20., cruise=30.):
    clock[0] = second
    sm.logMonoTime['liveMapDataSP'] = int(second * 1e9) - 1
    sm['liveMapDataSP'].speedLimit = current
    sm['liveMapDataSP'].speedLimitAhead = upcoming
    sm['liveMapDataSP'].speedLimitAheadValid = upcoming > 0.
    sm['liveMapDataSP'].speedLimitAheadDistance = distance
    return planner.update_targets(sm, 30., 0., cruise)[0]
  return planner, observe


def test_lower_approach_coasts_without_enforcing_until_boundary(boundary_planner):
  planner, observe = boundary_planner
  assert observe(100., 150.) == 30.
  assert observe(101., 120.) == 30.
  assert observe(102., 90.) == 30.
  resolver = planner.resolver
  assert planner.sla.is_active
  assert resolver.lower_lookahead_active
  assert resolver.approach_speed_limit_final == 20.
  assert resolver.speed_limit_final_last == 30.
  # A tie with cruise must still allow the idle/N approach.
  assert planner.source == planner_module.LongitudinalPlanSource.cruise
  allowed = planner_module.speed_limit_approach_allowed(planner.sla.is_active, resolver.lower_lookahead_active,
                                                       planner.source, planner.output_v_target, resolver.approach_speed_limit_final)
  assert allowed
  approach = planner_module.SpeedLimitApproach()
  assert approach.update(allowed, resolver.approach_speed_limit_final, 30., 1.)
  assert planner_module.speed_limit_idle_active(30., resolver.approach_speed_limit_final, 1., 'idle')
  assert not approach.update(allowed, resolver.approach_speed_limit_final, 21., 1.)
  assert observe(103., 0., current=20., upcoming=0.) == 20.
  assert not resolver.lower_lookahead_active
  assert resolver.approach_speed_limit_final == 0.


def test_higher_limit_anticipates_only_after_qualification(boundary_planner):
  planner, observe = boundary_planner
  assert observe(100., 90., current=20., upcoming=30.) == 20.
  assert observe(101., 60., current=20., upcoming=30.) == 20.
  assert observe(102., 30., current=20., upcoming=30.) == 30.
  assert not planner.resolver.lower_lookahead_active
  assert planner.resolver.map_decision_reason == 'higher_lookahead_in_range'
  assert observe(103., 0., current=30., upcoming=0.) == 30.


def test_disappearing_upcoming_limit_does_not_change_assist_target(boundary_planner):
  planner, observe = boundary_planner
  for second, distance in [(100., 150.), (101., 120.), (102., 90.)]:
    assert observe(second, distance) == 30.
  assert planner.resolver.lower_lookahead_active
  assert observe(103., 0., upcoming=0.) == 30.
  assert not planner.resolver.lower_lookahead_active
  assert planner.resolver.approach_distance == 0.


@pytest.mark.parametrize('assist,source,cruise,current_decel', [
  (False, 'cruise', 30., False),
  (True, 'sccVision', 30., False),
  (True, 'sccMap', 30., False),
  (True, 'cruise', 15., False),
  (True, 'cruise', 30., True),
])
def test_approach_cannot_override_other_controls(assist, source, cruise, current_decel):
  assert not planner_module.speed_limit_approach_allowed(assist, True, getattr(planner_module.LongitudinalPlanSource, source),
                                                        cruise, 20., current_decel)


@pytest.mark.parametrize('up_factor', [0., 4.])
def test_higher_limit_updates_cruise_without_extra_confirmation(boundary_planner, up_factor):
  from openpilot.cereal import custom
  from openpilot.common.constants import CV
  from openpilot.sunnypilot.selfdrive.car.cruise_ext import VCruiseHelperSP
  planner, observe = boundary_planner
  planner.resolver.lookahead_speed_factor_up = up_factor
  helper = VCruiseHelperSP.__new__(VCruiseHelperSP)
  helper.v_cruise_kph = helper.v_cruise_cluster_kph = 72.
  helper.v_cruise_min = 0.
  helper.prev_sla_state = assist_module.SpeedLimitAssistState.disabled
  helper.prev_speed_limit_final_last_kph = 0.

  def receive_plan():
    message = custom.LongitudinalPlanSP.new_message()
    message.speedLimit.resolver.speedLimitValid = planner.resolver.speed_limit_valid
    message.speedLimit.resolver.speedLimitLastValid = planner.resolver.speed_limit_last_valid
    message.speedLimit.resolver.speedLimitFinalLast = planner.resolver.speed_limit_final_last
    message.speedLimit.assist.state = planner.sla.state
    helper.update_speed_limit_assist(True, message)
    helper.update_speed_limit_assist_v_cruise_non_pcm()

  for second, distance in [(100., 90.), (101., 60.), (102., 30.), (103., 0.)]:
    assert observe(second, distance, current=20., upcoming=30., cruise=20.) == 20.
    receive_plan()
    assert helper.v_cruise_kph == pytest.approx(108. if up_factor > 0. and second >= 102. else 72.)
  observe(104., 0., current=30., upcoming=0., cruise=20.)
  assert planner.sla.is_active
  receive_plan()
  assert helper.v_cruise_kph == pytest.approx(108.)
  assert observe(105., 0., current=30., upcoming=0., cruise=helper.v_cruise_kph * CV.KPH_TO_MS) == 30.


@pytest.mark.parametrize('factor,distance,expected', [(0., 30., 20.), (1., 120., 20.), (1., 30., 30.)])
def test_higher_lookahead_range_and_disable(boundary_planner, factor, distance, expected):
  planner, observe = boundary_planner
  planner.resolver.lookahead_speed_factor_up = factor
  observe(100., distance + 60., current=20., upcoming=30.)
  observe(101., distance + 30., current=20., upcoming=30.)
  assert observe(102., distance, current=20., upcoming=30.) == expected


def test_higher_lookahead_disappearing_boundary_restores_current_limit(boundary_planner):
  planner, observe = boundary_planner
  observe(100., 90., current=20., upcoming=30.)
  observe(101., 60., current=20., upcoming=30.)
  assert observe(102., 30., current=20., upcoming=30.) == 30.
  assert observe(103., 0., current=20., upcoming=0.) == 20.
