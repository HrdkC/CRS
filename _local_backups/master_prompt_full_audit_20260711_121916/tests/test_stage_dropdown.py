from database.stage_manager import (
    StageManager
)

stages = (
    StageManager.get_all_stages_with_machine()
)

for stage in stages:

    print(

        stage["id"],

        stage["machine_code"],

        stage["stage_type"]

    )