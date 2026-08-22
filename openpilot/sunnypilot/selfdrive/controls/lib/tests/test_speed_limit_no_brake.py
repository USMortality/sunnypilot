from openpilot.sunnypilot.selfdrive.controls.lib.longitudinal_planner import speed_limit_no_brake_active


def test_speed_limit_no_brake_requires_lower_lookahead_active():
  assert speed_limit_no_brake_active(True, True, False)
  assert not speed_limit_no_brake_active(True, False, False)


def test_speed_limit_no_brake_disabled_with_lead():
  assert not speed_limit_no_brake_active(True, True, True)


def test_speed_limit_no_brake_disabled_by_config():
  assert not speed_limit_no_brake_active(False, True, False)
