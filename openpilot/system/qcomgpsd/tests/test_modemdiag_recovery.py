"""GNSS must recover its diagnostic transport after a modem USB reset."""
import os
from unittest.mock import Mock

import pytest

from openpilot.common.serial import Serial
from openpilot.system.qcomgpsd import modemdiag
from openpilot.system.qcomgpsd.modemdiag import ModemDiag, find_diag_port


def usb_interface(root, tty, number='00', vendor='2c7c', device='modem'):
  usb = root / 'devices' / device
  interface = usb / f'interface-{number}'
  interface.mkdir(parents=True, exist_ok=True)
  (usb / 'idVendor').write_text(vendor)
  (interface / 'bInterfaceNumber').write_text(number)
  node = root / 'tty' / tty
  node.mkdir(parents=True)
  (node / 'device').symlink_to(interface, target_is_directory=True)


def test_diag_interface_is_found_after_modem_ports_are_renumbered(tmp_path):
  usb_interface(tmp_path, 'ttyUSB1')
  usb_interface(tmp_path, 'ttyUSB2', number='01')
  usb_interface(tmp_path, 'ttyUSB3', number='02')
  usb_interface(tmp_path, 'ttyUSB4', number='03')
  assert find_diag_port(tmp_path / 'tty') == '/dev/ttyUSB1'


def test_port_number_does_not_override_usb_interface_identity(tmp_path):
  usb_interface(tmp_path, 'ttyUSB0', number='02')
  usb_interface(tmp_path, 'ttyUSB4', number='00')
  assert find_diag_port(tmp_path / 'tty') == '/dev/ttyUSB4'


@pytest.mark.parametrize('state', ['absent', 'other_vendor', 'multiple_modems', 'disconnecting'])
def test_no_blind_fallback_to_unverified_diag_port(tmp_path, state):
  if state == 'other_vendor':
    usb_interface(tmp_path, 'ttyUSB0', vendor='0403')
  elif state == 'multiple_modems':
    usb_interface(tmp_path, 'ttyUSB0', device='one')
    usb_interface(tmp_path, 'ttyUSB4', device='two')
  elif state == 'disconnecting':
    node = tmp_path / 'tty' / 'ttyUSB0'
    node.mkdir(parents=True)
    (node / 'device').symlink_to(tmp_path / 'removed-device')
  with pytest.raises(OSError, match='no unique Quectel'):
    find_diag_port(tmp_path / 'tty')


def receiver_on_pipe(read_fd):
  serial = Serial.__new__(Serial)
  serial._fd = read_fd
  serial._timeout = 0
  serial._exclusive = False
  diag = ModemDiag.__new__(ModemDiag)
  diag.serial = serial
  diag.pend = b''
  return diag


def test_disconnected_port_exits_instead_of_busy_looping():
  read_fd, write_fd = os.pipe()
  os.close(write_fd)
  diag = receiver_on_pipe(read_fd)
  try:
    with pytest.raises(ConnectionError, match='disconnected'):
      diag.recv(timeout=.1)
  finally:
    diag.serial.close()


def test_silent_modem_exits_for_session_recovery():
  read_fd, write_fd = os.pipe()
  diag = receiver_on_pipe(read_fd)
  try:
    with pytest.raises(TimeoutError, match='timed out'):
      diag.recv(timeout=.01)
  finally:
    diag.serial.close()
    os.close(write_fd)


def test_pending_frame_and_fragmented_stream_still_decode():
  read_fd, write_fd = os.pipe()
  diag = receiver_on_pipe(read_fd)
  first = diag.hdlc_encapsulate(b'\x10first\x7d\x7e')
  second = diag.hdlc_encapsulate(b'\x73second')
  try:
    diag.pend = first[:3]
    os.write(write_fd, first[3:] + second)
    assert diag.recv(timeout=.1) == (0x10, b'first\x7d\x7e')
    # The second packet is already buffered; it does not need another read.
    assert diag.recv(timeout=0) == (0x73, b'second')
  finally:
    diag.serial.close()
    os.close(write_fd)


def test_restarted_receiver_opens_newly_enumerated_port(tmp_path, monkeypatch):
  usb_interface(tmp_path, 'ttyUSB0')
  monkeypatch.setattr(modemdiag, 'find_diag_port', lambda: find_diag_port(tmp_path / 'tty'))
  factory = Mock(return_value=Mock())
  monkeypatch.setattr(modemdiag, 'Serial', factory)
  ModemDiag()
  assert factory.call_args.args[0] == '/dev/ttyUSB0'
  (tmp_path / 'tty' / 'ttyUSB0' / 'device').unlink()
  usb_interface(tmp_path, 'ttyUSB1')
  ModemDiag()
  assert factory.call_args.args[0] == '/dev/ttyUSB1'


@pytest.mark.parametrize('failed_step', ['flush', 'reset_input_buffer', 'reset_output_buffer'])
def test_hot_unplug_during_open_closes_partial_session(monkeypatch, failed_step):
  serial = Mock()
  getattr(serial, failed_step).side_effect = OSError('USB device removed')
  monkeypatch.setattr(modemdiag, 'Serial', Mock(return_value=serial))
  monkeypatch.setattr(modemdiag, 'find_diag_port', lambda: '/dev/ttyUSB1')
  with pytest.raises(OSError, match='removed'):
    ModemDiag()
  serial.close.assert_called_once()
