"""Exercise PPP failure recovery, modem reset cooldowns, and eSIM lock coordination."""

from unittest.mock import Mock, patch

import pytest

from openpilot.common.hardware.comma.modem import Modem, PPPSession, State


@pytest.fixture
def modem():
  m = Modem()
  m._publish_state = lambda **kwargs: m.S.update(kwargs)
  m._ppp.start = Mock()
  m._ppp.kill = Mock()
  m._ppp.cleanup_routes = Mock()
  m._ppp.reset_data_port = Mock()
  m._params_changed = Mock(return_value=False)
  m._poll = Mock()
  with patch('openpilot.common.hardware.comma.modem.os.path.exists', return_value=True):
    yield m


def test_failures_survive_reinitialization(modem):
  assert modem._handle_pppd_exit() == State.CONNECTED
  modem._do_disconnecting()
  modem._do_connecting()
  assert modem._handle_pppd_exit() == State.CONNECTED
  assert modem._handle_pppd_exit() == State.RESETTING


def test_reset_cooldown(modem):
  modem._last_reset = 1000
  for _ in range(PPPSession.MAX_FAILS - 1):
    modem._ppp.record_fail()
  with patch('openpilot.common.hardware.comma.modem.time.monotonic', return_value=1899):
    assert modem._handle_pppd_exit() == State.DISCONNECTING
  with patch('openpilot.common.hardware.comma.modem.time.monotonic', return_value=1900):
    assert modem._handle_pppd_exit() == State.RESETTING


def test_only_stable_connection_clears_failures(modem):
  modem._ppp.has_exited = Mock(return_value=False)
  modem._ppp.record_fail()
  modem.S['connected'] = True
  with patch('openpilot.common.hardware.comma.modem.time.monotonic', return_value=1000):
    assert modem._do_connected() == State.CONNECTED
  with patch('openpilot.common.hardware.comma.modem.time.monotonic', return_value=1059):
    modem._do_connected()
    assert modem._ppp.fails == 1
  with patch('openpilot.common.hardware.comma.modem.time.monotonic', return_value=1060):
    modem._do_connected()
    assert modem._ppp.fails == 0


def test_ip_timeout_counts_as_failure(modem):
  modem._ppp.has_exited = Mock(return_value=False)
  modem._ppp.started_at = 1000
  with patch('openpilot.common.hardware.comma.modem.time.monotonic', return_value=1089):
    assert modem._do_connected() == State.CONNECTED
    modem._ppp.kill.assert_not_called()
  with patch('openpilot.common.hardware.comma.modem.time.monotonic', return_value=1090):
    assert modem._do_connected() == State.CONNECTED
    modem._ppp.kill.assert_called_once()
    assert modem._ppp.fails == 1


def test_exit_clears_stale_connection(modem):
  modem.S.update(connected=True, ip_address='10.1.2.3')
  modem._connected_since = 1000
  modem._handle_pppd_exit()
  assert not modem.S['connected']
  assert modem.S['ip_address'] == ''
  assert modem._connected_since is None


@pytest.mark.parametrize('sim_change,port_present', [(True, True), (False, False)])
def test_exit_during_sim_or_port_change_does_not_count_as_failure(modem, sim_change, port_present):
  modem._sim_change = sim_change
  modem._ppp.record_fail()
  with patch('openpilot.common.hardware.comma.modem.os.path.exists', return_value=port_present):
    assert modem._handle_pppd_exit() == State.DISCONNECTING
  assert modem._ppp.fails == 1
  modem._ppp.start.assert_not_called()
  modem._ppp.reset_data_port.assert_not_called()


@pytest.mark.parametrize('sim_change,params_changed,port_present', [(True, False, True), (False, True, True), (False, False, False)])
def test_reset_skipped_for_configuration_or_device_change(modem, sim_change, params_changed, port_present):
  modem._sim_change = sim_change
  modem._params_changed.return_value = params_changed
  with patch('openpilot.common.hardware.comma.modem.os.path.exists', return_value=port_present):
    assert modem._do_resetting() == State.DISCONNECTING
  assert modem._last_reset is None
  modem._ppp.kill.assert_not_called()


def test_reset_waits_for_esim_operations(modem, tmp_path):
  with patch('openpilot.common.hardware.comma.modem.AT_LOCK', str(tmp_path / 'modem.lock')), \
       patch('openpilot.common.hardware.comma.modem.fcntl.flock', side_effect=BlockingIOError):
    assert modem._do_resetting() == State.RESETTING
  assert modem._last_reset is None
  modem._ppp.kill.assert_not_called()


def test_reset_sends_command_and_records_cooldown(modem, tmp_path):
  for _ in range(PPPSession.MAX_FAILS):
    modem._ppp.record_fail()
  with patch('openpilot.common.hardware.comma.modem.AT_LOCK', str(tmp_path / 'modem.lock')), \
       patch('openpilot.common.hardware.comma.modem._serial_port') as serial, \
       patch('openpilot.common.hardware.comma.modem.os.write') as write, \
       patch('openpilot.common.hardware.comma.modem.termios.tcflush'), \
       patch('openpilot.common.hardware.comma.modem.termios.tcdrain'), \
       patch('openpilot.common.hardware.comma.modem.time.monotonic', return_value=1000):
    serial.return_value.__enter__.return_value = 42
    assert modem._do_resetting() == State.DISCONNECTING
    write.assert_called_once_with(42, b'AT+CFUN=1,1\r')
    # A failed connection after reset reinitializes without resetting the modem again.
    assert modem._handle_pppd_exit() == State.DISCONNECTING
  assert modem._last_reset == 1000
  modem._ppp.kill.assert_called_once()
  modem._ppp.cleanup_routes.assert_called_once()
