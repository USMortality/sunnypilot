#!/usr/bin/env python3
import argparse
import json

import requests

from openpilot.sunnypilot.mapd.live_map_data.tomtom_map_data import ENDPOINT, FIELDS, load_api_key


def main():
  parser = argparse.ArgumentParser(description="Bounded, redacted TomTom corridor validation")
  parser.add_argument("corridor", help="JSON array of [latitude, longitude] points")
  parser.add_argument("--live", action="store_true", help="make exactly one Snap to Roads call")
  args = parser.parse_args()
  points = json.load(open(args.corridor))
  if not 2 <= len(points) <= 100:
    raise SystemExit("corridor must contain 2..100 points")
  print(json.dumps({"endpoint": "snapToRoads/1", "points": len(points), "calls": 1 if args.live else 0}))
  if not args.live:
    return
  key = load_api_key()
  if not key:
    raise SystemExit("TOMTOM_API_KEY is not configured")
  body = {"points": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": {}}
                     for lat, lon in points]}
  response = requests.post(ENDPOINT, params={"key": key, "fields": FIELDS, "vehicleType": "PassengerCar", "measurementSystem": "metric"},
                           json=body, timeout=(3, 8))
  data = response.json() if response.ok else {}
  evidence = {"status": response.status_code, "cacheControl": response.headers.get("Cache-Control", ""),
              "expires": response.headers.get("Expires", ""), "trackingIdPresent": bool(response.headers.get("Tracking-ID")),
              "roadElements": len(data.get("route", [])), "projectedPoints": len(data.get("projectedPoints", []))}
  print(json.dumps(evidence, indent=2))
  response.raise_for_status()


if __name__ == "__main__":
  main()
