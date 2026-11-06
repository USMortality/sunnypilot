#!/usr/bin/env python3
import numpy as np

import openpilot.cereal.messaging as messaging
from opendbc.car.structs import car
from opendbc.car.interfaces import ACCEL_MIN, ACCEL_MAX
from openpilot.common.constants import CV
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.modeld.constants import ModelConstants
from openpilot.selfdrive.controls.lib.accel_boost import AccelBoost
from openpilot.selfdrive.controls.lib.cruise_accel import A_CRUISE_MIN, get_cruise_accel
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import LongitudinalMpc, LongitudinalPlanSource
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import T_IDXS as T_IDXS_MPC
from openpilot.selfdrive.controls.lib.drive_helpers import CONTROL_N, get_accel_from_plan, should_stop
from openpilot.selfdrive.car.cruise import V_CRUISE_MAX, V_CRUISE_UNSET
from openpilot.common.swaglog import cloudlog
from openpilot.sunnypilot import PARAMS_UPDATE_PERIOD
from openpilot.sunnypilot.selfdrive.controls.lib.lead_coast import LeadCoastGap

from openpilot.sunnypilot.selfdrive.controls.lib.longitudinal_planner import (
  LongitudinalPlannerSP,
  SpeedLimitApproach,
  LongitudinalPlanSource as SpeedLimitPlanSource,
  limit_speed_limit_decel_target,
  lead_coast_min_distance,
  no_lead_normal_decel_idle_active,
  speed_limit_current_limit_decel_needed,
  speed_limit_approach_allowed,
  speed_limit_idle_active,
  speed_limit_no_brake_accel_target,
)
from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit.slc_config import (
  get_longitudinal_e2e_enabled,
  get_longitudinal_no_lead_idle_min_decel,
  get_longitudinal_no_lead_idle_decel_cooldown_s,
  get_longitudinal_no_lead_idle_overspeed_margin_kph,
  get_longitudinal_no_lead_decel_mode,
  get_slc_no_brake,
  get_slc_no_brake_accel,
  get_slc_no_brake_mode,
  get_slc_no_brake_release_gap_kph,
  get_slc_speed_limit_max_decel,
)

CONTROL_N_T_IDX = ModelConstants.T_IDXS[:CONTROL_N]
MIN_ALLOW_THROTTLE_SPEED = 2.5
CRUISE_TARGET_CHANGE_MIN_KPH = 0.1
LONGITUDINAL_IDLE_REENTRY_BLOCK_FRAMES = int(1.0 / DT_MDL)
LEAD_COAST_REENTRY_STABLE_S = 2.0
# A brief, noisy lead reading must not restart the whole qualification period.
# Only sustained unsafe readings reset it.
LEAD_COAST_UNSAFE_GRACE_FRAMES = int(0.25 / DT_MDL)
# Lead-planner braking blocks entry into coasting. Once N is active, the
# saved lead headway controls release instead of MPC gap corrections.
LEAD_COAST_HARD_BRAKE_ACCEL = -0.4
LEAD_COAST_SOFT_BRAKE_ACCEL = -0.15
LEAD_COAST_SOFT_BRAKE_FRAMES = int(0.2 / DT_MDL)
ButtonType = car.CarState.ButtonEvent.Type
CRUISE_TARGET_DOWN_BUTTONS = (ButtonType.decelCruise, ButtonType.setCruise)
CRUISE_TARGET_UP_BUTTONS = (ButtonType.accelCruise, ButtonType.resumeCruise)


def get_coast_accel(pitch):
  return np.sin(pitch) * -5.65 - 0.3


