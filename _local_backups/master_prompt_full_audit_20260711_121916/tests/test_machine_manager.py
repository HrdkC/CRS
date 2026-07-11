from database.machine_manager import (
    MachineManager
)

machines = (
    MachineManager.get_all_machines()
)

print(
    f"Machines Found: {len(machines)}"
)

for machine in machines:

    print(
        machine["machine_code"]
    )