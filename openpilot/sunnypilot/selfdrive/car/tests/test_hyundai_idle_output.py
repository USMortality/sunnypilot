from types import SimpleNamespace as NS

import pytest

from openpilot.cereal import messaging
from openpilot.selfdrive.car.helpers import convert_carControlSP
from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, structs
from opendbc.car.hyundai import hyundaicanfd
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags
from opendbc.sunnypilot.car.hyundai.lead_data_ext import LeadCoastGap


@pytest.fixture
def can_output(monkeypatch):
  # Exercise the real card conversion, controller handoff, CAN packer and
  # decoder. Only unrelated lateral/cluster messages are omitted.
  monkeypatch.setattr(hyundaicanfd, 'create_steering_messages', lambda *args: [])
  monkeypatch.setattr(hyundaicanfd, 'create_fca_warning_light', lambda *args: [])
  dbc = DBC[CAR.KIA_SPORTAGE_5TH_GEN][Bus.pt]
  controller = CarController.__new__(CarController)
  controller.CP = NS(flags=HyundaiFlags.CANFD, openpilotLongitudinalControl=True)
  controller.CAN = NS(ECAN=0)
  controller.frame = 2
  controller.lkas_icon = 0
  controller.packer = CANPacker(dbc)
  controller.coast_lead_gap = LeadCoastGap()
  controller.accel_last = 0.
  controller.object_gap = 0
  controller.lead_distance = controller.lead_rel_speed = 0.
  controller.lead_visible = False
  controller.tuning = NS(stopping=False, actual_accel=-.2, jerk_lower=1., jerk_upper=1.)
  cc = structs.CarControl()
  cc.enabled = cc.longActive = True
  cs = NS(out=NS(vEgo=20.), main_cruise_enabled=True)
  request = messaging.new_message('carControlSP')
  request.carControlSP.longitudinalIdle = True
  request.carControlSP.leadCoastMinDistance = 20.
  request.carControlSP.leadCoastTimeGaps = [0., 0.]
  parser = CANParser(dbc, [('SCC_CONTROL', 50)], 0)

  def send(stopping=False):
    payload = request.to_bytes()
    request.clear_write_flag()
    restored = messaging.log_from_bytes(payload)
    converted = convert_carControlSP(restored.carControlSP)
    messages = controller.create_canfd_msgs(False, 0, 70., -.2, stopping, cc.hudControl, cs, cc, converted)
    parser.update([1_000_000_000, messages])
    return dict(parser.vl['SCC_CONTROL'])
  return controller, cc, cs, request.carControlSP, send


def test_idle_request_reaches_actual_can_output(can_output):
  _, _, _, request, send = can_output
  values = send()
  assert values['ACCMode'] == 0
  assert values['aReqRaw'] == pytest.approx(0.)
  assert values['aReqValue'] == pytest.approx(0.)
  assert values['StopReq'] == 0
  request.longitudinalIdle = False
  values = send()
  assert values['ACCMode'] == 1
  assert values['aReqRaw'] == pytest.approx(-.2)


@pytest.mark.parametrize('blocker', ['disabled', 'long_inactive', 'gas_override', 'stopping', 'tuning_stop', 'raw_lead', 'missing_gaps', 'standstill'])
def test_idle_can_output_yields_to_control_and_lead_gates(can_output, blocker):
  controller, cc, cs, request, send = can_output
  if blocker == 'disabled':
    cc.enabled = False
  elif blocker == 'long_inactive':
    cc.longActive = False
  elif blocker == 'gas_override':
    cc.cruiseControl.override = True
  elif blocker == 'tuning_stop':
    controller.tuning.stopping = True
  elif blocker == 'raw_lead':
    request.leadOne.status = True
    request.leadOne.dRel = 5.
    request.leadOne.vRel = -1.
  elif blocker == 'missing_gaps':
    request.leadCoastTimeGaps = []
  elif blocker == 'standstill':
    cs.out.vEgo = 0.
  values = send(stopping=blocker == 'stopping')
  expected_mode = 0 if blocker == 'disabled' else 2 if blocker == 'gas_override' else 1
  assert values['ACCMode'] == expected_mode
  assert values['aReqRaw'] == pytest.approx(-.2)


def test_raw_lead_rejection_cannot_rebase_same_idle_request(can_output):
  _, _, _, request, send = can_output
  request.leadCoastTimeGaps = [3., 0.]
  request.leadOne.status = True
  request.leadOne.dRel = 60.
  assert send()['ACCMode'] == 0
  request.leadOne.dRel = 53.
  assert send()['ACCMode'] == 1
  request.leadOne.dRel = 60.
  assert send()['ACCMode'] == 1
  request.longitudinalIdle = False
  assert send()['ACCMode'] == 1
  request.longitudinalIdle = True
  assert send()['ACCMode'] == 0
