import gzip
import json
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError
from types import SimpleNamespace as NS

import pytest

from openpilot.sunnypilot.mapd.tools.telemetry_uploader import batch_prefix, cached_corridors, clean, location_sample, upload


def test_nonfinite_gps_values_are_strict_json():
  assert clean({'position': [float('nan'), 8.], 'speed': float('inf')}) == {'position': [None, 8.], 'speed': None}


@pytest.mark.parametrize('value,expected', [('True', True), ('False', False), (True, True), (False, False)])
def test_legacy_lookahead_boolean_does_not_block_uploads(value, expected):
  event = clean({'lower_lookahead_active': value, 'reason': 'True'})
  assert event['lower_lookahead_active'] is expected
  assert event['reason'] == 'True'


class LocationMessages(dict):
  def __init__(self):
    super().__init__(liveLocationKalman=NS(positionGeodetic=NS(valid=True, value=[49.071, 8.475]), gpsOK=True, status='valid'),
                     gpsLocation=NS(latitude=49.104374, longitude=8.470916, speed=12., hasFix=True, unixTimestampMillis=1793796000000))
    self.seen = {'liveLocationKalman': False, 'gpsLocation': True}
    self.valid = {'liveLocationKalman': True, 'gpsLocation': True}
    self.logMonoTime = {'liveLocationKalman': 100_000_000_000, 'gpsLocation': 100_000_000_000}


def test_parked_location_uses_fresh_gps_instead_of_old_localizer():
  messages = LocationMessages()
  payload, stamp = location_sample(messages, 101., 1793796001.)
  assert payload['valid']
  assert payload['position'] == {'latitude': 49.104374, 'longitude': 8.470916}
  assert payload['position_source'] == 'gps'
  assert payload['ego_kph'] == pytest.approx(43.2)
  assert stamp == messages.logMonoTime['gpsLocation']


def test_driving_prefers_valid_localizer_and_recovers_from_invalid_localizer():
  messages = LocationMessages()
  messages.seen['liveLocationKalman'] = True
  assert location_sample(messages, 101., 1793796001.)[0]['position_source'] == 'localizer'
  messages['liveLocationKalman'].gpsOK = False
  assert location_sample(messages, 101., 1793796001.)[0]['position_source'] == 'gps'


@pytest.mark.parametrize('field,value', [('hasFix', False), ('latitude', float('nan')), ('longitude', 181.),
                                         ('unixTimestampMillis', 1793795900000)])
def test_invalid_or_old_gnss_fix_is_never_live(field, value):
  messages = LocationMessages()
  setattr(messages['gpsLocation'], field, value)
  payload, _ = location_sample(messages, 101., 1793796001.)
  assert payload['valid'] is False
  assert payload['position'] is None


def test_stale_gps_message_is_not_republished_as_fresh():
  assert location_sample(LocationMessages(), 110., 1793796010.) is None


def test_road_geometry_backlog_is_sent_in_bounded_ordered_batches():
  events = [{'id': i, 'geometry': 'x' * 200} for i in range(20)]
  batch = batch_prefix(events, limit_bytes=1000)
  assert 1 < len(batch) < len(events)
  assert batch == events[:len(batch)]
  assert sum(len(json.dumps(e).encode()) for e in batch) <= 1000


def test_cache_export_preserves_provenance_and_ignores_expired_far_or_session_data(tmp_path):
  path, now = tmp_path / 'cache.sqlite', 1793801000.
  near = {'geometry': [[49.104, 8.471], [49.106, 8.471]],
          'sections': [{'start': 0., 'end': 100., 'speed': 70 / 3.6, 'confidence': .98, 'road_id': 'road42'}]}
  far = {**near, 'geometry': [[48., 8.], [48.002, 8.]]}
  with sqlite3.connect(path) as database:
    database.execute('CREATE TABLE corridors(cache_key TEXT,response TEXT,fetched REAL,expires REAL,session_id TEXT)')
    for key, response, expires, session in [('near', near, now + 50, 'persistent'), ('expired', near, now - 1, 'persistent'),
                                           ('far', far, now + 50, 'persistent'), ('session', near, now + 50, 'previous-boot')]:
      database.execute('INSERT INTO corridors VALUES (?,?,?,?,?)', (key, json.dumps(response), now - 100, expires, session))
  events = cached_corridors({'latitude': 49.104374, 'longitude': 8.470916}, now, path)
  assert len(events) == 1
  assert events[0]['event'] == 'tomtom_cache'
  assert events[0]['cache_key'] == 'near'
  assert events[0]['fetched_at_unix_s'] == now - 100
  assert events[0]['expires_at_unix_s'] == now + 50
  assert events[0]['sections'][0]['limit_kph'] == 70.
  assert len(events[0]['sections'][0]['geometry']) == 2


@pytest.mark.parametrize('redirect', [False, True])
def test_upload_protocol_and_no_credential_redirect(redirect):
  received = []

  class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
      assert self.headers['User-Agent'] == 'sunnypilot-slc-telemetry/1.0'
      body = gzip.decompress(self.rfile.read(int(self.headers['Content-Length'])))
      received.append((self.headers['Authorization'], json.loads(body)))
      self.send_response(302 if redirect else 204)
      if redirect:
        self.send_header('Location', '/different-target')
      self.end_headers()

    def log_message(self, *_args):
      pass

  server = HTTPServer(('127.0.0.1', 0), Handler)
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  events = [{'id': 1, 'event': 'location', 'position': None}]
  try:
    endpoint = f'http://127.0.0.1:{server.server_port}/api/telemetry/ingest'
    if redirect:
      with pytest.raises(HTTPError):
        upload(endpoint, 'test-only-token', 'test-session', events)
    else:
      upload(endpoint, 'test-only-token', 'test-session', events)
    assert received == [('Bearer test-only-token', {'source': 'test-session', 'events': events})]
  finally:
    server.shutdown()
    server.server_close()
    thread.join()
