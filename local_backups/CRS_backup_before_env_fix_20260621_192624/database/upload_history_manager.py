from database.database import get_connection


class UploadHistoryManager:

    @staticmethod
    def log_upload(

        plc_name,

        recipe_code,

        recipe_version,

        status,

        uploaded_by="PLC_UPLOAD",

        remarks=None

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO recipe_upload_history (

            plc_name,

            recipe_code,

            recipe_version,

            uploaded_by,

            status,

            remarks

        )

        VALUES (?, ?, ?, ?, ?, ?)
        """, (

            plc_name,

            recipe_code,

            recipe_version,

            uploaded_by,

            status,

            remarks

        ))

        conn.commit()

        conn.close()

        print(
            f"Upload Logged : {recipe_code}"
        )

    @staticmethod
    def get_history():

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
        SELECT *

        FROM recipe_upload_history

        ORDER BY id DESC
        """)

        rows = cursor.fetchall()

        conn.close()

        return rows
    
    @staticmethod
    def get_plc_history(

        plc_name

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
        SELECT *

        FROM recipe_upload_history

        WHERE plc_name = ?

        ORDER BY id DESC
        """, (

            plc_name,

        ))

        rows = cursor.fetchall()

        conn.close()

        return rows

    @staticmethod
    def get_latest_upload(

        plc_name

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
        SELECT *

        FROM recipe_upload_history

        WHERE plc_name = ?

        ORDER BY id DESC

        LIMIT 1
        """, (

            plc_name,

        ))

        row = cursor.fetchone()

        conn.close()

        return row