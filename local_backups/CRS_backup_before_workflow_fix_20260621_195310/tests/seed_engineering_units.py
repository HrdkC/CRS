from database.database import get_connection

conn = get_connection()

cursor = conn.cursor()

units = [

    ("mm", "Millimeter"),
    ("bar", "Pressure"),
    ("°C", "Temperature"),
    ("rpm", "Speed"),
    ("sec", "Seconds"),
    ("%", "Percentage"),
    ("kg", "Weight"),
    ("N", "Force"),
    ("mm/s", "Velocity")

]

for unit_code, description in units:

    cursor.execute(
        """
        INSERT OR IGNORE INTO engineering_units
        (
            unit_code,
            description
        )
        VALUES
        (
            ?, ?
        )
        """,
        (
            unit_code,
            description
        )
    )

conn.commit()

conn.close()

print(
    f"Inserted {len(units)} units"
)