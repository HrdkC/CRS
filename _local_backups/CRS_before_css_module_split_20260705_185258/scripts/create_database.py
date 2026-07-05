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

from database.models import *

create_plc_master()

create_users()

create_recipe_master()

create_recipe_parameters()

create_recipe_phase_control()

create_audit_log()

create_recipe_upload_history()

create_recipe_download_history()

create_user_sessions()

create_recipe_plc_mapping()

create_plc_parameter_mapping()

create_recipe_parameters_index()

create_phase_control_index()

print("Database Created Successfully")


