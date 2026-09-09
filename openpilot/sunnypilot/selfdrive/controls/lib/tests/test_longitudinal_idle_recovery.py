from types import SimpleNamespace as NS

import pytest

from openpilot.sunnypilot.selfdrive.controls.controlsd_ext import longitudinal_plan_sp_idle_active


class IdleMessages(dict):
  def all_checks(self, services):
    return all(self.healthy.get(service, True) for service in services)


@pytest.fixture
def idle_messages():
  sm = IdleMessages(
    longitudinalPlanSP=NS(speedLimit=NS(assist=NS(longitudinalIdle=True))),
    longitudinalPlan=NS(shouldStop=False, fcw=False),
    controlsState=NS(forceDecel=False),
    carState=NS(gasPressed=False, brakePressed=False),
  )
  sm.healthy = {}
  return sm


@pytest.mark.parametrize('service', ['longitudinalPlanSP', 'longitudinalPlan', 'radarState'])
def test_stale_or_invalid_plan_cannot_hold_idle(idle_messages, service):
  assert longitudinal_plan_sp_idle_active(idle_messages)
  idle_messages.healthy[service] = False
  assert not longitudinal_plan_sp_idle_active(idle_messages)


@pytest.mark.parametrize('service,field', [
  ('longitudinalPlan', 'shouldStop'), ('longitudinalPlan', 'fcw'), ('controlsState', 'forceDecel'),
  ('carState', 'gasPressed'), ('carState', 'brakePressed'),
])
def test_idle_yields_to_control_requests(idle_messages, service, field):
  setattr(idle_messages[service], field, True)
  assert not longitudinal_plan_sp_idle_active(idle_messages)


