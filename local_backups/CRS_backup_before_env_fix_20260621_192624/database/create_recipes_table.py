from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS recipes
    (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        machine_id INTEGER NOT NULL,

        stage_id INTEGER NOT NULL,

        recipe_code TEXT NOT NULL,

        recipe_name TEXT NOT NULL,

        version INTEGER NOT NULL DEFAULT 1,

        status TEXT NOT NULL DEFAULT 'DRAFT',

        created_by TEXT,

        created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

        updated_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
    )
    """
)

cursor.execute(
    """
    CREATE UNIQUE INDEX IF NOT EXISTS
    idx_recipe_unique

    ON recipes
    (

        machine_id,

        stage_id,

        recipe_code,

        version
    )
    """
)

conn.commit()

conn.close()

print(
    "Recipes Table Created"
)