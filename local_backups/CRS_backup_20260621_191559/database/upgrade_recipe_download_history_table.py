from database.database import (
    get_connection
)


def upgrade_recipe_download_history_table():

    conn = get_connection()

    cursor = conn.cursor()

    columns = []

    cursor.execute(
        """
        PRAGMA table_info(
            recipe_download_history
        )
        """
    )

    for row in cursor.fetchall():

        columns.append(
            row["name"]
        )

    if (
        "download_start_time"
        not in columns
    ):

        cursor.execute(
            """
            ALTER TABLE
            recipe_download_history

            ADD COLUMN
            download_start_time
            TIMESTAMP
            """
        )

        print(
            "Added download_start_time"
        )

    if (
        "download_end_time"
        not in columns
    ):

        cursor.execute(
            """
            ALTER TABLE
            recipe_download_history

            ADD COLUMN
            download_end_time
            TIMESTAMP
            """
        )

        print(
            "Added download_end_time"
        )

    if (
        "download_message"
        not in columns
    ):

        cursor.execute(
            """
            ALTER TABLE
            recipe_download_history

            ADD COLUMN
            download_message
            TEXT
            """
        )

        print(
            "Added download_message"
        )

    cursor.execute(
        """
        UPDATE
            recipe_download_history

        SET
            download_start_time =
            download_time

        WHERE
            download_start_time
            IS NULL
        """
    )

    conn.commit()

    conn.close()

    print(
        "recipe_download_history upgraded"
    )


if __name__ == "__main__":

    upgrade_recipe_download_history_table()