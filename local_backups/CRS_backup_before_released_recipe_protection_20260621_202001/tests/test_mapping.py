# from utils.project_path import *
import sys
import os

ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if ROOT_DIR not in sys.path:

    sys.path.insert(
        0,
        ROOT_DIR
    )

from database.plc_parameter_mapping_manager import (
    PLCParameterMappingManager
)

PLCParameterMappingManager.add_mapping(

    plc_name="P15KM",

    parameter_name="Carcass Setting",

    plc_array_index=0

)

PLCParameterMappingManager.add_mapping(

    plc_name="P15KM",

    parameter_name="Stretch Position",

    plc_array_index=1

)