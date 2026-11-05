import hashlib
import stat
from unittest.mock import Mock

import pytest
import requests

from openpilot.sunnypilot.mapd import mapd_installer as installer


@pytest.fixture
def bundle(tmp_path, monkeypatch):
  binary, checksum = tmp_path / 'mapd', tmp_path / 'mapd.sha256'
  content = b'patched mapd test artifact'
  binary.write_bytes(content)
  checksum.write_text(hashlib.sha256(content).hexdigest() + '\n')
  monkeypatch.setattr(installer, 'MAPD_PATH', str(binary))
  monkeypatch.setattr(installer, 'MAPD_HASH_PATH', str(checksum))
  monkeypatch.setattr(installer, 'MAPD_BIN_DIR', str(tmp_path))
  monkeypatch.setattr(installer.Paths, 'mapd_root', lambda: str(tmp_path / 'maps'))
  monkeypatch.setattr(requests, 'get', Mock(side_effect=AssertionError('bundled installation must not download upstream mapd')))
  return binary, checksum, content


@pytest.mark.parametrize('stored_version', ['', 'v1.12.0', 'older-version'])
def test_valid_bundle_is_never_replaced_due_to_version_metadata(bundle, stored_version):
  binary, _, content = bundle
  manager = installer.MapdInstallManager.__new__(installer.MapdInstallManager)
  manager._spinner, manager._params = Mock(), Mock()
  manager._params.get.return_value = stored_version
  manager.install_bundled()
  assert binary.read_bytes() == content
  assert binary.stat().st_mode & stat.S_IXUSR
  manager._params.put.assert_called_once_with('MapdVersion', installer.VERSION, block=True)


@pytest.mark.parametrize('failure', ['missing_binary', 'stock_binary', 'missing_checksum', 'invalid_checksum'])
def test_invalid_bundle_cannot_be_marked_installed_or_replaced(bundle, failure):
  binary, checksum, _ = bundle
  if failure == 'missing_binary':
    binary.unlink()
  elif failure == 'stock_binary':
    binary.write_bytes(b'unpatched upstream mapd')
  elif failure == 'missing_checksum':
    checksum.unlink()
  else:
    checksum.write_text('not a SHA-256 checksum')
  before = binary.read_bytes() if binary.exists() else None
  params = Mock()
  with pytest.raises(RuntimeError, match='stock upstream mapd is not compatible'):
    installer.update_installed_version(installer.VERSION, params)
  params.put.assert_not_called()
  assert (binary.read_bytes() if binary.exists() else None) == before


def test_install_rejects_invalid_bundle_before_repairing_permissions(bundle):
  binary, _, _ = bundle
  binary.write_bytes(b'wrong binary')
  binary.chmod(0o600)
  manager = installer.MapdInstallManager.__new__(installer.MapdInstallManager)
  manager._spinner, manager._params = Mock(), Mock()
  with pytest.raises(RuntimeError):
    manager.install_bundled()
  assert not binary.stat().st_mode & stat.S_IXUSR
  manager._params.put.assert_not_called()
