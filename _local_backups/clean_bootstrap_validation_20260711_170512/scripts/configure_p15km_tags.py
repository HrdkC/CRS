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

cursor.execute("""

UPDATE plc_master

SET

    recipe_data_tag = ?,

    phase_data_tag = ?,

    download_request_tag = ?,

    download_complete_tag = ?,

    upload_request_tag = ?,

    upload_complete_tag = ?

WHERE plc_name = ?

""", (

    "CRS_Recipe_Data",

    "CRS_Recipe_PhaseData",

    "CRS_Download_Request",

    "CRS_Download_Complete",

    "CRS_Upload_Request",

    "CRS_Upload_Complete",

    "P15KM"

))

conn.commit()
conn.close()

print(
    "P15KM CRS Tags Configured"
)