from database.database import get_connection

conn = get_connection()

cursor = conn.cursor()

for table_name in [

    "recipe_master",

    "recipe_parameters"

]:

    cursor.execute("""

    SELECT name

    FROM sqlite_master

    WHERE type='table'

    AND name=?

    """, (

        table_name,

    ))

    row = cursor.fetchone()

    if row:

        print(
            f"✓ {table_name} EXISTS"
        )

    else:

        print(
            f"✗ {table_name} NOT FOUND"
        )

conn.close()