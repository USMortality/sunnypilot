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
  assert lead_allows_coasting(True, 50., 0., 0., 20.)
  assert not lead_allows_coasting(True, 40., 0., 0., 20.)
  assert not lead_allows_coasting(True, 50., -0.5, 0., 20.)
  assert not lead_allows_coasting(True, 50., 0., -0.5, 20.)
  assert not lead_allows_coasting(True, float('nan'), 0., 0., 20.)


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
