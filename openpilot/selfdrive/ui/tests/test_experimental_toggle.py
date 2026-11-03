"""Settings callbacks must change the same switch that the running planner reads."""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit import slc_config


@pytest.fixture(params=['layouts/settings/toggles.py', 'mici/layouts/settings/toggles.py'])
def settings(request, monkeypatch):
  # Import the actual layout/callback without creating a window or a live UI subscriber.
  with monkeypatch.context() as imports:
    imports.setitem(sys.modules, 'openpilot.selfdrive.ui.ui_state', NS(ui_state=Mock()))
    spec = importlib.util.spec_from_file_location('experimental_toggle_test', Path(__file__).resolve().parents[1] / request.param)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
  layout_class = module.TogglesLayout if 'mici' not in request.param else module.TogglesLayoutMici
  layout = layout_class.__new__(layout_class)
  control = Mock()
  if 'mici' in request.param:
    layout._experimental_btn = control
  else:
    layout._experimental_toggle = NS(action_item=control)
  monkeypatch.setattr(module.gui_app, 'push_widget', Mock())
  if 'mici' in request.param:
    monkeypatch.setattr(module, 'BigDialog', Mock())
  else:
    monkeypatch.setattr(module, 'alert_dialog', Mock())
  return module, layout, control


def test_both_layouts_persist_experimental_switch(settings, tmp_path, monkeypatch):
  _, layout, _ = settings
  path = tmp_path / 'slc.json'
  monkeypatch.setattr(slc_config, 'SLC_CONFIG_PATH', path)
  path.write_text(json.dumps({'speedLimitLookaheadFactorDown': 4.}))
  for enabled in (False, True):
    layout._on_experimental_mode_toggle(enabled)
    assert slc_config.get_longitudinal_e2e_enabled() is enabled
    assert json.loads(path.read_text())['speedLimitLookaheadFactorDown'] == 4.


def test_both_layouts_revert_switch_and_show_save_failure(settings, tmp_path, monkeypatch):
  module, layout, control = settings
  path = tmp_path / 'slc.json'
  monkeypatch.setattr(slc_config, 'SLC_CONFIG_PATH', path)
  path.write_text('{"longitudinalE2EEnabled": true}')
  def fail_save(*args):
    raise OSError('read-only filesystem')
  monkeypatch.setattr(module, 'set_longitudinal_e2e_enabled', fail_save)
  layout._on_experimental_mode_toggle(False)
  calls = control.set_checked if hasattr(layout, '_experimental_btn') else control.set_state
  calls.assert_called_once_with(True)
  module.gui_app.push_widget.assert_called_once()
  assert slc_config.get_longitudinal_e2e_enabled()
