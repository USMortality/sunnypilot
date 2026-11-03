from openpilot.cereal import log
from openpilot.sunnypilot.selfdrive.controls.lib.speed_limit.slc_config import get_longitudinal_e2e_enabled, set_longitudinal_e2e_enabled
from openpilot.selfdrive.ui.mici.widgets.dialog import BigDialog
from openpilot.selfdrive.controls.lib.longitudinal_personality import LONGITUDINAL_PERSONALITY_ORDER, LONGITUDINAL_PERSONALITY_TO_BUTTON

from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.selfdrive.ui.mici.widgets.button import BigToggle, BigParamControl, BigMultiParamToggle
from openpilot.system.ui.lib.application import gui_app
from openpilot.selfdrive.ui.layouts.settings.common import restart_needed_callback
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.selfdrive.ui.mici.layouts.settings.initial_cruise_speed import InitialCruiseSpeedButton

PERSONALITY_TO_INT = log.LongitudinalPersonality.schema.enumerants



class TogglesLayoutMici(NavScroller):
  def __init__(self):
    super().__init__()

    self._personality_toggle = BigMultiParamToggle(
      "following distance", "LongitudinalPersonality", ["aggressive", "moderate", "standard", "relaxed"],
      param_values=list(LONGITUDINAL_PERSONALITY_ORDER),
      description="Standard is recommended.\n" +
                  "Aggressive follows closer, with firmer gas and braking.\n" +
                  "Relaxed leaves more space.\n" +
                  "Use the steering wheel distance button on supported cars.")
    self._experimental_btn = BigToggle(
      "experimental mode", initial_state=get_longitudinal_e2e_enabled(), toggle_callback=self._on_experimental_mode_toggle,
      description_icon=gui_app.texture("icons_mici/experimental_mode.png", 64, 64),
      description="Let the driving model control gas and brakes.\nIncludes stopping for red lights and stop signs.\n" +
                  "Set speed is an upper bound.\nTurn off to use cruise and speed-limit control for speed selection.\n" +
                  "Changes apply within a few seconds.")
    self._experimental_btn.set_enabled(lambda: ui_state.CP is None or ui_state.has_longitudinal_control)
    self._initial_cruise_speed = InitialCruiseSpeedButton()
    self._initial_cruise_speed.set_visible(lambda: ui_state.CP is not None and ui_state.has_longitudinal_control and not ui_state.CP.pcmCruise)
    is_metric_toggle = BigToggle("use metric units", initial_state=ui_state.params.get_bool("IsMetric"), toggle_callback=self._on_metric_toggle)
    ldw_toggle = BigParamControl("lane departure warnings", "IsLdwEnabled",
                                 description="Warn when you drift across a detected lane line.\n" +
                                             "Only above 31 mph (50 km/h), with no turn signal.")
    always_on_dm_toggle = BigParamControl("always-on driver monitor", "AlwaysOnDM", description="Monitor the driver even when sunnypilot is not engaged.")
    record_front = BigParamControl("record & upload cabin camera", "RecordFront",
                                   description_icon=gui_app.texture("icons_mici/settings/device/cameras.png", 64, 64),
                                   toggle_callback=restart_needed_callback, description="Upload cabin camera data to help improve driver monitoring.")
    record_mic = BigParamControl("record & upload mic audio", "RecordAudio", description_icon=gui_app.texture("icons_mici/microphone.png", 64, 64),
                                 toggle_callback=restart_needed_callback,
                                 description="Record microphone audio while driving.\n" +
                                             "Audio is included in dashcam videos in sunnylink.")
    enable_openpilot = BigParamControl("enable sunnypilot", "OpenpilotEnabledToggle", toggle_callback=restart_needed_callback,
                                       description="Enable to use sunnypilot driver assistance.\n" +
                                                   "Disable to use your car's stock driver assistance.")

    self._scroller.add_widgets([
      self._experimental_btn,
      self._personality_toggle,
      self._initial_cruise_speed,
      is_metric_toggle,
      ldw_toggle,
      always_on_dm_toggle,
      record_front,
      record_mic,
      enable_openpilot,
    ])

    # Toggle lists
    self._refresh_toggles = (
      ("IsMetric", is_metric_toggle),
      ("IsLdwEnabled", ldw_toggle),
      ("AlwaysOnDM", always_on_dm_toggle),
      ("RecordFront", record_front),
      ("RecordAudio", record_mic),
      ("OpenpilotEnabledToggle", enable_openpilot),
    )

    enable_openpilot.set_enabled(lambda: not ui_state.engaged)
    record_front.set_enabled(False if ui_state.params.get_bool("RecordFrontLock") else (lambda: not ui_state.engaged))
    record_mic.set_enabled(lambda: not ui_state.engaged)

    if ui_state.params.get_bool("ShowDebugInfo"):
      gui_app.set_show_touches(True)
      gui_app.set_show_fps(True)

    ui_state.add_engaged_transition_callback(self._update_toggles)

  def _update_state(self):
    super()._update_state()

    if ui_state.sm.updated["selfdriveState"]:
      personality = PERSONALITY_TO_INT[ui_state.sm["selfdriveState"].personality]
      if personality != ui_state.personality and ui_state.started:
        self._personality_toggle.set_value(self._personality_toggle._options[LONGITUDINAL_PERSONALITY_TO_BUTTON[personality]])
      ui_state.personality = personality

  def show_event(self):
    super().show_event()
    self._update_toggles()

  def _on_experimental_mode_toggle(self, state: bool):
    try:
      set_longitudinal_e2e_enabled(state)
    except (OSError, ValueError):
      self._experimental_btn.set_checked(get_longitudinal_e2e_enabled())
      gui_app.push_widget(BigDialog("unable to save", "Experimental Mode could not be saved. Please try again."))

  def _on_metric_toggle(self, state: bool):
    ui_state.params.put_bool("IsMetric", state, block=True)
    self._update_toggles()

  def _update_toggles(self):
    ui_state.update_params()
    self._initial_cruise_speed.refresh()
    self._experimental_btn.set_checked(get_longitudinal_e2e_enabled())

    if ui_state.CP is not None:
      self._personality_toggle.set_visible(ui_state.has_longitudinal_control)

    # Refresh toggles from params to mirror external changes
    for key, item in self._refresh_toggles:
      item.set_checked(ui_state.params.get_bool(key))
