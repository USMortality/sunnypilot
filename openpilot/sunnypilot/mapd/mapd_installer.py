#!/usr/bin/env python3
"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.

Verify the bundled patched mapd; never replace it with stock upstream mapd.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import TYPE_CHECKING

from openpilot.common.hardware.hw import Paths
from openpilot.common.spinner import Spinner
from openpilot.sunnypilot import get_file_hash
from openpilot.sunnypilot.mapd import MAPD_PATH, MAPD_BIN_DIR, MAPD_HASH_PATH

if TYPE_CHECKING:
  from openpilot.common.params import Params

VERSION = "v1.12.0-slc.1"


def verify_bundled_mapd() -> None:
  try:
    expected = Path(MAPD_HASH_PATH).read_text().strip()
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
      raise ValueError("invalid checksum metadata")
    if get_file_hash(MAPD_PATH) != expected:
      raise ValueError("binary checksum mismatch")
  except (OSError, ValueError) as error:
    raise RuntimeError("Bundled patched mapd is missing or invalid. Restore it from this checkout or rebuild with "
                       "openpilot/third_party/mapd_pfeiferj/build.sh; stock upstream mapd is not compatible.") from error


def update_installed_version(version: str, params: Params | None = None) -> None:
  # mapd_manager also calls this at startup. Do not label an unverified binary
  # as the patched version, even on prebuilt installations.
  verify_bundled_mapd()
  if params is None:
    from openpilot.common.params import Params
    params = Params()
  params.put("MapdVersion", version, block=True)


class MapdInstallManager:
  def __init__(self, spinner_ref: Spinner):
    from openpilot.common.params import Params
    self._spinner = spinner_ref
    self._params = Params()

  @staticmethod
  def ensure_directories_exist() -> None:
    os.makedirs(Paths.mapd_root(), exist_ok=True)
    os.makedirs(MAPD_BIN_DIR, exist_ok=True)

  def install_bundled(self) -> None:
    self.ensure_directories_exist()
    verify_bundled_mapd()
    # Copies can lose their executable bit. Repair only verified content.
    path = Path(MAPD_PATH)
    path.chmod(stat.S_IMODE(path.stat().st_mode) | stat.S_IXUSR)
    update_installed_version(VERSION, self._params)
    self._spinner.update(f"Bundled patched mapd verified: {VERSION}")


if __name__ == "__main__":
  spinner = Spinner()
  try:
    MapdInstallManager(spinner).install_bundled()
  finally:
    spinner.close()
