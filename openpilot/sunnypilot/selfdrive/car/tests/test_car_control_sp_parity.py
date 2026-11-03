"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""


def test_can_facing_idle_fields_exist_in_pinned_opendbc():
  from openpilot.cereal import messaging
  from openpilot.selfdrive.car.helpers import convert_carControlSP
  from opendbc.car import structs

  dat = messaging.new_message('carControlSP')
  required = {'longitudinalIdle', 'leadCoastMinDistance', 'leadCoastTimeGaps'}
  assert required <= set(structs.CarControlSP.__dataclass_fields__)
  converted = convert_carControlSP(dat.carControlSP)
  assert converted.mads is not None


def test_convert_car_control_sp_accepts_saved_coast_gaps():
  from openpilot.cereal import messaging
  from openpilot.selfdrive.car.helpers import convert_carControlSP

  dat = messaging.new_message('carControlSP')
  dat.carControlSP.longitudinalIdle = True
  dat.carControlSP.leadCoastMinDistance = 20.
  # Preserve the exact boundary through serialization and the card conversion.
  gaps = [2.1234567890123, 0.]
  dat.carControlSP.leadCoastTimeGaps = gaps
  restored = messaging.log_from_bytes(dat.to_bytes())
  converted = convert_carControlSP(restored.carControlSP)
  assert converted.longitudinalIdle
  assert converted.leadCoastMinDistance == 20.
  assert converted.leadCoastTimeGaps == gaps
