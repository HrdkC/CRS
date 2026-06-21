from database.database import get_connection

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    SELECT DISTINCT
        recipe_code,
        version

    FROM recipe_parameters

    ORDER BY
        recipe_code,
        version
    """
)

versions = cursor.fetchall()

for row in versions:

    cursor.execute(
        """
        INSERT INTO recipe_versions
        (
            recipe_code,
            version,
            created_by
        )
        VALUES
        (
            ?, ?, ?
        )
        """,
        (
            row["recipe_code"],
            row["version"],
            "SYSTEM_MIGRATION"
        )
    )

conn.commit()

print(
    f"Migrated {len(versions)} versions"
)

conn.close()