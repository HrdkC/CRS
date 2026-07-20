from database.database import get_connection
from database.schema_guard import require_table


class UploadHistoryManager:

    OPTIONAL_COLUMNS = {

        "user_role": "TEXT",

        "plc_id": "INTEGER",

        "source_tag": "TEXT",

        "destination_tag": "TEXT",

        "candidate_change_count": "INTEGER DEFAULT 0",

        "validated_parameters": "INTEGER DEFAULT 0",

        "payload_mismatch_count": "INTEGER DEFAULT 0"

    }

    @staticmethod
    def ensure_schema(cursor=None):
        required = {
            "plc_name", "recipe_code", "recipe_version", "uploaded_by",
            "status", "remarks", "user_role", "plc_id", "source_tag",
            "destination_tag", "candidate_change_count",
            "validated_parameters", "payload_mismatch_count",
        }
        if cursor is None:
            return require_table("recipe_upload_history", required)
        exists = cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='recipe_upload_history'"
        ).fetchone()
        columns = {
            row[1] for row in cursor.execute("PRAGMA table_info(recipe_upload_history)")
        } if exists else set()
        missing = sorted(required - columns)
        if missing:
            raise RuntimeError(
                "recipe_upload_history schema is not ready: " + ", ".join(missing)
            )
        return True

    @staticmethod
    def ensure_table(cursor=None):

        return UploadHistoryManager.ensure_schema(cursor)

    @staticmethod
    def log_upload(

        plc_name,

        recipe_code,

        recipe_version,

        status,

        uploaded_by="PLC_UPLOAD",

        remarks=None,

        user_role=None,

        plc_id=None,

        source_tag=None,

        destination_tag=None,

        candidate_change_count=0,

        validated_parameters=0,

        payload_mismatch_count=0

    ):

        conn = get_connection()

        cursor = conn.cursor()

        UploadHistoryManager.ensure_schema(
            cursor
        )

        cursor.execute("""
        INSERT INTO recipe_upload_history (

            plc_name,

            recipe_code,

            recipe_version,

            uploaded_by,

            status,

            remarks,

            user_role,

            plc_id,

            source_tag,

            destination_tag,

            candidate_change_count,

            validated_parameters,

            payload_mismatch_count

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            plc_name,

            recipe_code,

            recipe_version,

            uploaded_by,

            status,

            remarks,

            user_role,

            plc_id,

            source_tag,

            destination_tag,

            candidate_change_count,

            validated_parameters,

            payload_mismatch_count

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

        UploadHistoryManager.ensure_schema(
            cursor
        )

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

        UploadHistoryManager.ensure_schema(
            cursor
        )

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

        UploadHistoryManager.ensure_schema(
            cursor
        )

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
