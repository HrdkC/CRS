from database.tbm_family_manager import (
    TBMFamilyManager
)

families = (
    TBMFamilyManager.get_all_families()
)

print(
    f"Families Found: {len(families)}"
)

for family in families:

    print(
        family["family_name"]
    )