import os
import sys

sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            ".."
        )
    )
)

from database.plc_registry_import_manager import (
    PLCRegistryImportManager
)


preview = PLCRegistryImportManager.build_preview(
    suffix_stage_map={
        "KM": "FIRST_STAGE",
        "PU": "SECOND_STAGE"
    },
    create_missing_machines=False,
    create_missing_stages=False,
    default_family_id=None
)

assert isinstance(
    preview,
    list
)

if preview:

    assert "plc_name" in preview[0]

    assert "status" in preview[0]

print(
    "PLC Registry Import Preview Test Passed"
)
