from database.database import (
    get_connection
)


def upgrade_recipe_phase_control_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        PRAGMA table_info(
            recipe_phase_control
        )
        """
    )

    columns = [

        row["name"]

        for row in cursor.fetchall()

    ]

    if "recipe_id" not in columns:

        cursor.execute(
            """
            ALTER TABLE
            recipe_phase_control

            ADD COLUMN
            recipe_id INTEGER
            """
        )

        print(
            "recipe_id added"
        )

    conn.commit()

    conn.close()

    print(
        "recipe_phase_control upgraded"
    )


if __name__ == "__main__":

    upgrade_recipe_phase_control_table()