from types import SimpleNamespace as NS

import pytest

from openpilot.cereal import log
from openpilot.selfdrive.controls.lib.longitudinal_personality import LONGITUDINAL_PERSONALITY_ORDER


def test_first_gap_release_and_full_cycle_need_no_removed_experimental_latch():
  from unittest.mock import Mock
  from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD, ButtonType, EventName
  daemon = SelfdriveD.__new__(SelfdriveD)
  daemon.CP = NS(openpilotLongitudinalControl=True)
  daemon.params = Mock()
  daemon.events = Mock()
  daemon.personality = LONGITUDINAL_PERSONALITY_ORDER[0]
  assert not hasattr(daemon, 'experimental_mode_switched')
  buttons = NS(buttonEvents=[NS(type=ButtonType.gapAdjustCruise, pressed=False)])
  for expected in (*LONGITUDINAL_PERSONALITY_ORDER[1:], LONGITUDINAL_PERSONALITY_ORDER[0]):
    daemon.update_longitudinal_personality(buttons)
    assert daemon.personality == expected
    daemon.params.put.assert_called_with('LongitudinalPersonality', expected)
    daemon.events.add.assert_called_with(EventName.personalityChanged)
  assert daemon.events.add.call_count == 4


@pytest.mark.parametrize('longitudinal,pressed', [(False, False), (True, True)])
def test_gap_button_does_not_cycle_without_release_and_long_control(longitudinal, pressed):
  from unittest.mock import Mock
  from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD, ButtonType
  daemon = SelfdriveD.__new__(SelfdriveD)
  daemon.CP = NS(openpilotLongitudinalControl=longitudinal)
  daemon.params = Mock()
  daemon.events = Mock()
  daemon.personality = log.LongitudinalPersonality.standard
  daemon.update_longitudinal_personality(NS(buttonEvents=[NS(type=ButtonType.gapAdjustCruise, pressed=pressed)]))
  assert daemon.personality == log.LongitudinalPersonality.standard
  daemon.params.put.assert_not_called()


