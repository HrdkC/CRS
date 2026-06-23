from database.recipe_manager import (
    RecipeManager
)

from database.recipe_phase_control_manager import (
    RecipePhaseControlManager
)

from database.recipe_validation_manager import (
    RecipeValidationManager
)


class RecipeDownloadEligibilityManager:

    @staticmethod
    def check_eligibility(

        recipe_id

    ):

        result = {

            "eligible": True,

            "status": "ELIGIBLE",

            "errors": [],

            "warnings": []

        }

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                recipe_id
            )
        )

        if not recipe:

            result["eligible"] = False

            result["status"] = "BLOCKED"

            result["errors"].append(
                "Recipe Not Found"
            )

            return result

        if recipe["status"] != "RELEASED":

            result["eligible"] = False

            result["errors"].append(
                f"Recipe status is "
                f"{recipe['status']}. "
                f"Only RELEASED recipes can be downloaded."
            )

        if recipe.get("is_test_only") == 1:

            result["eligible"] = False

            result["errors"].append(
                "Recipe is marked TEST ONLY and is blocked from PLC download."
            )

        if recipe["version_usage_status"] == "HISTORY_RELEASED":

            result["eligible"] = False

            result["errors"].append(
                f"V{recipe['version']} is historical. "
                f"Download is allowed only from current "
                f"production version V"
                f"{recipe['current_released_version']}."
            )

        if (

            recipe["status"] == "RELEASED"

            and

            recipe["version_usage_status"] != "CURRENT_RELEASED"

        ):

            result["eligible"] = False

            result["errors"].append(
                "Released recipe is not marked as current "
                "production version."
            )

        phase_rows = (
            RecipePhaseControlManager
            .get_recipe_phase_control(
                recipe_id
            )
        )

        if not phase_rows:

            result["eligible"] = False

            result["errors"].append(
                "No phase control rows found."
            )

        elif len(phase_rows) != 12:

            result["eligible"] = False

            result["errors"].append(
                f"Incomplete phase control rows. "
                f"Expected 12, found {len(phase_rows)}."
            )

        for row in phase_rows:

            if not row["phase_control_id"]:

                result["eligible"] = False

                result["errors"].append(
                    f"Phase line {row['line_no']} "
                    f"has no phase control selected."
                )

            if row["sequence_no"] is None:

                result["eligible"] = False

                result["errors"].append(
                    f"Phase line {row['line_no']} "
                    f"has no sequence number."
                )

        validation = (
            RecipeValidationManager
            .validate_recipe(
                recipe_id,

                require_released=False
            )
        )

        if not validation["valid"]:

            result["eligible"] = False

            result["errors"].extend(
                validation["errors"]
            )

        if result["eligible"]:

            result["status"] = "ELIGIBLE"

            result["warnings"].append(
                "Recipe is current, released, and validation passed."
            )

        else:

            result["status"] = "BLOCKED"

        return result
