from database.audit_manager import (
    AuditManager
)

from database.database import (
    get_connection
)

from database.upgrade_recipes_test_only import (
    upgrade_recipes_test_only
)


class RecipeCleanupManager:

    @staticmethod
    def mark_incomplete_test_recipes(
        username="SYSTEM",
        role="ADMIN"
    ):

        upgrade_recipes_test_only()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                r.id,
                r.recipe_code
            FROM recipes r
            WHERE COALESCE(r.is_test_only, 0) = 0
            AND UPPER(r.recipe_code) LIKE '%TEST%'
            AND (
                NOT EXISTS (
                    SELECT 1
                    FROM recipe_parameter_values v
                    WHERE v.recipe_id = r.id
                )
                OR NOT EXISTS (
                    SELECT 1
                    FROM recipe_phase_control pc
                    WHERE pc.recipe_id = r.id
                )
            )
            """
        )

        rows = [
            dict(row)
            for row in cursor.fetchall()
        ]

        if not rows:

            conn.close()

            return {
                "marked": 0,
                "recipes": []
            }

        recipe_ids = [
            row["id"]
            for row in rows
        ]

        placeholders = ",".join(
            "?"
            for _ in recipe_ids
        )

        cursor.execute(
            f"""
            UPDATE recipes
            SET is_test_only = 1
            WHERE id IN ({placeholders})
            """,
            recipe_ids
        )

        conn.commit()
        conn.close()

        for row in rows:

            AuditManager.log_event(
                username=username,
                role=role,
                action="RECIPE_MARKED_TEST_ONLY",
                change_source="SYSTEM_CLEANUP",
                record_id=row["id"],
                recipe_code=row["recipe_code"],
                old_value="is_test_only=0",
                new_value="is_test_only=1",
                reason=(
                    "Incomplete test recipe cleanup: missing parameters "
                    "or phase-control rows."
                )
            )

        return {
            "marked": len(rows),
            "recipes": rows
        }
