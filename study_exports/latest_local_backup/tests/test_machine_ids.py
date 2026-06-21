from database.machine_manager import (
    MachineManager
)

machines = (
    MachineManager.get_all_machines()
)

for machine in machines:

    print(

        machine["id"],

        machine["machine_code"]

    )