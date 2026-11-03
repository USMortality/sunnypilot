import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from openpilot.cereal import log
from openpilot.selfdrive.controls.lib.longitudinal_personality import (
  LONGITUDINAL_PERSONALITY_ORDER, LONGITUDINAL_PERSONALITY_TO_BUTTON, next_personality, personality_to_gap_bars,
)
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import get_T_FOLLOW, get_jerk_factor
from openpilot.sunnypilot.selfdrive.controls.lib.longitudinal_planner import lead_coast_min_distance


PROFILES = [('aggressive', 1, 1.0, .6), ('moderate', 2, 1.5, .8), ('standard', 3, 2.0, 1.), ('relaxed', 4, 2.5, 1.)]


def test_cycle_and_button_order_cover_every_declared_profile():
  assert set(LONGITUDINAL_PERSONALITY_ORDER) == set(log.LongitudinalPersonality.schema.enumerants.values())
  assert len(LONGITUDINAL_PERSONALITY_ORDER) == 4
  profile = LONGITUDINAL_PERSONALITY_ORDER[0]
  visited = []
  for _ in range(4):
    visited.append(profile)
    profile = next_personality(profile)
  assert tuple(visited) == LONGITUDINAL_PERSONALITY_ORDER
  assert profile == visited[0]


@pytest.mark.parametrize('name,bars,follow,jerk', PROFILES)
def test_all_profile_consumers(name, bars, follow, jerk):
  raw = log.LongitudinalPersonality.schema.enumerants[name]
  state = log.SelfdriveState.new_message(personality=raw)
  assert personality_to_gap_bars(raw) == bars
  assert personality_to_gap_bars(state.personality) == bars
  assert LONGITUDINAL_PERSONALITY_TO_BUTTON[raw] == bars - 1
  assert get_T_FOLLOW(state.personality) == follow
  assert get_jerk_factor(state.personality) == jerk
  assert lead_coast_min_distance(20., state.personality) == pytest.approx(.95 * follow * 20.)


@pytest.mark.parametrize('name,bars,follow,jerk', PROFILES)
def test_profile_change_alert_handles_fourth_profile(name, bars, follow, jerk):
  from openpilot.selfdrive.selfdrived.events import personality_changed_alert
  alert = personality_changed_alert(None, None, None, True, 0, name)
  assert name.title() in alert.alert_text_1


@pytest.mark.parametrize('name,bars,follow,jerk', PROFILES)
def test_mici_indicator_maps_all_four_profiles(monkeypatch, name, bars, follow, jerk):
  # Render the actual indicator's bar logic without opening a graphics window.
  from openpilot.system.ui.lib.application import gui_app
  state = log.SelfdriveState.new_message(personality=log.LongitudinalPersonality.schema.enumerants[name])
  with monkeypatch.context() as imports:
    imports.setitem(sys.modules, 'openpilot.selfdrive.ui.ui_state', NS(ui_state=NS(sm={'selfdriveState': state, 'onroadEvents': []})))
    path = Path(__file__).resolve().parents[2] / 'ui/mici/onroad/long_indicator.py'
    spec = importlib.util.spec_from_file_location('four_profile_indicator_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
  monkeypatch.setattr(gui_app, 'texture', lambda path, width, height, **kwargs: NS(width=width, height=height))
  monkeypatch.setattr(module.rl, 'get_time', lambda: 10.)
  indicator = module.LongIndicator()
  indicator._personality = 99  # cause a profile-change highlight
  calls = []
  monkeypatch.setattr(indicator, '_draw_centered', lambda texture, rect, y, alpha: calls.append((y, alpha)))
  indicator._draw_distance_bars(module.rl.Rectangle(0., 0., 92., 200.), 1., True)
  assert len(indicator._distance_filters) == 4
  assert len(calls) == 8
  highlighted = [index for index, (_, alpha) in enumerate(calls[1::2]) if alpha > 0.]
  assert highlighted == [bars - 1]
