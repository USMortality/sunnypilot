"""Rate-limited SLC audit events in the normal logMessage/rlog stream."""
import math
import time
from numbers import Integral, Real

from openpilot.common.constants import CV
from openpilot.common.swaglog import cloudlog
from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit.slc_config import get_slc_decision_logging

EVENTS = frozenset(("slc_observation", "slc_decision", "slc_application", "slc_cruise_initialization", "slc_coast"))
HEARTBEAT_S = 5.0
MIN_EVENT_INTERVAL_S = .5


def kph(speed):
  return round(float(speed) * CV.MS_TO_KPH, 1) if math.isfinite(float(speed)) else None


def message_info(sm, service):
  try:
    return {
      "mono_time_ns": int(getattr(sm, "logMonoTime", {}).get(service, 0)),
      "valid": bool(getattr(sm, "valid", {}).get(service, False)),
    }
  except (AttributeError, TypeError, ValueError):
    return {"mono_time_ns": 0, "valid": False}


def _json_value(value):
  if value is None or isinstance(value, (str, bool)):
    return value[:256] if isinstance(value, str) else value
  if isinstance(value, Integral):
    return int(value)
  if isinstance(value, Real):
    return float(value) if math.isfinite(value) else None
  if isinstance(value, dict):
    return {str(k): _json_value(v) for k, v in value.items()}
  if isinstance(value, (list, tuple)):
    return [_json_value(v) for v in value]
  return str(value)[:256]


class SpeedLimitDecisionLogger:
  def __init__(self, emit=None, clock=time.monotonic, enabled=None):
    self.emit = emit if emit is not None else cloudlog.event
    self.clock = clock
    self.enabled = enabled if enabled is not None else get_slc_decision_logging
    self._next_config_check = -math.inf
    self._enabled = False
    self._last = {}

  def log(self, event, key, context, force=False):
    # Logging and context construction must never interrupt control or publishing.
    try:
      now = self.clock()
      if now >= self._next_config_check:
        self._next_config_check = now + HEARTBEAT_S
        self._enabled = bool(self.enabled())
      if not self._enabled:
        self._last.clear()
        return
      key = key() if callable(key) else key
      previous, stamp = self._last.get(event, (None, -math.inf))
      changed = previous != key
      if not force and ((not changed and now - stamp < HEARTBEAT_S) or (changed and now - stamp < MIN_EVENT_INTERVAL_S)):
        return
      self._last[event] = (key, now)
      payload = context() if callable(context) else context
      stamp_ns = int(now * 1e9)
      self.emit(event, schema_version=1, decision_mono_time_ns=stamp_ns,
                trigger="forced" if force else "change" if changed else "heartbeat", **_json_value(payload))
      return stamp_ns
    except Exception:
      pass
