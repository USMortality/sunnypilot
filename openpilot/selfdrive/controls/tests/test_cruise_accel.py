import pytest

from openpilot.selfdrive.controls.lib.cruise_accel import get_cruise_accel, get_max_accel


@pytest.mark.parametrize('speed,expected', [(0., 1.2), (2.8, 1.1), (10., .7), (25., .45), (40., .35), (50., .35),
                                           (6.4, .9), (17.5, .575), (32.5, .4)])
def test_final_ben_speed_dependent_comfort_ceiling(speed, expected):
  assert get_max_accel(speed) == pytest.approx(expected)
  acceleration = 0.
  # Large set-speed increase must saturate at the comfort ceiling, not 2 m/s².
  for _ in range(500):
    acceleration = get_cruise_accel(speed + 20., speed, acceleration, .05)
    assert acceleration <= expected + 1e-9
  assert acceleration == pytest.approx(expected)


@pytest.mark.parametrize('speed,jerk', [(0., 1.2), (2.8, 1.1), (10., .8), (25., .5), (40., .3)])
def test_final_ben_acceleration_ramp_is_restored(speed, jerk):
  assert get_cruise_accel(speed + 20., speed, 0., .05) == pytest.approx(jerk * .05)


@pytest.mark.parametrize('speed', [0., 2.8, 10., 25., 40.])
def test_prior_high_acceleration_cannot_bypass_ceiling(speed):
  assert get_cruise_accel(speed + 20., speed, 2., .05) == pytest.approx(get_max_accel(speed))


def test_rising_speed_keeps_output_inside_falling_comfort_ceiling():
  acceleration = 1.2
  for tick in range(1000):
    speed = tick * .05
    acceleration = get_cruise_accel(60., speed, acceleration, .05)
    assert acceleration <= get_max_accel(speed) + 1e-9


def test_experimental_explicit_ceiling_preserves_existing_behavior():
  acceleration = 0.
  for _ in range(500):
    acceleration = get_cruise_accel(50., 25., acceleration, .05, max_accel=2.)
  assert acceleration == pytest.approx(2.)


def test_braking_request_is_not_limited_by_positive_acceleration_ceiling():
  acceleration = 0.
  for _ in range(100):
    acceleration = get_cruise_accel(10., 25., acceleration, .05)
  assert acceleration == pytest.approx(-.5)
