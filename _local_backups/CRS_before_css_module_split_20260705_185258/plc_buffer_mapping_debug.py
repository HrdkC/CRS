from database.database import get_connection

conn = get_connection()
cur = conn.cursor()

print("=== plc_tags columns ===")
cur.execute("PRAGMA table_info(plc_tags)")
columns = [row["name"] if hasattr(row, "keys") else row[1] for row in cur.fetchall()]
print(columns)

wanted_cols = [
    "id",
    "machine_id",
    "stage_id",
    "tag_name",
    "tag_type",
    "tag_purpose",
    "is_array",
    "array_size",
    "array_start_index",
    "array_end_index",
    "description",
    "created_by",
    "created_at",
]

select_cols = [col for col in wanted_cols if col in columns]

print("\n=== PLC TAGS P15 SS / CRS DOWNLOAD TAGS ===")
cur.execute(f"""
SELECT {", ".join(select_cols)}
FROM plc_tags
WHERE machine_id = 5
  AND stage_id = 12
  AND (
        tag_name LIKE 'CRS_%'
        OR tag_purpose IN (
            'RECIPE_DATA',
            'TEST_RECIPE_DATA',
            'RECIPE_CODE',
            'DOWNLOAD_ENABLE',
            'MACHINE_IN_MANUAL',
            'DOWNLOAD_REQUEST',
            'DOWNLOAD_COMPLETE',
            'DOWNLOAD_ACK',
            'DOWNLOAD_BUSY',
            'DOWNLOAD_ERROR',
            'DOWNLOAD_RESULT'
        )
      )
ORDER BY tag_purpose, tag_name
""")

for row in cur.fetchall():
    print(dict(row))

print("\n=== STAGE PLC SETUP RULE TABLES ===")
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r["name"] for r in cur.fetchall()]

for table_name in tables:
    if (
        "setup" in table_name.lower()
        or "readiness" in table_name.lower()
        or "tag" in table_name.lower()
    ):
        print(table_name)

for table in tables:
    if table in (
        "stage_plc_tag_setup_rules",
        "stage_plc_tag_requirements",
        "plc_stage_tag_setup_rules"
    ):
        print("\n==", table, "==")

        cur.execute(f"PRAGMA table_info({table})")
        table_columns = [row["name"] if hasattr(row, "keys") else row[1] for row in cur.fetchall()]
        print("columns:", table_columns)

        order_col = "display_order" if "display_order" in table_columns else "id"

        cur.execute(f"""
        SELECT *
        FROM {table}
        WHERE machine_id = 5
          AND stage_id = 12
        ORDER BY {order_col}
        """)

        for row in cur.fetchall():
            print(dict(row))

conn.close()
