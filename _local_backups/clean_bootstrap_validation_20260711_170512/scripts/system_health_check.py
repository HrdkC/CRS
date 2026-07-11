# system_health_check.py

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

from database.plc_manager_legacy import PLCManager
from database.recipe_manager import RecipeManager
from database.audit_manager import AuditManager

# from utils.project_path import *

from database.plc_manager_legacy import PLCManager
from database.recipe_manager import RecipeManager
from database.audit_manager import AuditManager

print("\n===== PLCs =====")

for plc in PLCManager.list_plcs():

    print(dict(plc))

print("\n===== Recipes =====")

for recipe in RecipeManager.list_recipes():

    print(dict(recipe))

print("\n===== Recent Audit =====")

history = AuditManager.get_audit_history(10)

for row in history:

    print(row)