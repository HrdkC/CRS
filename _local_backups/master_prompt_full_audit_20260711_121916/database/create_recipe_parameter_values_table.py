from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS
    recipe_parameter_values
    (

        id INTEGER
        PRIMARY KEY AUTOINCREMENT,

        recipe_id INTEGER
        NOT NULL,

        parameter_definition_id INTEGER
        NOT NULL,

        parameter_value REAL,

        is_modified INTEGER
        DEFAULT 0,

        created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

        updated_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(recipe_id)
        REFERENCES recipes(id),

        FOREIGN KEY(parameter_definition_id)
        REFERENCES parameter_definitions(id)
    )
    """
)

cursor.execute(
    """
    CREATE UNIQUE INDEX IF NOT EXISTS
    idx_recipe_parameter_unique

    ON recipe_parameter_values
    (

        recipe_id,

        parameter_definition_id

    )
    """
)

conn.commit()

conn.close()

print(
    "Recipe Parameter Values Table Created"
)