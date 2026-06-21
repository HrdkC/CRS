from database.stage_manager import (
    StageManager
)

StageManager.create_stage(
    machine_id=1,
    stage_type="FIRST_STAGE"
)

StageManager.create_stage(
    machine_id=1,
    stage_type="SECOND_STAGE"
)

print(
    "P01 Stages Created"
)