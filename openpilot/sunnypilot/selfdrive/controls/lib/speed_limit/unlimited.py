"""Separate unrestricted road signs from the advisory planning speed."""
import math

from openpilot.common.constants import CV

UNLIMITED_CAR_KPH = 253.
UNLIMITED_TARGET_MS = 130. * CV.KPH_TO_MS


def is_unlimited_car_limit(speed_ms):
  return math.isclose(speed_ms * CV.MS_TO_KPH, UNLIMITED_CAR_KPH, abs_tol=.1)
