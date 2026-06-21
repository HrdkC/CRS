# tests/test_recipe_parameters_columns.py

from database.database import get_connection

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    "PRAGMA table_info(recipe_parameters)"
)

for row in cursor.fetchall():

    print(dict(row))

conn.close()