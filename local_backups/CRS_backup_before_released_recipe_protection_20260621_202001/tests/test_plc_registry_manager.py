from database.plc_registry_manager import (
    PLCRegistryManager
)

plcs = (
    PLCRegistryManager.get_all_plcs()
)

print(
    f"PLCs Found: {len(plcs)}"
)

for plc in plcs:

    print(
        plc["plc_name"]
    )