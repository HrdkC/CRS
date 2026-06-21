# check_indexes.py

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

import sqlite3

conn = sqlite3.connect("database/recipe.db")
cursor = conn.cursor()

cursor.execute("""
SELECT
    name,
    type,
    tbl_name
FROM sqlite_master
WHERE type='index'
ORDER BY name
""")

for row in cursor.fetchall():
    print(row)

conn.close()

