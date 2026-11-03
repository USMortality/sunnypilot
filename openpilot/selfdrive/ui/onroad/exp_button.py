import pyray as rl
from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit.slc_config import get_longitudinal_e2e_enabled, set_longitudinal_e2e_enabled
from openpilot.system.ui.widgets.confirm_dialog import alert_dialog
from openpilot.system.ui.lib.multilang import tr
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets import Widget


class ExpButton(Widget):
  def __init__(self, button_size: int, icon_size: int):
    super().__init__()
    self._experimental_mode: bool = False
    self._engageable: bool = False

    self._white_color: rl.Color = rl.Color(255, 255, 255, 255)
    self._black_bg: rl.Color = rl.Color(0, 0, 0, 166)
    self._txt_wheel: rl.Texture = gui_app.texture('icons/chffr_wheel.png', icon_size, icon_size)
    self._txt_exp: rl.Texture = gui_app.texture('icons/experimental.png', icon_size, icon_size)
    self._rect = rl.Rectangle(0, 0, button_size, button_size)

  def set_rect(self, rect: rl.Rectangle) -> None:
    self._rect.x, self._rect.y = rect.x, rect.y

  def _update_state(self) -> None:
    selfdrive_state = ui_state.sm["selfdriveState"]
    self._experimental_mode = get_longitudinal_e2e_enabled() and ui_state.has_longitudinal_control
    self._engageable = selfdrive_state.engageable or selfdrive_state.enabled

  def _handle_mouse_release(self, _):
    super()._handle_mouse_release(_)
    if ui_state.has_longitudinal_control:
      try:
        set_longitudinal_e2e_enabled(not get_longitudinal_e2e_enabled())
        self._experimental_mode = get_longitudinal_e2e_enabled()
      except (OSError, ValueError):
        gui_app.push_widget(alert_dialog(tr("Unable to save Experimental Mode. Please try again.")))

  def _render(self, rect: rl.Rectangle) -> None:
    center_x = int(self._rect.x + self._rect.width // 2)
    center_y = int(self._rect.y + self._rect.height // 2)

    self._white_color.a = 180 if self.is_pressed or not self._engageable else 255

    texture = self._txt_exp if self._experimental_mode else self._txt_wheel
    rl.draw_circle(center_x, center_y, self._rect.width / 2, self._black_bg)
    rl.draw_texture_ex(texture, rl.Vector2(center_x - texture.width / 2, center_y - texture.height / 2), 0.0, 1.0, self._white_color)
