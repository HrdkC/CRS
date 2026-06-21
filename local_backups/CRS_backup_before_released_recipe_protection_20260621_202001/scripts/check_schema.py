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

tables = [
    "plc_master",
    "users",
    "recipe_master",
    "recipe_parameters",
    "audit_log",
    "recipe_upload_history"
]

for table in tables:

    print("\n" + "=" * 80)
    print(f"TABLE : {table}")
    print("=" * 80)

    cursor.execute(
        f"PRAGMA table_info({table})"
    )

    print(
        f"{'Column':<25}"
        f"{'Type':<15}"
        f"{'PK':<5}"
        f"{'Default'}"
    )

    print("-" * 80)

    for column in cursor.fetchall():

        print(
            f"{column[1]:<25}"
            f"{column[2]:<15}"
            f"{column[5]:<5}"
            f"{column[4]}"
        )

conn.close()

