from database.machine_manager import (
    MachineManager
)

try:

    MachineManager.create_machine(

        machine_code="p03",

        family_id=1,

        description="Duplicate Test"

    )

    print(
        "Machine Created"
    )

except Exception as e:

    print(
        f"Duplicate Blocked: {e}"
    )