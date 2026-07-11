# verify_tables.py

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
    "user_sessions",
    "recipe_master",
    "recipe_parameters",
    "recipe_phase_control",
    "recipe_plc_mapping",
    "audit_log",
    "recipe_upload_history"
]

for table in tables:

    cursor.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
    )

    result = cursor.fetchone()

    if result:
        print(f"✓ {table}")
    else:
        print(f"✗ {table}")

conn.close()

