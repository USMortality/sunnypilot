"""Exercise the actual FCW helper/timing block without loading the driving daemon.

Only the selected source AST is compiled; no duplicate implementation or native
IPC/control processes are used. These are logic regressions, not road validation.
"""
import ast
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from openpilot.cereal import log

LaneState, Direction = log.LaneChangeState, log.LaneChangeDirection


@pytest.fixture(scope='module')
def logic():
  source = Path(__file__).parents[1] / 'selfdrived.py'
  tree = ast.parse(source.read_text())
  constants = [node for node in tree.body if isinstance(node, ast.Assign) and
               any(isinstance(target, ast.Name) and target.id.startswith('LANE_CHANGE_FCW_SUPPRESS_') for target in node.targets)]
  helper = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'should_suppress_lane_change_fcw')
  update = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == 'update_events')
  start = next(i for i, node in enumerate(update.body) if isinstance(node, ast.Assign) and
               any(isinstance(target, ast.Name) and target.id == 'lane_change_state' for target in node.targets))
  end = next(i for i, node in enumerate(update.body) if isinstance(node, ast.Assign) and
             any(isinstance(target, ast.Name) and target.id == 'recent_lane_change' for target in node.targets))
  tracking = ast.FunctionDef(name='track', args=ast.arguments(posonlyargs=[], args=[ast.arg(arg='self')],
    kwonlyargs=[], kw_defaults=[], defaults=[]), body=[*update.body[start:end + 1], ast.Return(value=ast.Name(id='recent_lane_change', ctx=ast.Load()))],
    decorator_list=[])
  realtime = ast.parse((source.parents[2] / 'common/realtime.py').read_text())
  dt = next(ast.literal_eval(node.value) for node in realtime.body if isinstance(node, ast.Assign) and
            any(isinstance(target, ast.Name) and target.id == 'DT_CTRL' for target in node.targets))
  module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0),
                           *constants, helper, tracking], type_ignores=[])
  namespace = {'LaneChangeState': LaneState, 'LaneChangeDirection': Direction, 'DT_CTRL': dt}
  exec(compile(ast.fix_missing_locations(module), str(source), 'exec'), namespace)
  return NS(suppress=namespace[helper.name], track=namespace['track'])


def inputs(state=LaneState.laneChangeStarting, direction=Direction.left, **lead_changes):
  lead = NS(present=True, dRel=20., vRel=1., yRel=1.)
  lead.__dict__.update(lead_changes)

  class Messages(dict):
    valid = {'radarState': True}
  sm = Messages(modelV2=NS(meta=NS(laneChangeState=state, laneChangeDirection=direction)), radarState=NS(leadOne=lead))
  return sm, NS(aEgo=0., brakePressed=False)


@pytest.mark.parametrize('direction,yrel', [(Direction.left, .51), (Direction.right, -.51)])
def test_crossover_requires_lead_on_correct_target_side(logic, direction, yrel):
  sm, car = inputs(direction=direction, yRel=yrel)
  assert logic.suppress(sm, car, False)
  sm['radarState'].leadOne.yRel = -yrel
  assert not logic.suppress(sm, car, False)


@pytest.mark.parametrize('field,value', [('present', False), ('dRel', 10.), ('dRel', 9.),
                                       ('vRel', .5), ('vRel', 0.), ('vRel', -1.), ('yRel', .5)])
def test_crossover_does_not_suppress_without_qualifying_lead(logic, field, value):
  sm, car = inputs(**{field: value})
  assert not logic.suppress(sm, car, False)


@pytest.mark.parametrize('recent', [False, True])
@pytest.mark.parametrize('gate', ['radar', 'driver_brake', 'ego_braking'])
def test_braking_and_invalid_radar_keep_fcw_enabled(logic, recent, gate):
  sm, car = inputs()
  if gate == 'radar':
    sm.valid = {'radarState': False}
  elif gate == 'driver_brake':
    car.brakePressed = True
  else:
    car.aEgo = -1.
  assert not logic.suppress(sm, car, recent)


def test_completed_lane_change_can_reset_direction_without_changing_grace_gate(logic):
  sm, car = inputs(state=LaneState.off, direction=Direction.none, yRel=0.)
  assert logic.suppress(sm, car, True)
  assert not logic.suppress(sm, car, False)
  for closing_speed in [.5, 0., -1.]:
    sm['radarState'].leadOne.vRel = closing_speed
    assert not logic.suppress(sm, car, True)


def test_previous_grace_does_not_bypass_target_side_for_new_crossover(logic):
  sm, car = inputs(direction=Direction.none)
  assert not logic.suppress(sm, car, True)


def test_grace_starts_after_completed_maneuver_and_expires_at_ten_seconds(logic):
  sm, _ = inputs()
  sm.frame = 100
  daemon = NS(sm=sm, last_lane_change_end_frame=-1, lane_change_maneuver_active=False, lane_change_state_prev=LaneState.off)
  assert not logic.track(daemon)
  sm['modelV2'].meta.laneChangeState = LaneState.laneChangeFinishing
  assert not logic.track(daemon)
  sm.frame = 200
  sm['modelV2'].meta.laneChangeState = LaneState.off
  assert logic.track(daemon)
  assert daemon.last_lane_change_end_frame == 200
  sm.frame = 1199
  assert logic.track(daemon)
  sm.frame = 1200
  assert not logic.track(daemon)


def test_cancelled_pre_lane_change_does_not_arm_grace(logic):
  sm, _ = inputs(state=LaneState.preLaneChange)
  sm.frame = 100
  daemon = NS(sm=sm, last_lane_change_end_frame=-1, lane_change_maneuver_active=False, lane_change_state_prev=LaneState.off)
  assert not logic.track(daemon)
  sm['modelV2'].meta.laneChangeState = LaneState.off
  assert not logic.track(daemon)
  assert daemon.last_lane_change_end_frame == -1
