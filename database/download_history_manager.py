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


class DownloadHistoryManager:

    @staticmethod
    def create_download_record(

        plc_name,

        recipe_code,

        recipe_version,

        downloaded_by="system"

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO
            recipe_download_history
            (

                plc_name,

                recipe_code,

                recipe_version,

                download_status,

                downloaded_by,

                download_start_time

            )

            VALUES
            (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (

                plc_name,

                recipe_code,

                recipe_version,

                "IN_PROGRESS",

                downloaded_by

            )
        )

        download_id = (
            cursor.lastrowid
        )

        conn.commit()

        conn.close()

        return download_id

    @staticmethod
    def complete_download_record(

        download_id,

        message="SUCCESS"

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE
            recipe_download_history

            SET

                download_status = ?,

                download_end_time =
                CURRENT_TIMESTAMP,

                download_message = ?

            WHERE id = ?
            """,
            (

                "SUCCESS",

                message,

                download_id

            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def fail_download_record(

        download_id,

        message

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE
            recipe_download_history

            SET

                download_status = ?,

                download_end_time =
                CURRENT_TIMESTAMP,

                download_message = ?

            WHERE id = ?
            """,
            (

                "FAILED",

                message,

                download_id

            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_history():

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipe_download_history

            ORDER BY id DESC
            """
        )

        rows = cursor.fetchall()

        conn.close()

        return rows