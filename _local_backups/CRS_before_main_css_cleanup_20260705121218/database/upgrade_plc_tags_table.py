import sys
import os

ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if ROOT_DIR not in sys.path:

    sys.path.insert(
        0,
        ROOT_DIR
    )

from database.database import (
    get_connection
)


def upgrade_plc_tags_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        PRAGMA table_info(plc_tags)
        """
    )

    columns = [

        row["name"]

        for row in cursor.fetchall()

    ]

    if "tag_purpose" not in columns:

        cursor.execute(
            """
            ALTER TABLE plc_tags

            ADD COLUMN tag_purpose TEXT
            """
        )

        print(
            "Added tag_purpose"
        )

    else:

        print(
            "tag_purpose already exists"
        )

    conn.commit()

    conn.close()

    print(
        "plc_tags upgraded"
    )


if __name__ == "__main__":

    upgrade_plc_tags_table()