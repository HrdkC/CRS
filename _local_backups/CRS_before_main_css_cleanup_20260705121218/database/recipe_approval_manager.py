from database.database import (
    get_connection
)

from database.recipe_status_history_manager import (
    RecipeStatusHistoryManager
)


class RecipeApprovalManager:

    @staticmethod
    def submit_for_review(

        recipe_id,

        username,

        remarks=""

    ):

        return (
            RecipeApprovalManager
            .change_status(

                recipe_id,

                "REVIEW",

                username,

                remarks

            )
        )

    @staticmethod
    def approve_recipe(

        recipe_id,

        username,

        remarks=""

    ):

        return (
            RecipeApprovalManager
            .change_status(

                recipe_id,

                "APPROVED",

                username,

                remarks

            )
        )

    @staticmethod
    def reject_recipe(

        recipe_id,

        username,

        remarks

    ):

        if not remarks:

            return (

                False,

                "Rejection Remarks Required"

            )

        return (
            RecipeApprovalManager
            .change_status(

                recipe_id,

                "DRAFT",

                username,

                remarks

            )
        )

    @staticmethod
    def change_status(

        recipe_id,

        new_status,

        username,

        remarks=""

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipes

            WHERE id = ?
            """,
            (
                recipe_id,
            )
        )

        recipe = cursor.fetchone()

        if not recipe:

            conn.close()

            return (

                False,

                "Recipe Not Found"

            )

        recipe = dict(recipe)

        old_status = (
            recipe["status"]
        )

        recipe_code = (
            recipe["recipe_code"]
        )

        if new_status == "APPROVED":

            cursor.execute(
                """
                SELECT MAX(version) AS current_version

                FROM recipes

                WHERE

                    machine_id = ?

                    AND stage_id = ?

                    AND UPPER(recipe_code) = UPPER(?)

                    AND status = 'RELEASED'
                """,
                (
                    recipe["machine_id"],
                    recipe["stage_id"],
                    recipe_code
                )
            )

            current = cursor.fetchone()

            if (
                current
                and
                current["current_version"] is not None
                and
                current["current_version"] >= recipe["version"]
            ):

                conn.close()

                return (

                    False,

                    f"Cannot approve V{recipe['version']} because "
                    f"V{current['current_version']} is already released."

                )

        allowed = {

            "DRAFT": [
                "REVIEW"
            ],

            "REVIEW": [
                "APPROVED",
                "DRAFT"
            ],

            "APPROVED": [
                "RELEASED"
            ],

            "RELEASED": []
        }

        if (

            new_status
            not in
            allowed.get(
                old_status,
                []
            )

        ):

            conn.close()

            return (

                False,

                f"Invalid Workflow : "
                f"{old_status} -> "
                f"{new_status}"

            )

        cursor.execute(
            """
            UPDATE recipes

            SET

                status = ?,

                updated_at =
                CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                new_status,
                recipe_id
            )
        )

        conn.commit()

        RecipeStatusHistoryManager.add_history(

            recipe_id=
            recipe_id,

            recipe_code=
            recipe_code,

            old_status=
            old_status,

            new_status=
            new_status,

            changed_by=
            username,

            remarks=
            remarks

        )

        if new_status == "APPROVED":

            cursor.execute(
                """
                UPDATE recipes

                SET

                    status = 'RELEASED',

                    updated_at =
                    CURRENT_TIMESTAMP

                WHERE id = ?
                """,
                (
                    recipe_id,
                )
            )

            conn.commit()

            RecipeStatusHistoryManager.add_history(

                recipe_id=
                recipe_id,

                recipe_code=
                recipe_code,

                old_status=
                "APPROVED",

                new_status=
                "RELEASED",

                changed_by=
                "SYSTEM",

                remarks=
                "Auto Release After Approval"

            )

        conn.close()

        return (

            True,

            "Status Updated"

        )
