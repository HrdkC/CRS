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
PRAGMA table_info(recipe_parameters)
""")

for row in cursor.fetchall():
    print(row)

conn.close()