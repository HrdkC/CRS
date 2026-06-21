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

SELECT name

FROM sqlite_master

WHERE type='table'

ORDER BY name

""")

for row in cursor.fetchall():

    print(
        row["name"]
    )

conn.close()