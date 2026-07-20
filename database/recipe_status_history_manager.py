from database.database import get_connection


class RecipeStatusHistoryManager:
    @staticmethod
    def add_history(
        recipe_id,
        recipe_code,
        old_status,
        new_status,
        changed_by,
        remarks="",
        correlation_id=None,
        _connection=None,
    ):
        owns_connection = _connection is None
        conn = _connection or get_connection()
        cursor = conn.cursor()
        columns = {
            row[1] for row in cursor.execute("PRAGMA table_info(recipe_status_history)")
        }
        if "correlation_id" in columns:
            cursor.execute(
                """
                INSERT INTO recipe_status_history
                (recipe_id, recipe_code, old_status, new_status, changed_by,
                 remarks, correlation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recipe_id, recipe_code, old_status, new_status, changed_by,
                    remarks, correlation_id,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO recipe_status_history
                (recipe_id, recipe_code, old_status, new_status, changed_by, remarks)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    recipe_id, recipe_code, old_status, new_status, changed_by,
                    remarks,
                ),
            )
        history_id = int(cursor.lastrowid)
        if owns_connection:
            conn.commit()
            conn.close()
        return history_id

    @staticmethod
    def get_history(recipe_id):
        conn = get_connection()
        try:
            rows = conn.execute(
                """
                SELECT * FROM recipe_status_history
                WHERE recipe_id = ?
                ORDER BY changed_at DESC, id DESC
                """,
                (recipe_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
