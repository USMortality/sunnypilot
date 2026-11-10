import math

EARTH_RADIUS_M = 6371000.0
MAX_POSITION_EXTENSION_M = 150.0
MAX_POSITION_DISTANCE_M = 20.0


def distance_m(a, b):
  lat1, lat2 = math.radians(a[0]), math.radians(b[0])
  dlat, dlon = lat2 - lat1, math.radians(b[1] - a[1])
  h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
  return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def polyline_length(points):
  return sum(distance_m(a, b) for a, b in zip(points, points[1:], strict=False))


def point_at_progress(points, progress):
  for a, b in zip(points, points[1:], strict=False):
    length = distance_m(a, b)
    if length > 0 and progress <= length:
      fraction = max(0.0, progress / length)
      return [a[0] + fraction * (b[0] - a[0]), a[1] + fraction * (b[1] - a[1])]
    progress -= length
  return points[-1]


def geometry_between(points, start, end):
  """Clip a speed section to the road polyline, retaining intermediate bends."""
  if len(points) < 2:
    return []
  start, end = max(0., start), min(polyline_length(points), end)
  if end <= start:
    return []
  selected = [point_at_progress(points, start)]
  walked = 0.
  for a, b in zip(points, points[1:], strict=False):
    walked += distance_m(a, b)
    if start < walked < end:
      selected.append(b)
  selected.append(point_at_progress(points, end))
  return selected


def extend_geometry_to_position(points, position):
  """Include a vehicle just before the first road node, without bridging adjacent roads."""
  if len(points) < 2 or distance_m(position, points[0]) > MAX_POSITION_EXTENSION_M:
    return points
  a, b = points[:2]
  scale_x = math.cos(math.radians(position[0]))
  dx, dy = (b[1] - a[1]) * scale_x, b[0] - a[0]
  px, py = (position[1] - a[1]) * scale_x, position[0] - a[0]
  length2 = dx * dx + dy * dy
  if not length2:
    return points
  fraction = (px * dx + py * dy) / length2
  projected = [a[0] + fraction * (b[0] - a[0]), a[1] + fraction * (b[1] - a[1])]
  if fraction < 0 and distance_m(position, projected) <= MAX_POSITION_DISTANCE_M:
    return [position, *points][:256]
  return points


def road_geometry_window(points, position, heading):
  """Keep full topology endpoints and bound a corridor around the vehicle."""
  points = extend_geometry_to_position(points, position)
  progress, _ = closest_progress(points, position, heading=heading)
  return geometry_between(points, max(0., progress - 50.), progress + 1000.)[:256]


def closest_progress(points, position, minimum_progress=0.0, maximum_progress=math.inf, heading=None):
  """Return along-line progress and lateral distance using a local equirectangular projection."""
  if len(points) < 2:
    return 0.0, math.inf
  lat0 = math.radians(position[0])
  scale_x = EARTH_RADIUS_M * math.cos(lat0) * math.pi / 180
  scale_y = EARTH_RADIUS_M * math.pi / 180
  px, py = (position[1] - points[0][1]) * scale_x, (position[0] - points[0][0]) * scale_y
  best_dist, best_progress, walked = math.inf, 0.0, 0.0
  for a, b in zip(points, points[1:], strict=False):
    ax, ay = (a[1] - points[0][1]) * scale_x, (a[0] - points[0][0]) * scale_y
    bx, by = (b[1] - points[0][1]) * scale_x, (b[0] - points[0][0]) * scale_y
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    seg = math.sqrt(seg2)
    # Reject the opposite carriageway even when it is the nearest geometry.
    aligned = heading is None or (seg > 0 and abs((math.degrees(math.atan2(dx, dy)) - heading + 180) % 360 - 180) < 90)
    if not aligned or walked + seg < minimum_progress or walked > maximum_progress:
      walked += seg
      continue
    lower = max(0.0, (minimum_progress - walked) / seg) if seg else 0.0
    upper = min(1.0, (maximum_progress - walked) / seg) if seg else 1.0
    t = max(lower, min(upper, ((px - ax) * dx + (py - ay) * dy) / seg2)) if seg2 else 0.0
    d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
    if d < best_dist:
      best_dist, best_progress = d, walked + t * seg
    walked += seg
  return best_progress, best_dist


def first_reversal_progress(points, progress=0.0):
  """End prediction at an abrupt reversal; a route-free matcher cannot infer a U-turn.

  Smooth bends and roundabouts retain their ordered geometry. A new observation
  after actually making the turn can establish the new direction.
  """
  walked = 0.0
  for a, b, c in zip(points, points[1:], points[2:], strict=False):
    walked += distance_m(a, b)
    if walked < progress:
      continue
    scale = math.cos(math.radians(b[0]))
    incoming = ((b[1] - a[1]) * scale, b[0] - a[0])
    outgoing = ((c[1] - b[1]) * scale, c[0] - b[0])
    norm = math.hypot(*incoming) * math.hypot(*outgoing)
    if norm and sum(x * y for x, y in zip(incoming, outgoing, strict=True)) / norm < -0.5:
      return walked
  return math.inf
