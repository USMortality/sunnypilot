"""On-road and home shortcuts share the settings switch, without deprecated params."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit import slc_config


@pytest.fixture
def ui(monkeypatch, tmp_path):
  state = NS(has_longitudinal_control=True, sm={'selfdriveState': NS(engageable=True, enabled=False)})
  from openpilot.system.ui.lib.application import gui_app
  monkeypatch.setattr(gui_app, 'texture', lambda path, width, height, **kwargs: NS(width=width, height=height))
  monkeypatch.setattr(gui_app, 'font', lambda *args: None)
  monkeypatch.setattr(slc_config, 'SLC_CONFIG_PATH', tmp_path / 'slc.json')
  slc_config.set_longitudinal_e2e_enabled(False)
  def load(path):
    with monkeypatch.context() as imports:
      imports.setitem(sys.modules, 'openpilot.selfdrive.ui.ui_state', NS(ui_state=state, UIStatus=Mock(), ChestnutState=Mock()))
      spec = importlib.util.spec_from_file_location('experimental_ui_' + path.replace('/', '_'),
                                                   Path(__file__).resolve().parents[1] / path)
      module = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(module)
    return module
  return state, load


def test_onroad_toggle_uses_current_saved_state_for_rapid_taps(ui):
  _, load = ui
  module = load('onroad/exp_button.py')
  button = module.ExpButton(192, 144)
  button._update_state()
  assert not button._experimental_mode
  button._handle_mouse_release(None)
  assert slc_config.get_longitudinal_e2e_enabled()
  # Tap again before a selfdriveState update: do not reuse its old state.
  button._handle_mouse_release(None)
  assert not slc_config.get_longitudinal_e2e_enabled()


def test_onroad_toggle_yields_to_vehicle_capability_and_external_changes(ui):
  state, load = ui
  module = load('onroad/exp_button.py')
  button = module.ExpButton(192, 144)
  slc_config.set_longitudinal_e2e_enabled(True)
  button._update_state()
  assert button._experimental_mode
  state.has_longitudinal_control = False
  button._handle_mouse_release(None)
  assert slc_config.get_longitudinal_e2e_enabled()
  button._update_state()
  assert not button._experimental_mode


def test_home_indicator_refreshes_when_settings_change(ui):
  _, load = ui
  module = load('widgets/exp_mode_button.py')
  button = module.ExperimentalModeButton()
  assert not button.experimental_mode
  slc_config.set_longitudinal_e2e_enabled(True)
  button._update_state()
  assert button.experimental_mode


def test_mici_home_shortcut_saves_same_switch(ui):
  state, load = ui
  module = load('mici/layouts/home.py')
  home = module.MiciHomeLayout.__new__(module.MiciHomeLayout)
  home._toggle_experimental_mode()
  assert slc_config.get_longitudinal_e2e_enabled()
  home._toggle_experimental_mode()
  assert not slc_config.get_longitudinal_e2e_enabled()
  state.has_longitudinal_control = False
  home._toggle_experimental_mode()
  assert not slc_config.get_longitudinal_e2e_enabled()


def test_hud_contains_button_at_original_position(ui, monkeypatch):
  _, load = ui
  module = load('onroad/hud_renderer.py')
  hud = module.HudRenderer()
  hud.is_cruise_available = False
  hud._draw_current_speed = Mock()
  hud._exp_button.render = Mock()
  monkeypatch.setattr(module.rl, 'draw_rectangle_gradient_v', Mock())
  hud._render(module.rl.Rectangle(10, 20, 2160, 1080))
  button_rect = hud._exp_button.render.call_args.args[0]
  assert (button_rect.x, button_rect.y, button_rect.width, button_rect.height) == (1948, 50, 192, 192)


def test_restored_icons_are_available():
  assets = Path(__file__).resolve().parents[2] / 'assets'
  for path in ['icons/experimental.png', 'icons/experimental_white.png', 'icons/experimental_grey.png', 'icons_mici/experimental_mode.png']:
    assert (assets / path).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')


def test_mici_long_press_consumes_release_without_opening_settings(ui, monkeypatch):
  import time
  _, load = ui
  module = load('mici/layouts/home.py')
  monkeypatch.setattr(module.MiciHomeLayout, '_get_version_text', lambda self: None)
  monkeypatch.setattr(module, 'UnifiedLabel', Mock())
  home = module.MiciHomeLayout()
  home.set_rect(module.rl.Rectangle(0, 0, 500, 800))
  home._on_settings_click = Mock()
  home._press_started[0] = time.monotonic() - 1.
  home._Widget__is_pressed[0] = True
  monkeypatch.setattr(module.gui_app, '_mouse_events', [])
  home._process_mouse_events()
  assert slc_config.get_longitudinal_e2e_enabled()
  assert not home.is_pressed
  # The same touch's release must not also open settings.
  module.gui_app._mouse_events.append(NS(slot=0, pos=module.rl.Vector2(10, 10), left_pressed=False, left_released=True))
  home._process_mouse_events()
  home._on_settings_click.assert_not_called()
