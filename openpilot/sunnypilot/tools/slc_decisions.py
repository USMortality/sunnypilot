"""Export SLC audit events from local rlogs as JSONL for offline analysis."""
import argparse
import json
import sys
from collections import Counter
from contextlib import nullcontext
from pathlib import Path

from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit.decision_log import EVENTS


def decision_events(messages):
  for message in messages:
    if message.which() != "logMessage":
      continue
    try:
      record = json.loads(message.logMessage)
      payload = record.get("msg", {})
      if isinstance(payload, dict) and payload.get("event") in EVENTS:
        yield {**payload, "log_message_mono_time_ns": message.logMonoTime}
    except (TypeError, ValueError, AttributeError):
      continue


def main():
  from openpilot.tools.lib.logreader import LogReader

  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("rlogs", nargs="+", type=Path, help="local rlog.zst or rlog.bz2 files")
  parser.add_argument("--output", type=Path, help="write JSONL to this file instead of stdout")
  args = parser.parse_args()
  for path in args.rlogs:
    if not path.is_file():
      parser.error(f"not a local rlog file: {path}")
  counts = Counter()
  output = args.output.open("w") if args.output else nullcontext(sys.stdout)
  with output as stream:
    for path in args.rlogs:
      for event in decision_events(LogReader(str(path))):
        counts[event["event"]] += 1
        if event.get("auto_accepted_on_engagement"):
          counts["engagement_auto_accepts"] += 1
        if event.get("selected_invalid_map_message"):
          counts["invalid_map_selection_events"] += 1
        if event.get("selected_invalid_vehicle_message"):
          counts["invalid_vehicle_selection_events"] += 1
        stream.write(json.dumps({"rlog": str(path), **event}, allow_nan=False) + "\n")
  print(json.dumps(dict(counts)), file=sys.stderr)


if __name__ == "__main__":
  main()
