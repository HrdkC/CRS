import os
import sys

# Ensure project root is available in Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.database import get_connection


def cleanup_legacy_plc_tag_typo():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, tag_name
        FROM plc_tags
        WHERE UPPER(tag_name) = 'CSR_DOWNLOAD_COMPLETE'
    """)
    rows = cursor.fetchall()

    if not rows:
        print("No legacy typo tag found: CSR_Download_Complete")
        conn.close()
        return

    cursor.execute("""
        DELETE FROM plc_tags
        WHERE UPPER(tag_name) = 'CSR_DOWNLOAD_COMPLETE'
    """)

    conn.commit()
    conn.close()

    print(f"Removed {len(rows)} legacy typo tag row(s): CSR_Download_Complete")


if __name__ == "__main__":
    cleanup_legacy_plc_tag_typo()