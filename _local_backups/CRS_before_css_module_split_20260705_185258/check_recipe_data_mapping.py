from database.database import get_connection

conn = get_connection()
cur = conn.cursor()

print("=== plc_tags columns ===")
cur.execute("PRAGMA table_info(plc_tags)")
columns = [row["name"] if hasattr(row, "keys") else row[1] for row in cur.fetchall()]
for col in columns:
    print(col)

wanted = [
    "id",
    "machine_id",
    "stage_id",
    "tag_name",
    "tag_purpose",
    "tag_type",
    "data_type",
    "is_array",
    "array_start",
    "array_end",
    "array_size",
    "active",
    "is_active",
]

select_cols = [c for c in wanted if c in columns]

print("\n=== CRS recipe data mapping ===")
sql = f"""
SELECT {", ".join(select_cols)}
FROM plc_tags
WHERE tag_name IN ('CRS_Recipe_Data', 'CRS_Test_Recipe_Data')
ORDER BY machine_id, stage_id, tag_name
"""
cur.execute(sql)

for row in cur.fetchall():
    print(dict(row))

conn.close()
