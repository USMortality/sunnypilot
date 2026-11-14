"""Cruise acceleration and jerk limits, independent of the native MPC solver."""
import numpy as np

# Breakpoints are in m/s and correspond to 0, 10, 36, 90 and 144 km/h.
A_CRUISE_MAX_BP = [0., 2.8, 10., 25., 40.]
A_CRUISE_MAX_VALS = [1.4, 1.3, 0.7, 0.45, 0.35]
J_CRUISE_VALS = [1.2, 1.1, 0.8, 0.5, 0.3]
A_CRUISE_MIN = -0.5


def get_max_accel(v_ego):
  return float(np.interp(v_ego, A_CRUISE_MAX_BP, A_CRUISE_MAX_VALS))


def get_cruise_accel(v_cruise, v_ego, a_cruise_prev, dt, max_accel=None):
  # Normal cruise uses the comfort curve. Experimental control may explicitly
  # supply its existing higher ceiling; its model/lead arbitration is unchanged.
  ceiling = get_max_accel(v_ego) if max_accel is None else max_accel
  target_accel = np.clip(v_cruise - v_ego, A_CRUISE_MIN, ceiling)
  jerk = np.interp(v_ego, A_CRUISE_MAX_BP, J_CRUISE_VALS)
  target_accel = float(np.clip(target_accel, a_cruise_prev - jerk * dt, a_cruise_prev + jerk * dt))
  # An inherited acceleration (e.g. after pedal override), or a decreasing
  # speed-dependent ceiling, must not let the jerk ramp exceed the ceiling.
  return min(target_accel, ceiling)