@pytest.fixture
def planner_flow(monkeypatch):
  """Run the real planner update with deterministic MPC output, without a native solver."""
  import importlib.util
  import sys
  from pathlib import Path
  import numpy as np
  from openpilot.cereal import log
  from openpilot.common.constants import CV
  from openpilot.common.filter_simple import FirstOrderFilter
  from openpilot.selfdrive.modeld.constants import ModelConstants
  from openpilot.sunnypilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlannerSP, SpeedLimitApproach

  mpc_name = 'openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc'
  with monkeypatch.context() as imports:
    imports.setitem(sys.modules, mpc_name, NS(LongitudinalMpc=object,
                    LongitudinalPlanSource=log.LongitudinalPlan.LongitudinalPlanSource, T_IDXS=ModelConstants.T_IDXS))
    spec = importlib.util.spec_from_file_location('planner_idle_test', Path(__file__).resolve().parents[5] /
                                                 'selfdrive/controls/lib/longitudinal_planner.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

  monkeypatch.setattr(LongitudinalPlannerSP, 'update', lambda self, sm: None)
  monkeypatch.setattr(LongitudinalPlannerSP, 'update_targets', lambda self, *args: (51. * CV.KPH_TO_MS, self.output_a_target))
  monkeypatch.setattr(module, 'get_slc_no_brake', lambda: True)
  monkeypatch.setattr(module, 'get_slc_no_brake_mode', lambda: 'idle')
  monkeypatch.setattr(module, 'get_longitudinal_no_lead_decel_mode', lambda: 'idle')
  monkeypatch.setattr(module, 'get_slc_no_brake_release_gap_kph', lambda: 5.)
  monkeypatch.setattr(module, 'get_accel_from_plan', lambda *args, **kwargs: planner.mpc.accel)

  planner = module.LongitudinalPlanner.__new__(module.LongitudinalPlanner)
  planner.CP = NS(openpilotLongitudinalControl=True, longitudinalActuatorDelay=0.2, steerRatio=15., wheelbase=2.8)
  planner.dt = 0.05
  planner.fcw = False
  planner.longitudinal_idle = False
  planner.longitudinal_idle_block_frames = 0
  planner.no_lead_idle_target = 0.
  planner.v_cruise_kph_prev = 80.
  planner.speed_limit_approach = SpeedLimitApproach()
  planner.coast_lead_stable_time = module.LEAD_COAST_REENTRY_STABLE_S
  planner.coast_lead_present = (False, False)
  planner.coast_lead_distances = (None, None)
  planner.v_desired_filter = FirstOrderFilter(70. * CV.KPH_TO_MS, 2., 0.05)
  planner.a_cruise = planner.output_a_target = 0.
  planner.source = module.SpeedLimitPlanSource.speedLimitAssist
  planner.resolver = NS(lower_lookahead_active=True, speed_limit_final_last=51. * CV.KPH_TO_MS,
                        distance=200., lookahead_speed_factor_down=4.)
  planner.is_e2e = lambda sm: False
  planner.mpc = NS(set_weights=lambda *a, **k: None, set_cur_state=lambda *a: None, update=lambda *a, **k: None,
                   v_solution=np.zeros(len(ModelConstants.T_IDXS)), a_solution=np.zeros(len(ModelConstants.T_IDXS)),
                   j_solution=np.zeros(len(ModelConstants.T_IDXS)-1), crash_cnt=0,
                   source=module.LongitudinalPlanSource.lead0, accel=0.5)
  sm = IdleMessages(
    carControl=NS(orientationNED=[]),
    carState=NS(vEgo=70. * CV.KPH_TO_MS, vCruise=80., buttonEvents=[], standstill=False, brakePressed=False,
                gasPressed=False, aEgo=0., steeringAngleDeg=0.),
    controlsState=NS(forceDecel=False, longControlState=module.LongCtrlState.pid),
    selfdriveState=NS(enabled=True, personality=log.LongitudinalPersonality.standard),
    modelV2=NS(meta=NS(disengagePredictions=NS(gasPressProbs=[1., 1.])), action=NS(desiredAcceleration=0., shouldStop=False)),
    vehicleParameters=NS(angleOffsetDeg=0.),
    radarState=NS(leadOne=NS(present=False, dRel=60., vRel=0., aLeadK=0.),
                  leadTwo=NS(present=False, dRel=70., vRel=0., aLeadK=0.)),
  )
  sm.healthy = {}
  return planner, sm


def test_planner_releases_to_final_target_without_reentering_idle(planner_flow):
  from openpilot.common.constants import CV
  planner, sm = planner_flow
  planner.update(sm)
  assert planner.longitudinal_idle
  sm['carState'].vEgo = 56. * CV.KPH_TO_MS
  planner.update(sm)
  assert not planner.longitudinal_idle
  assert planner.output_a_target < 0.
  sm['carState'].vEgo = 57. * CV.KPH_TO_MS
  planner.update(sm)
  assert not planner.longitudinal_idle
  sm['carState'].vEgo = 49. * CV.KPH_TO_MS
  for _ in range(80):
    planner.update(sm)
  assert planner.output_a_target > 0.


def test_new_lead_requires_stability_and_braking_wins(planner_flow):
  planner, sm = planner_flow
  for _ in range(45):
    planner.update(sm)
  sm['radarState'].leadOne.present = True
  planner.update(sm)
  assert not planner.longitudinal_idle
  for _ in range(45):
    planner.update(sm)
  assert planner.longitudinal_idle
  planner.mpc.accel = -0.4
  planner.update(sm)
  assert not planner.longitudinal_idle
  assert planner.output_a_target <= -0.4


@pytest.mark.parametrize('field,value', [('vRel', -0.5), ('aLeadK', -0.5), ('dRel', 10.)])
def test_unsafe_second_lead_blocks_idle(planner_flow, field, value):
  planner, sm = planner_flow
  sm['radarState'].leadTwo.present = True
  setattr(sm['radarState'].leadTwo, field, value)
  for _ in range(45):
    planner.update(sm)
  assert not planner.longitudinal_idle


def test_released_approach_survives_temporary_other_cruise_source(planner_flow):
  from openpilot.common.constants import CV
  from openpilot.sunnypilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanSource
  planner, sm = planner_flow
  sm['carState'].vEgo = 56. * CV.KPH_TO_MS
  planner.update(sm)
  planner.source = LongitudinalPlanSource.sccMap
  sm['carState'].vEgo = 57. * CV.KPH_TO_MS
  planner.update(sm)
  planner.source = LongitudinalPlanSource.speedLimitAssist
  planner.update(sm)
  assert not planner.longitudinal_idle
  assert planner.output_a_target < 0.


def test_flickering_lead_cannot_reenter_idle_on_missing_frames(planner_flow):
  planner, sm = planner_flow
  planner.update(sm)
  assert planner.longitudinal_idle
  for i in range(100):
    sm['radarState'].leadOne.present = i % 2 == 0
    planner.update(sm)
    assert not planner.longitudinal_idle
  # Once the lead is consistently absent, coasting can resume.
  for _ in range(45):
    planner.update(sm)
  assert planner.longitudinal_idle


def test_braking_requires_stable_recovery_before_idle(planner_flow):
  planner, sm = planner_flow
  sm['radarState'].leadOne.present = True
  for _ in range(45):
    planner.update(sm)
  assert planner.longitudinal_idle
  for _ in range(20):
    planner.mpc.accel = -0.4
    planner.update(sm)
    assert not planner.longitudinal_idle
    assert planner.output_a_target <= -0.4
    planner.mpc.accel = 0.5
    planner.update(sm)
    assert not planner.longitudinal_idle
  for _ in range(45):
    planner.update(sm)
  assert planner.longitudinal_idle


def test_lead_disappearing_after_braking_does_not_bypass_delay(planner_flow):
  planner, sm = planner_flow
  sm['radarState'].leadOne.present = True
  planner.mpc.accel = -0.4
  planner.update(sm)
  sm['radarState'].leadOne.present = False
  planner.mpc.accel = 0.5
  for _ in range(30):
    planner.update(sm)
    assert not planner.longitudinal_idle
  for _ in range(15):
    planner.update(sm)
  assert planner.longitudinal_idle
