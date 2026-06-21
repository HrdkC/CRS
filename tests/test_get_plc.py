# test_get_plc.py

import sys
import os

ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from database.plc_manager_legacy import PLCManager

plc = PLCManager.get_plc(
    "P15KM"
)

print(plc)

if plc:
    print(dict(plc))