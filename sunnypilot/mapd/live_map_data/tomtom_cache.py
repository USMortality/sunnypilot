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
      self.db.execute("CREATE TABLE IF NOT EXISTS corridors (cache_key TEXT PRIMARY KEY, provider_version TEXT, session_id TEXT, response TEXT, provenance TEXT, fetched REAL, expires REAL)")
      self.db.execute("CREATE TABLE IF NOT EXISTS usage (endpoint TEXT, month TEXT, count INTEGER, PRIMARY KEY(endpoint, month))")

  def get(self, key, now=None):
    now = time.time() if now is None else now
    with self.lock:
      row = self.db.execute("SELECT response, expires, session_id FROM corridors WHERE cache_key=?", (key,)).fetchone()
    if not row or row[1] <= now or row[2] not in (self.session_id, "persistent"):
      return None
    return json.loads(row[0])

  def put(self, key, version, response, provenance, ttl, now=None, persistent=False):
    now = time.time() if now is None else now
    session = "persistent" if persistent else self.session_id
    with self.lock, self.db:
      self.db.execute("INSERT OR REPLACE INTO corridors VALUES (?,?,?,?,?,?,?)",
                      (key, version, session, json.dumps(response, separators=(",", ":")), provenance, now, now + ttl))
      self.db.execute("DELETE FROM corridors WHERE cache_key IN (SELECT cache_key FROM corridors ORDER BY fetched DESC LIMIT -1 OFFSET ?)", (self.max_entries,))

  def allow_and_count(self, endpoint, monthly_limit, now=None):
    month = time.strftime("%Y-%m", time.gmtime(time.time() if now is None else now))
    with self.lock, self.db:
      row = self.db.execute("SELECT count FROM usage WHERE endpoint=? AND month=?", (endpoint, month)).fetchone()
      count = row[0] if row else 0
      if count >= monthly_limit:
        return False
      self.db.execute("INSERT INTO usage VALUES (?,?,1) ON CONFLICT(endpoint,month) DO UPDATE SET count=count+1", (endpoint, month))
    return True