class LongitudinalPlanner(LongitudinalPlannerSP):
  def __init__(self, CP, CP_SP, init_v=0.0, init_a=0.0, dt=DT_MDL):
    self.CP = CP
    self.mpc = LongitudinalMpc(dt=dt)
    LongitudinalPlannerSP.__init__(self, self.CP, CP_SP, self.mpc)
    self.fcw = False
    self.dt = dt
    self.accel_boost = AccelBoost()
    self.longitudinal_idle = False
    self.speed_limit_approach = SpeedLimitApproach()
    # No lead starts qualified; the first detected lead, invalid inputs, or a
    # controller reset clears this timer before idle eligibility is evaluated.
    self.coast_lead_stable_time = LEAD_COAST_REENTRY_STABLE_S
    self.coast_lead_present = (False, False)
    self.coast_lead_distances = (None, None)
    self.coast_lead_unsafe_frames = 0
    self.coast_lead_gap = LeadCoastGap()
    self.coast_lead_brake_frames = 0
    self.longitudinal_idle_block_frames = 0
    self.no_lead_idle_target = 0.
    self.v_cruise_kph_prev = V_CRUISE_UNSET
    self.slc_config_frame = -1
    self._update_slc_config(force=True)

    self.v_desired_filter = FirstOrderFilter(init_v, 2.0, self.dt)
    self.a_cruise = init_a
    self.output_a_target = init_a
    self.output_should_stop = False

    self.v_desired_trajectory = np.zeros(CONTROL_N)
    self.a_desired_trajectory = np.zeros(CONTROL_N)
    self.j_desired_trajectory = np.zeros(CONTROL_N)

  def _update_slc_config(self, force=False):
    self.slc_config_frame = getattr(self, 'slc_config_frame', -1) + 1
    if not force and self.slc_config_frame % int(PARAMS_UPDATE_PERIOD / self.dt) != 0:
      return

    self.speed_limit_no_brake = get_slc_no_brake()
    self.longitudinal_e2e_enabled = get_longitudinal_e2e_enabled()
    self.no_lead_decel_mode = get_longitudinal_no_lead_decel_mode()
    self.no_lead_idle_min_decel = get_longitudinal_no_lead_idle_min_decel()
    self.no_lead_idle_overspeed_margin = get_longitudinal_no_lead_idle_overspeed_margin_kph() * CV.KPH_TO_MS
    self.no_lead_idle_decel_block_frames = int(get_longitudinal_no_lead_idle_decel_cooldown_s() / self.dt)
    self.no_brake_mode = get_slc_no_brake_mode()
    self.no_brake_release_gap = get_slc_no_brake_release_gap_kph() * CV.KPH_TO_MS
    self.no_brake_accel = get_slc_no_brake_accel()
    self.speed_limit_max_decel = get_slc_speed_limit_max_decel()

  def _update_lead_coast_qualification(self, sm, v_ego, reset_state, all_checks):
    leads = (sm['radarState'].leadOne, sm['radarState'].leadTwo)
    lead_present = tuple(lead.present for lead in leads)
    has_lead = any(lead_present)
    lead_appeared = any(present and not previous for present, previous in
                        zip(lead_present, self.coast_lead_present, strict=True))
    self.coast_lead_present = lead_present
    min_gap = lead_coast_min_distance(v_ego, sm['selfdriveState'].personality)
    raw_leads = tuple((lead.present, lead.dRel, lead.vRel, lead.aLeadK) for lead in leads)
    safe = all_checks(['radarState']) and self.coast_lead_gap.allows(raw_leads, v_ego, min_gap)
    if self.coast_lead_gap.time_gaps is None:
      safe &= all(not lead.present or (previous is not None and lead.dRel >= previous - 0.5)
                  for lead, previous in zip(leads, self.coast_lead_distances, strict=True))
    if self.longitudinal_idle and not safe:
      self.coast_lead_stable_time = 0.
    self.coast_lead_distances = tuple(lead.dRel if lead.present else None for lead in leads)

    if reset_state or lead_appeared:
      self.coast_lead_stable_time = 0.
      self.coast_lead_unsafe_frames = 0
      self.coast_lead_brake_frames = 0
    elif not safe:
      self.coast_lead_unsafe_frames += 1
      if self.coast_lead_unsafe_frames >= LEAD_COAST_UNSAFE_GRACE_FRAMES:
        self.coast_lead_stable_time = 0.
    else:
      self.coast_lead_unsafe_frames = 0
      self.coast_lead_stable_time = min(self.coast_lead_stable_time + self.dt, LEAD_COAST_REENTRY_STABLE_S)

    qualified = self.coast_lead_stable_time >= LEAD_COAST_REENTRY_STABLE_S
    return leads, raw_leads, has_lead, min_gap, safe and qualified

  def update(self, sm):
    LongitudinalPlannerSP.update(self, sm)
    self._update_slc_config()
    all_checks = getattr(sm, 'all_checks', lambda services=None: True)

    accel_coast = get_coast_accel(sm['carControl'].orientationNED[1]) if len(sm['carControl'].orientationNED) == 3 else 0.

    v_ego = sm['carState'].vEgo
    v_cruise_kph = min(sm['carState'].vCruise, V_CRUISE_MAX)
    v_cruise_raw = v_cruise_kph * CV.KPH_TO_MS
    v_cruise = v_cruise_raw
    if sm['controlsState'].forceDecel:
      v_cruise = 0.0

    long_control_off = sm['controlsState'].longControlState == LongCtrlState.off

    # Reset current state when not engaged, or user is controlling the speed
    reset_state = long_control_off if self.CP.openpilotLongitudinalControl else not sm['selfdriveState'].enabled
    # PCM cruise speed may be updated a few cycles later, check if initialized
    v_cruise_initialized = sm['carState'].vCruise != V_CRUISE_UNSET
    reset_state = reset_state or not v_cruise_initialized
    cruise_down_pressed = any(b.pressed and b.type in CRUISE_TARGET_DOWN_BUTTONS for b in sm['carState'].buttonEvents)
    cruise_up_pressed = any(b.pressed and b.type in CRUISE_TARGET_UP_BUTTONS for b in sm['carState'].buttonEvents)
    cruise_target_decreased = (
      v_cruise_initialized and
      self.v_cruise_kph_prev != V_CRUISE_UNSET and
      v_cruise_kph < self.v_cruise_kph_prev - CRUISE_TARGET_CHANGE_MIN_KPH
    )
    cruise_target_increased = (
      v_cruise_initialized and
      self.v_cruise_kph_prev != V_CRUISE_UNSET and
      v_cruise_kph > self.v_cruise_kph_prev + CRUISE_TARGET_CHANGE_MIN_KPH
    )

    if reset_state:
      self.v_desired_filter.x = v_ego
      self.output_a_target = np.clip(sm['carState'].aEgo, ACCEL_MIN, ACCEL_MAX)
      self.a_cruise = self.output_a_target

    # Prevent divergence, smooth in current v_ego
    self.v_desired_filter.x = max(0.0, self.v_desired_filter.update(v_ego))

    # No change cost when user is controlling the speed, or when standstill
    prev_accel_constraint = not (reset_state or sm['carState'].standstill)

    # Get new v_cruise and a_target from Smart Cruise Control and Speed Limit Assist
    v_cruise, self.output_a_target = LongitudinalPlannerSP.update_targets(self, sm, self.v_desired_filter.x, self.output_a_target, v_cruise)
    leads, raw_leads, has_lead, lead_coast_min_gap, lead_coast_allowed = \
      self._update_lead_coast_qualification(sm, v_ego, reset_state, all_checks)
    no_brake_release_gap = self.no_brake_release_gap
    # A temporary longitudinal override can coincide with a set-speed change.
    # Remember that target while still engaged; the idle safety gates keep N off
    # until the pedal is released and longitudinal control resumes.
    # Cancel takes priority over arming. Then release even a newly armed target
    # if already within its gap; the re-entry cooldown is tracked separately.
    if not sm['selfdriveState'].enabled or not v_cruise_initialized or cruise_up_pressed or cruise_target_increased:
      self.no_lead_idle_target = 0.
    elif v_cruise_initialized and (cruise_down_pressed or cruise_target_decreased):
      self.no_lead_idle_target = v_cruise_raw
    if self.no_lead_idle_target > 0. and v_ego <= self.no_lead_idle_target + no_brake_release_gap:
      self.no_lead_idle_target = 0.
    if reset_state or cruise_up_pressed or cruise_target_increased:
      self.longitudinal_idle_block_frames = max(self.longitudinal_idle_block_frames, LONGITUDINAL_IDLE_REENTRY_BLOCK_FRAMES)
    idle_reentry_blocked = self.longitudinal_idle_block_frames > 0
    speed_limit_source_active = self.source == SpeedLimitPlanSource.speedLimitAssist
    speed_limit_current_limit_decel = speed_limit_current_limit_decel_needed(
      self.sla.is_active or self.no_lead_idle_target > 0.,
      v_ego, self.resolver.speed_limit_final_last, self.no_lead_idle_overspeed_margin)
    approach_allowed = speed_limit_approach_allowed(
      self.sla.is_active, self.resolver.lower_lookahead_active, self.source,
      v_cruise, self.resolver.approach_speed_limit_final, speed_limit_current_limit_decel)
    # Track this approach even while another source temporarily blocks coast.
    # Otherwise SCC priority clears the release/cancel latch and re-arms N.
    approach_cancel = reset_state or cruise_up_pressed or cruise_target_increased or sm['carState'].gasPressed
    approach_active = self.speed_limit_approach.update(
      self.speed_limit_no_brake and self.resolver.lower_lookahead_active,
      self.resolver.approach_speed_limit_final, v_ego, no_brake_release_gap,
      cancel=approach_cancel,
    )
    approach_active &= approach_allowed
    # Releasing N finishes the slowdown, not the approach. Hold its release
    # speed until the map boundary instead of accelerating to the old zone.
    # Explicit cancellation and lost qualification clear the hold in update().
    approach_hold_speed = self.speed_limit_approach.hold_speed if approach_allowed else 0.
    if approach_hold_speed > 0.:
      v_cruise = min(v_cruise, approach_hold_speed)
    no_brake_for_speed_limit = approach_active and not idle_reentry_blocked and lead_coast_allowed and not has_lead
    # Only idle mode may coast behind a steady lead; fixed/dynamic overrides remain no-lead only.
    if self.no_brake_mode == "idle":
      no_brake_for_speed_limit = approach_active and not idle_reentry_blocked and lead_coast_allowed
    no_brake_for_speed_limit &= ((speed_limit_source_active or approach_allowed) and not speed_limit_current_limit_decel and
                                 not reset_state and not sm['controlsState'].forceDecel and
                                 not sm['carState'].brakePressed and not sm['carState'].gasPressed and
                                 all_checks(['modelV2', 'carState']))
    speed_limit_idle = (
      not idle_reentry_blocked and
      no_brake_for_speed_limit and
      v_ego > MIN_ALLOW_THROTTLE_SPEED and
      not sm['carState'].standstill and
      not sm['carState'].brakePressed and
      not sm['carState'].gasPressed and
      speed_limit_idle_active(v_ego, self.resolver.approach_speed_limit_final, no_brake_release_gap, self.no_brake_mode)
    )
    no_brake_accel = speed_limit_no_brake_accel_target(v_ego, self.resolver.approach_speed_limit_final, no_brake_release_gap,
                                                       self.no_brake_accel, self.no_brake_mode,
                                                       self.resolver.approach_distance, self.resolver.lookahead_speed_factor_down,
                                                       accel_coast, A_CRUISE_MIN)
    if no_brake_for_speed_limit:
      self.output_a_target = no_brake_accel

    self.mpc.set_weights(prev_accel_constraint, personality=sm['selfdriveState'].personality)
    if self.CP.openpilotLongitudinalControl:
      self.mpc.set_cur_state(self.v_desired_filter.x, self.output_a_target)
    else:
      self.mpc.set_cur_state(v_ego, sm['carState'].aEgo)
    self.mpc.update(sm['radarState'], personality=sm['selfdriveState'].personality)

    self.v_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC, self.mpc.v_solution)
    self.a_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC, self.mpc.a_solution)
    self.j_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC[:-1], self.mpc.j_solution)

    # TODO counter is only needed because radar is glitchy, remove once radar is gone
    self.fcw = self.mpc.crash_cnt > 2 and not sm['carState'].standstill
    if self.fcw:
      cloudlog.info("FCW triggered")

    # Save starting point for next iteration
    a_prev = self.output_a_target

    action_t =  self.CP.longitudinalActuatorDelay + DT_MDL
    output_a_target_mpc = get_accel_from_plan(self.v_desired_trajectory, self.a_desired_trajectory, CONTROL_N_T_IDX,
                                              action_t=action_t)
    output_should_stop_mpc = should_stop(v_ego, output_a_target_mpc)
    output_a_target_e2e = sm['modelV2'].action.desiredAcceleration
    output_should_stop_e2e = sm['modelV2'].action.shouldStop

    if no_brake_for_speed_limit:
      self.a_cruise = no_brake_accel
    else:
      self.a_cruise = get_cruise_accel(v_cruise, v_ego, self.a_cruise, self.dt,
                                       max_accel=ACCEL_MAX if self.longitudinal_e2e_enabled else None)
    cruise_should_stop = should_stop(v_ego, self.a_cruise)

    candidates = [(output_a_target_mpc, self.mpc.source, output_should_stop_mpc),
                  (self.a_cruise, LongitudinalPlanSource.cruise, cruise_should_stop)]
    if self.longitudinal_e2e_enabled:
      output_a_target_e2e = self.accel_boost.update(sm, output_a_target_e2e, output_a_target_mpc, self.a_cruise)
      candidates.append((output_a_target_e2e, LongitudinalPlanSource.e2e, output_should_stop_e2e))

    output_a_target, selected_source, _ = min(candidates, key=lambda c: c[0])
    any_should_stop = any(should_stop for _, _, should_stop in candidates)
    speed_limit_source_active = self.source == SpeedLimitPlanSource.speedLimitAssist
    if speed_limit_current_limit_decel:
      self.longitudinal_idle_block_frames = max(self.longitudinal_idle_block_frames, self.no_lead_idle_decel_block_frames)
    idle_blocked = self.longitudinal_idle_block_frames > 0
    intentional_no_lead_decel = (
      self.no_lead_idle_target > 0. or
      (speed_limit_source_active and not speed_limit_current_limit_decel and
       not self.speed_limit_approach.released and
       v_ego > self.resolver.speed_limit_final_last + no_brake_release_gap)
    )
    normal_decel_idle = (
      not idle_blocked and
      no_lead_normal_decel_idle_active(self.no_lead_decel_mode, intentional_no_lead_decel,
                                       (selected_source == LongitudinalPlanSource.cruise or self.longitudinal_idle) and
                                       self.source in (SpeedLimitPlanSource.cruise, SpeedLimitPlanSource.speedLimitAssist),
                                       output_a_target, self.no_lead_idle_min_decel, has_lead, any_should_stop,
                                       lead_coast_allowed=lead_coast_allowed) and
      v_ego > MIN_ALLOW_THROTTLE_SPEED and
      not sm['carState'].standstill and
      not sm['carState'].brakePressed and
      not sm['carState'].gasPressed
    )
    # MPC gap corrections do not cancel an active coast. Before entry, keep
    # the existing brake gate so we do not enter N during a braking maneuver.
    if not self.longitudinal_idle and has_lead and output_a_target_mpc < LEAD_COAST_SOFT_BRAKE_ACCEL:
      self.coast_lead_brake_frames = min(self.coast_lead_brake_frames + 1, LEAD_COAST_SOFT_BRAKE_FRAMES)
    else:
      self.coast_lead_brake_frames = 0
    lead_braking = not self.longitudinal_idle and has_lead and (
      output_a_target_mpc <= LEAD_COAST_HARD_BRAKE_ACCEL or self.coast_lead_brake_frames >= LEAD_COAST_SOFT_BRAKE_FRAMES)
    if lead_braking:
      self.coast_lead_stable_time = 0.
      lead_coast_allowed = False
    # A qualified lower-limit approach owns speed-only coasting in experimental
    # mode too. Model stop requests, FCW and the independent lead gates still
    # cancel N; ordinary model control resumes as soon as the approach releases.
    e2e_blocks_idle = selected_source == LongitudinalPlanSource.e2e and not speed_limit_idle
    idle_safe = (lead_coast_allowed and not reset_state and not sm['controlsState'].forceDecel and not self.fcw and not any_should_stop and
                 not e2e_blocks_idle and all_checks(['radarState', 'modelV2', 'carState']))
    self.longitudinal_idle = self.coast_lead_gap.update(idle_safe and (speed_limit_idle or normal_decel_idle),
                                                       raw_leads, v_ego, lead_coast_min_gap)
    logger = getattr(self, 'decision_logger', None)
    if logger is not None:
      # Log after the final idle gate, so replay distinguishes a detected
      # approach from a coast request that was blocked before CAN handoff.
      idle_changed = self.longitudinal_idle != getattr(self, '_logged_longitudinal_idle', False)
      logger.log("slc_coast", lambda: (self.longitudinal_idle, speed_limit_idle, approach_allowed, e2e_blocks_idle,
                                      any_should_stop, self.fcw, lead_coast_allowed, reset_state,
                                      self.speed_limit_approach.released, approach_hold_speed, approach_cancel), lambda: {
        "resolver_decision_mono_time_ns": getattr(self.resolver, 'last_decision_event_ns', None),
        "idle_active": self.longitudinal_idle,
        "qualified_approach_requested": speed_limit_idle,
        "approach_allowed": approach_allowed,
        "approach_released": self.speed_limit_approach.released,
        "approach_hold_speed_mps": approach_hold_speed,
        "approach_cancel_requested": approach_cancel,
        "ego_mps": v_ego,
        "approach_release_gap_mps": no_brake_release_gap,
        "approach_target_mps": self.resolver.approach_speed_limit_final,
        "e2e_selected": selected_source == LongitudinalPlanSource.e2e,
        "e2e_blocks_idle": e2e_blocks_idle,
        "model_acceleration_mps2": output_a_target_e2e,
        "stop_requested": any_should_stop,
        "fcw": self.fcw,
        "lead_coast_allowed": lead_coast_allowed,
        "reset_state": reset_state,
        "idle_reentry_blocked": idle_reentry_blocked,
      }, force=idle_changed)
      self._logged_longitudinal_idle = self.longitudinal_idle
    if self.longitudinal_idle:
      output_a_target = 0.
    cap_speed_limit_decel = (
      not self.longitudinal_idle and
      not no_brake_for_speed_limit and
      selected_source == LongitudinalPlanSource.cruise and
      self.source == SpeedLimitPlanSource.speedLimitAssist
    )
    output_a_target = limit_speed_limit_decel_target(output_a_target, cap_speed_limit_decel,
                                                     has_lead, self.speed_limit_max_decel)
    self.mpc.source = selected_source
    self.output_should_stop = any_should_stop
    self.output_a_target = np.clip(output_a_target, ACCEL_MIN, ACCEL_MAX)

    self.v_desired_filter.x = self.v_desired_filter.x + self.dt * (self.output_a_target + a_prev) / 2.0
    if self.longitudinal_idle_block_frames > 0:
      self.longitudinal_idle_block_frames -= 1
    self.v_cruise_kph_prev = v_cruise_kph if v_cruise_initialized else V_CRUISE_UNSET

  def publish(self, sm, pm):
    plan_send = messaging.new_message('longitudinalPlan')

    plan_send.valid = sm.all_checks()

    longitudinalPlan = plan_send.longitudinalPlan
    longitudinalPlan.modelMonoTime = sm.logMonoTime['modelV2']
    longitudinalPlan.processingDelay = (plan_send.logMonoTime / 1e9) - sm.logMonoTime['modelV2']
    longitudinalPlan.solverExecutionTime = self.mpc.solve_time

    longitudinalPlan.speeds = self.v_desired_trajectory.tolist()
    longitudinalPlan.accels = self.a_desired_trajectory.tolist()
    longitudinalPlan.jerks = self.j_desired_trajectory.tolist()

    longitudinalPlan.hasLead = sm['radarState'].leadOne.present
    longitudinalPlan.longitudinalPlanSource = self.mpc.source
    longitudinalPlan.fcw = self.fcw

    longitudinalPlan.aTarget = float(self.output_a_target)
    longitudinalPlan.accelBoost = float(self.accel_boost.total_boost)
    longitudinalPlan.shouldStop = bool(self.output_should_stop)
    longitudinalPlan.allowBrake = True

    pm.send('longitudinalPlan', plan_send)

    self.publish_longitudinal_plan_sp(sm, pm)
