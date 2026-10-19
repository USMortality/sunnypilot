from opendbc.car.hyundai.hyundaicanfd import longitudinal_idle_allowed
from opendbc.sunnypilot.car.hyundai.lead_data_ext import CanFdLeadData


def lead(visible=False):
  return CanFdLeadData(0, 0., 0., visible)


def test_longitudinal_idle_allowed_without_lead():
  assert longitudinal_idle_allowed(True, False, False, lead(False))


def test_longitudinal_idle_rejected_when_disabled():
  assert not longitudinal_idle_allowed(False, False, False, lead(False))


def test_longitudinal_idle_rejected_when_stopping():
  assert not longitudinal_idle_allowed(True, True, False, lead(False))


def test_longitudinal_idle_rejected_on_gas_override():
  assert not longitudinal_idle_allowed(True, False, True, lead(False))


def test_longitudinal_idle_rejected_with_lead():
  assert not longitudinal_idle_allowed(True, False, False, lead(True))


def test_longitudinal_idle_with_approved_steady_lead():
  assert longitudinal_idle_allowed(True, False, False, lead(True), lead_coast_allowed=True)
  assert not longitudinal_idle_allowed(True, True, False, lead(True), lead_coast_allowed=True)
  assert not longitudinal_idle_allowed(True, False, True, lead(True), lead_coast_allowed=True)


def test_lead_coasting_requires_gap_and_steady_speed():
  from opendbc.sunnypilot.car.hyundai.lead_data_ext import lead_allows_coasting
  assert lead_allows_coasting(True, 50., 0., 0., 38.)
  assert not lead_allows_coasting(True, 35., 0., 0., 38.)
  assert not lead_allows_coasting(True, 50., -0.5, 0., 38.)
  assert not lead_allows_coasting(True, 50., 0., -0.5, 38.)
  assert not lead_allows_coasting(True, float('nan'), 0., 0., 38.)


def test_idle_output_restores_active_acc_and_preserves_stop_requests():
  from types import SimpleNamespace as NS
  from opendbc.car.hyundai.hyundaicanfd import create_acc_control

  packer = NS(make_can_msg=lambda name, bus, values: values)
  tuning = NS(stopping=False, actual_accel=0.4, jerk_lower=1., jerk_upper=1.)

  def output(idle):
    return create_acc_control(packer, NS(ECAN=0), True, 0., 0.4, False, False, 51., NS(leadDistanceBars=2),
                              lead(True), True, tuning, longitudinal_idle=idle, lead_coast_allowed=True)

  assert output(True)['ACCMode'] == 0
  assert output(True)['aReqRaw'] == 0.
  assert output(False)['ACCMode'] == 1
  assert output(False)['aReqRaw'] == 0.4
  tuning.stopping = True
  assert output(True)['ACCMode'] == 1
  assert output(True)['StopReq'] == 1


def test_saved_can_headway_ignores_decel_and_holds_fixed_baseline():
  from opendbc.sunnypilot.car.hyundai.lead_data_ext import LeadCoastGap
  gap = LeadCoastGap()
  absent = (False, 0., 0., 0.)
  assert gap.update(True, ((True, 50., 0., 0.), absent), 20., 38.)
  # 2.5 s entry headway: a faster ego and a slightly closing lead still have
  # more than 2.25 s, despite the raw speed/acceleration entry gates failing.
  assert gap.update(True, ((True, 55., -0.5, -0.8), absent), 22., 41.8)
  assert gap.update(True, ((True, 46., -0.5, -0.8), absent), 20., 38.)
  assert not gap.update(True, ((True, 45., 0., 0.), absent), 20., 38.)
  # A rebound cannot silently restart N while the request is still asserted.
  assert not gap.update(True, ((True, 50., 0., 0.), absent), 20., 38.)
  assert not gap.update(False, ((True, 50., 0., 0.), absent), 20., 38.)
  assert gap.update(True, ((True, 50., 0., 0.), absent), 20., 38.)


def test_can_new_lead_and_invalid_data_reject_saved_coast():
  from opendbc.sunnypilot.car.hyundai.lead_data_ext import LeadCoastGap
  gap = LeadCoastGap()
  absent = (False, 0., 0., 0.)
  assert gap.update(True, (absent, absent), 20., 38.)
  assert not gap.update(True, ((True, 60., 0., 0.), absent), 20., 38.)
  gap.update(False, (absent, absent), 20., 38.)
  assert gap.update(True, ((True, 50., 0., 0.), absent), 20., 38.)
  assert not gap.update(True, ((True, float('nan'), 0., 0.), absent), 20., 38.)


def test_can_uses_planner_baseline_instead_of_new_raw_sample():
  from opendbc.sunnypilot.car.hyundai.lead_data_ext import LeadCoastGap
  gap = LeadCoastGap()
  absent = (False, 0., 0., 0.)
  # Planner entered at 50 m / 20 m/s = 2.5 s. The later CAN sample is
  # already slowing, but still above the planner's 2.25 s release boundary.
  assert gap.update(True, ((True, 46., -0.5, -0.8), absent), 20., 38., saved_time_gaps=[2.5, 0.])
  assert gap.saved_time_gaps == [2.5, 0.]
  assert not gap.update(True, ((True, 45., 0., 0.), absent), 20., 38., saved_time_gaps=[2.5, 0.])
  assert not gap.update(True, ((True, 50., 0., 0.), absent), 20., 38., saved_time_gaps=[2.5, 0.])


def test_can_rejects_missing_or_invalid_planner_baseline():
  from opendbc.sunnypilot.car.hyundai.lead_data_ext import LeadCoastGap
  leads = ((True, 50., 0., 0.), (False, 0., 0., 0.))
  for baseline in ([], [2.5], [2.5, 0., 0.], [float('nan'), 0.], [float('inf'), 0.], [-2.5, 0.]):
    gap = LeadCoastGap()
    assert not gap.update(True, leads, 20., 38., saved_time_gaps=baseline)
