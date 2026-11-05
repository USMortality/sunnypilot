import os
from openpilot.common.basedir import BASEDIR

MAPD_BIN_DIR = os.path.join(BASEDIR, 'openpilot', 'third_party/mapd_pfeiferj')
MAPD_PATH = os.path.join(MAPD_BIN_DIR, 'mapd')
MAPD_HASH_PATH = os.path.join(MAPD_BIN_DIR, 'mapd.sha256')
