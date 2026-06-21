# verify_recipe_master_data.py

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
conn.row_factory = sqlite3.Row

cursor = conn.cursor()

cursor.execute("""
SELECT *
FROM recipe_master
""")

for row in cursor.fetchall():

    print(dict(row))

conn.close()