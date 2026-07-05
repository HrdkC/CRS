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

from database.plc_parameter_mapping_manager import (
    PLCParameterMappingManager
)

mappings = PLCParameterMappingManager.list_mappings(
    "P15KM"
)

for row in mappings:

    print(
        dict(row)
    )