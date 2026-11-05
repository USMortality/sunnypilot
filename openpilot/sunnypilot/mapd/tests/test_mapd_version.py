"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
from openpilot.sunnypilot import get_file_hash
from openpilot.sunnypilot.mapd import MAPD_PATH, MAPD_HASH_PATH
from unittest import TestCase


class TestMapdVersion(TestCase):
  def test_compare_versions(self):
    mapd_hash = get_file_hash(MAPD_PATH)

    with open(MAPD_HASH_PATH) as f:
      current_hash = f.read().strip()

    assert current_hash == mapd_hash, "Run bash openpilot/third_party/mapd_pfeiferj/build.sh to rebuild mapd and its checksum"
