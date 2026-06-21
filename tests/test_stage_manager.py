from database.stage_manager import (
    StageManager
)

stages = (
    StageManager.get_all_stages()
)

print(
    f"Stages Found: {len(stages)}"
)

for stage in stages:

    print(

        stage["machine_code"],

        stage["stage_type"]

    )