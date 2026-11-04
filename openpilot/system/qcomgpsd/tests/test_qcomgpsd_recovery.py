"""Exercise the daemon recovery loop with hardware I/O and IPC substituted."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS
from unittest.mock import Mock, call

import pytest


class EndSession(BaseException):
  pass


@pytest.fixture
def gps(monkeypatch):
  # Loading the actual daemon must not bind live IPC sockets or toggle GPIOs.
  ipc = ModuleType('openpilot.cereal.messaging')
  ipc.PubMaster = Mock(return_value=Mock())
  with monkeypatch.context() as imports:
    imports.setitem(sys.modules, 'openpilot.cereal.messaging', ipc)
    path = Path(__file__).resolve().parents[1] / 'qcomgpsd.py'
    spec = importlib.util.spec_from_file_location('gps_recovery_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
  module.messaging = ipc
  monkeypatch.setattr(module, 'wait_for_modem', Mock())
  monkeypatch.setattr(module, 'setup_quectel', Mock())
  monkeypatch.setattr(module, 'teardown_quectel', Mock())
  monkeypatch.setattr(module, 'gpio_init', Mock())
  monkeypatch.setattr(module, 'gpio_set', Mock())
  monkeypatch.setattr(module, 'time', NS(sleep=Mock()))
  monkeypatch.setattr(module.cloudlog, 'exception', Mock())
  monkeypatch.setattr(module.cloudlog, 'warning', Mock())
  monkeypatch.setattr(module.signal, 'signal', Mock())
  return module


@pytest.mark.parametrize('failure', ['disconnect', 'setup', 'missing_device'])
def test_gps_reinitializes_and_publishes_after_modem_failure(gps, monkeypatch, failure):
  old, new = Mock(), Mock()
  if failure == 'missing_device':
    sessions = [FileNotFoundError('modem temporarily absent'), new]
  else:
    sessions = [old, new]
  monkeypatch.setattr(gps, 'ModemDiag', Mock(side_effect=sessions))
  if failure == 'setup':
    gps.setup_quectel.side_effect = [RuntimeError('modem still resetting'), None]
  received = []
  def messages(diag, pm):
    received.append(diag)
    if diag is old:
      raise ConnectionError('old USB port disconnected')
    pm.send('gpsLocation', 'fresh fix')
    raise EndSession()
  monkeypatch.setattr(gps, 'run_messages', messages)
  with pytest.raises(EndSession):
    gps.main()
  assert gps.ModemDiag.call_count == gps.wait_for_modem.call_count == 2
  assert received == ([old, new] if failure == 'disconnect' else [new])
  if failure != 'missing_device':
    old.serial.close.assert_called_once()
  new.serial.close.assert_called_once()
  gps.time.sleep.assert_called_once_with(1.)
  # Recovery reuses the publisher; it cannot leave GPS disconnected from IPC.
  gps.messaging.PubMaster.assert_called_once_with(['qcomGnss', 'gpsLocation'])
  gps.messaging.PubMaster.return_value.send.assert_called_once_with('gpsLocation', 'fresh fix')
  assert gps.setup_quectel.call_args_list[-1] == call(new)


@pytest.mark.parametrize('teardown_fails', [False, True])
def test_intended_shutdown_closes_port_without_reconnecting(gps, monkeypatch, teardown_fails):
  diag = Mock()
  monkeypatch.setattr(gps, 'ModemDiag', Mock(return_value=diag))
  handlers = {}
  gps.signal.signal.side_effect = lambda sig, callback: handlers.update({sig: callback})
  if teardown_fails:
    gps.teardown_quectel.side_effect = OSError('modem already removed')
  def stop_session(diag, pm):
    handlers[gps.signal.SIGTERM](None, None)
  monkeypatch.setattr(gps, 'run_messages', stop_session)
  with pytest.raises(SystemExit) as e:
    gps.main()
  assert e.value.code == 0
  diag.serial.close.assert_called_once()
  gps.teardown_quectel.assert_called_once_with(diag)
  gps.gpio_set.assert_called_with(gps.GPIO.GNSS_PWR_EN, False)
  gps.time.sleep.assert_not_called()
  gps.ModemDiag.assert_called_once()
