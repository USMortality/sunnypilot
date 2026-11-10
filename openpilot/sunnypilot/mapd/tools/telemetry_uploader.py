"""Opt-in read-only bridge from comma messages to the private SLC webapp.

The webapp is Nuxt/TypeScript. This uses the comma's existing Python runtime
and does not serve HTTP. Remove CONFIG to disable.
"""
import fcntl
import gzip
import json
import math
import threading
import time
import uuid
from collections import deque
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

CONFIG = Path('/data/sunnypilot/slc-telemetry.json')
EVENTS = {'slc_observation', 'slc_decision', 'slc_application', 'slc_coast', 'slc_cruise_initialization'}


def clean(value):
  if isinstance(value, float) and not math.isfinite(value):
    return None
  if isinstance(value, dict):
    # Older decision loggers stringify numpy booleans. Keep their queued
    # decisions compatible with the server's strict boolean schema.
    return {key: (item == 'True' if key == 'lower_lookahead_active' and isinstance(item, str) and item in ('True', 'False') else clean(item))
            for key, item in value.items()}
  if isinstance(value, list):
    return [clean(item) for item in value]
  return value


class NoRedirect(HTTPRedirectHandler):
  def redirect_request(self, *_args, **_kwargs):
    return None


def location_sample(sm, now, unix_now):
  """Prefer a valid localizer; use fresh GNSS directly while it is asleep."""
  llk_name, gps_name = 'liveLocationKalman', 'gpsLocation'

  def fresh(name):
    return sm.seen[name] and 0 <= now - sm.logMonoTime[name] * 1e-9 < 3.

  llk = sm[llk_name]
  if fresh(llk_name) and sm.valid[llk_name] and llk.positionGeodetic.valid and llk.gpsOK and str(llk.status) == 'valid':
    values = llk.positionGeodetic.value
    if len(values) >= 2 and math.isfinite(values[0]) and math.isfinite(values[1]) and abs(values[0]) <= 90 and abs(values[1]) <= 180:
      return {'event': 'location', 'position': {'latitude': values[0], 'longitude': values[1]},
              'valid': True, 'gps_ok': True, 'status': 'valid', 'position_source': 'localizer'}, sm.logMonoTime[llk_name]
  if fresh(gps_name):
    gps = sm[gps_name]
    speed = getattr(gps, 'speed', None)
    valid = (sm.valid[gps_name] and gps.hasFix and math.isfinite(gps.latitude) and math.isfinite(gps.longitude) and
             abs(gps.latitude) <= 90 and abs(gps.longitude) <= 180 and abs(unix_now - gps.unixTimestampMillis * .001) < 10.)
    return {'event': 'location', 'position': {'latitude': gps.latitude, 'longitude': gps.longitude} if valid else None,
            'valid': bool(valid), 'gps_ok': bool(valid), 'status': 'gps_fix' if valid else 'waiting_for_gps_fix',
            'ego_kph': speed * 3.6 if valid and isinstance(speed, (int, float)) and math.isfinite(speed) and speed >= 0 else None,
            'position_source': 'gps', 'fix_time_unix_s': gps.unixTimestampMillis * .001}, sm.logMonoTime[gps_name]
  return None


def upload(endpoint, token, source, events):
  body = gzip.compress(json.dumps({'source': source, 'events': events}, allow_nan=False).encode())
  request = Request(endpoint, data=body, method='POST', headers={
    'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json', 'Content-Encoding': 'gzip',
    'User-Agent': 'sunnypilot-slc-telemetry/1.0',
  })
  with build_opener(NoRedirect()).open(request, timeout=10) as response:
    if response.status != 204:
      raise OSError('telemetry not acknowledged')


def batch_prefix(pending, limit_bytes=512 * 1024):
  """Keep retries containing road geometry below the receiver's body limit."""
  selected, size = [], 0
  for event in pending:
    encoded = len(json.dumps(event, allow_nan=False).encode())
    if selected and (size + encoded > limit_bytes or len(selected) >= 1000):
      break
    selected.append(event)
    size += encoded
  return selected


def run(config):
  import openpilot.cereal.messaging as messaging
  from openpilot.common.swaglog import cloudlog
  from openpilot.common.params import Params

  endpoint, token = config['endpoint'], config['token']
  url = urlsplit(endpoint)
  if url.scheme != 'https' or not url.hostname or url.username or url.password or not token:
    raise ValueError('telemetry requires an HTTPS endpoint and upload token')
  pending, lock, stop = deque(maxlen=3000), threading.Lock(), threading.Event()
  source, sequence = uuid.uuid4().hex, 0

  def add(payload, mono_ns):
    nonlocal sequence
    sequence += 1
    # Preserve capture time across delayed delivery; backlog must not look live.
    age = max(0., time.monotonic() - mono_ns * 1e-9)
    event = clean({**payload, 'id': sequence, 'observed_at_unix_s': time.time() - age})  # noqa: TID251 — shared UTC across hosts.
    with lock:
      pending.append(event)

  def collect():
    while not stop.is_set():
      try:
        sm = messaging.SubMaster(['liveLocationKalman', 'gpsLocation', 'carState'])
        logs = messaging.sub_sock('logMessage')
        while not stop.wait(1.):
          sm.update(0)
          if sm.updated['liveLocationKalman'] or sm.updated['gpsLocation']:
            sample = location_sample(sm, time.monotonic(), time.time())  # noqa: TID251 — compare GNSS UTC timestamp.
            if sample is not None:
              payload, stamp = sample
              if sm.alive['carState'] and sm.valid['carState']:
                payload['ego_kph'] = float(sm['carState'].vEgo) * 3.6
              add(payload, stamp)
          for message in messaging.drain_sock(logs):
            try:
              record = json.loads(message.logMessage)
              payload = record.get('msg') if isinstance(record, dict) else None
              if isinstance(payload, dict) and payload.get('event') in EVENTS:
                add(payload, message.logMonoTime)
            except (ValueError, TypeError):
              continue
      except Exception:
        cloudlog.warning('SLC telemetry subscription interrupted; retrying')
        stop.wait(5.)

  # Location services sleep while parked. Show the saved position as explicitly
  # invalid/undated until real LLK messages arrive; never label it a live fix.
  try:
    cached = json.loads(Params().get('LastGPSPositionLLK') or '{}')
    position = {'latitude': cached['latitude'], 'longitude': cached['longitude']}
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in position.values()):
      position = None
  except (ValueError, TypeError, KeyError):
    position = None
  add({'event': 'location', 'position': position, 'valid': False, 'gps_ok': False,
       'status': 'cached_position_time_unknown'}, time.monotonic_ns())

  threading.Thread(target=collect, daemon=True).start()
  delay = 2.
  try:
    while not stop.wait(delay):
      if not CONFIG.is_file():
        return
      with lock:
        events = batch_prefix(pending)
      if not events:
        continue
      try:
        upload(endpoint, token, source, events)
      except Exception:
        # Back off during outages. Never reset the modem or block controls for
        # diagnostic delivery. No URL, token or raw response is logged.
        delay = min(60., delay * 2.)
      else:
        with lock:
          while pending and pending[0]['id'] <= events[-1]['id']:
            pending.popleft()
        delay = 2.
  finally:
    stop.set()


def main():
  # A manually started bridge and manager must never upload in parallel.
  with open('/tmp/slc-telemetry.lock', 'w') as lock:
    try:
      fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
      return
    run(json.loads(CONFIG.read_text()))


if __name__ == '__main__':
  main()
