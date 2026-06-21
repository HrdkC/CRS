from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS
    recipe_version_values
    (

        id INTEGER
        PRIMARY KEY AUTOINCREMENT,

        recipe_version_id INTEGER
        NOT NULL,

        parameter_definition_id INTEGER
        NOT NULL,

        parameter_value REAL,

        created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP

    )
    """
)

conn.commit()

conn.close()

print(
    "Recipe Version Values Table Created"
)