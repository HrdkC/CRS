from database.machine_manager import (
    MachineManager
)

MachineManager.create_machine(

    machine_code="P01",

    family_id=1,

    description="PCR TBM P01",

    created_by="admin"
)

print(
    "Machine Created"
)