import json
import os
import sqlite3
import threading
import time


class TomTomCache:
  """Bounded, session-scoped by default. Persistence requires explicit header/terms evidence."""
  def __init__(self, path="/data/sunnypilot/tomtom-cache.sqlite", session_id="", max_entries=256):
    directory = os.path.dirname(path)
    if directory:
      os.makedirs(directory, exist_ok=True)
    self.db = sqlite3.connect(path, check_same_thread=False)
    self.lock = threading.Lock()
    self.session_id, self.max_entries = session_id, max_entries
    with self.db:
      self.db.execute("CREATE TABLE IF NOT EXISTS corridors (cache_key TEXT PRIMARY KEY, provider_version TEXT, session_id TEXT, " +
                      "response TEXT, provenance TEXT, fetched REAL, expires REAL)")
      self.db.execute("CREATE TABLE IF NOT EXISTS usage (endpoint TEXT, month TEXT, count INTEGER, PRIMARY KEY(endpoint, month))")
      self.db.execute("CREATE TABLE IF NOT EXISTS daily_usage (endpoint TEXT, day TEXT, count INTEGER, PRIMARY KEY(endpoint, day))")

  def get(self, key, now=None):
    now = time.time() if now is None else now  # noqa: TID251 — cache expiry requires wall time across boots.
    with self.lock:
      row = self.db.execute("SELECT response, expires, session_id FROM corridors WHERE cache_key=?", (key,)).fetchone()
    if not row or row[1] <= now or row[2] not in (self.session_id, "persistent"):
      return None
    return json.loads(row[0])

  def put(self, key, version, response, provenance, ttl, now=None, persistent=False):
    now = time.time() if now is None else now  # noqa: TID251 — persisted timestamps require wall time.
    session = "persistent" if persistent else self.session_id
    with self.lock, self.db:
      self.db.execute("INSERT OR REPLACE INTO corridors VALUES (?,?,?,?,?,?,?)",
                      (key, version, session, json.dumps(response, separators=(",", ":")), provenance, now, now + ttl))
      self.db.execute("DELETE FROM corridors WHERE cache_key IN (SELECT cache_key FROM corridors ORDER BY fetched DESC LIMIT -1 OFFSET ?)", (self.max_entries,))

  def allow_and_count(self, endpoint, monthly_limit, now=None, daily_limit=2500):
    wall_time = time.time() if now is None else now  # noqa: TID251 — calendar budgets require wall time.
    month = time.strftime("%Y-%m", time.gmtime(wall_time))
    day = time.strftime("%Y-%m-%d", time.gmtime(wall_time))
    with self.lock, self.db:
      monthly_row = self.db.execute("SELECT count FROM usage WHERE endpoint=? AND month=?", (endpoint, month)).fetchone()
      daily_row = self.db.execute("SELECT count FROM daily_usage WHERE endpoint=? AND day=?", (endpoint, day)).fetchone()
      monthly_count = monthly_row[0] if monthly_row else 0
      daily_count = daily_row[0] if daily_row else 0
      if monthly_count >= monthly_limit or daily_count >= daily_limit:
        return False
      self.db.execute("INSERT INTO usage VALUES (?,?,1) ON CONFLICT(endpoint,month) DO UPDATE SET count=count+1", (endpoint, month))
      self.db.execute("INSERT INTO daily_usage VALUES (?,?,1) ON CONFLICT(endpoint,day) DO UPDATE SET count=count+1", (endpoint, day))
    return True
