from database.database import (
    get_connection
)

conn = get_connection()

cursor = conn.cursor()

try:

    cursor.execute(
        """
        ALTER TABLE
        recipe_versions

        ADD COLUMN
        recipe_id INTEGER
        """
    )

    print(
        "recipe_id added"
    )

except Exception as ex:

    print(
        ex
    )

try:

    cursor.execute(
        """
        ALTER TABLE
        recipe_versions

        ADD COLUMN
        version_comment TEXT
        """
    )

    print(
        "version_comment added"
    )

except Exception as ex:

    print(
        ex
    )

conn.commit()

conn.close()

print(
    "recipe_versions upgraded"
)