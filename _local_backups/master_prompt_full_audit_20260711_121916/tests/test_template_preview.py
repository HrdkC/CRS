from database.template_import_manager import (
    TemplateImportManager
)
import time

start = time.time()

rows = (

    TemplateImportManager
    .build_preview(

        excel_file=r"D:\gt9088.xlsx",

        machine_id=5,

        stage_id=11

    )

)

print("SECONDS =",
    round(
        time.time() - start,
        3)
)

print(
    "ROWS =",
    len(rows)
)

print()

for row in rows[:10]:

    print(row)