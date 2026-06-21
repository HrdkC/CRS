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

from plc.plc_recipe_manager import (
    PLCRecipeManager
)

PLCRecipeManager.download_recipe_to_plc(

    plc_name="P15KM",

    recipe_code="GT7107"

)