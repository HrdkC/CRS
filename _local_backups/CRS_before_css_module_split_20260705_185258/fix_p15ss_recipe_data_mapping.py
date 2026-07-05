from database.database import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute(
    "UPDATE plc_tags SET tag_purpose = ? WHERE id = ?",
    ("RECIPE_DATA", 21)
)

cur.execute(
    "UPDATE plc_tags SET tag_purpose = ? WHERE id = ?",
    ("TEST_RECIPE_DATA", 23)
)

conn.commit()

cur.execute("""
SELECT id, machine_id, stage_id, tag_name, tag_purpose, tag_type, is_array, array_size
FROM plc_tags
WHERE id IN (21, 23)
ORDER BY tag_name
""")

print("=== Corrected P15 SS recipe data mapping ===")
for row in cur.fetchall():
    print(dict(row))

conn.close()
