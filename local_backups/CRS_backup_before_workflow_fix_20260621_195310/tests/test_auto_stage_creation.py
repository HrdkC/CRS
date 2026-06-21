from database.machine_manager import (
    MachineManager
)

from database.stage_manager import (
    StageManager
)

MachineManager.create_machine(

    machine_code="P02",

    family_id=1,

    description="PCR TBM P02",

    created_by="admin"

)

stages = (
    StageManager.get_all_stages()
)

for stage in stages:

    print(

        stage["machine_code"],

        stage["stage_type"]

    )