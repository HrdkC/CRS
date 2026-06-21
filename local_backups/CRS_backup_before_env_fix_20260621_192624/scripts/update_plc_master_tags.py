import sys
import os

ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if ROOT_DIR not in sys.path:

    sys.path.insert(
        0,
        ROOT_DIR
    )

from database.database import get_connection

conn = get_connection()
cursor = conn.cursor()

columns = [

    "recipe_data_tag TEXT",

    "phase_data_tag TEXT",

    "download_request_tag TEXT",

    "download_complete_tag TEXT",

    "upload_request_tag TEXT",

    "upload_complete_tag TEXT"

]

for column in columns:

    try:

        cursor.execute(
            f"""
            ALTER TABLE plc_master
            ADD COLUMN {column}
            """
        )

        print(
            f"Added : {column}"
        )

    except Exception as e:

        print(
            f"Skipped : {column}"
        )

conn.commit()
conn.close()

print(
    "PLC Master Updated"
)