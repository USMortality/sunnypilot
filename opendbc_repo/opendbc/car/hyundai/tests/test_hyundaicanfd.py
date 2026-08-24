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
