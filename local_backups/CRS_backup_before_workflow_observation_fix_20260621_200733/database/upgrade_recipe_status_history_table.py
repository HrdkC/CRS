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


def upgrade_recipe_status_history_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        PRAGMA table_info(
            recipe_status_history
        )
        """
    )

    columns = [

        row["name"]

        for row in cursor.fetchall()

    ]

    if "remarks" not in columns:

        cursor.execute(
            """
            ALTER TABLE
            recipe_status_history

            ADD COLUMN remarks TEXT
            """
        )

        print(
            "Added remarks"
        )

    else:

        print(
            "remarks already exists"
        )

    conn.commit()

    conn.close()

    print(
        "recipe_status_history upgraded"
    )


if __name__ == "__main__":

    upgrade_recipe_status_history_table()