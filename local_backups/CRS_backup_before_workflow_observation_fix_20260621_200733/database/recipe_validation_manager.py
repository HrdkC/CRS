from database.recipe_manager import (
    RecipeManager
)

from database.recipe_parameter_value_manager import (
    RecipeParameterValueManager
)


class RecipeValidationManager:

    @staticmethod
    def validate_recipe(

        recipe_id

    ):

        result = {

            "valid": True,

            "errors": []

        }

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                recipe_id
            )
        )

        if not recipe:

            result["valid"] = False

            result["errors"].append(
                "Recipe Not Found"
            )

            return result

        if recipe["status"] != "RELEASED":

            result["valid"] = False

            result["errors"].append(
                f"Recipe Status Is "
                f"{recipe['status']}. "
                f"Only RELEASED "
                f"Recipes Can Be Downloaded."
            )

        values = (
            RecipeParameterValueManager
            .get_recipe_values(
                recipe_id
            )
        )

        if len(values) == 0:

            result["valid"] = False

            result["errors"].append(
                "No Recipe Parameters Found"
            )

            return result

        for row in values:

            parameter_name = (
                row["parameter_name"]
            )

            value = (
                row["parameter_value"]
            )

            min_value = (
                row["min_value"]
            )

            max_value = (
                row["max_value"]
            )

            tag_index = (
                row["tag_index"]
            )

            if value is None:

                result["valid"] = False

                result["errors"].append(

                    f"Tag {tag_index} : "
                    f"{parameter_name} "
                    f"Value Is Empty"

                )

                continue

            try:

                numeric_value = (
                    float(value)
                )

            except Exception:

                result["valid"] = False

                result["errors"].append(

                    f"Tag {tag_index} : "
                    f"{parameter_name} "
                    f"Invalid Numeric Value"

                )

                continue

            if (

                min_value is not None

                and

                numeric_value < min_value

            ):

                result["valid"] = False

                result["errors"].append(

                    f"Tag {tag_index} : "
                    f"{parameter_name} "
                    f"Below Minimum "
                    f"({numeric_value} < {min_value})"

                )

            if (

                max_value is not None

                and

                numeric_value > max_value

            ):

                result["valid"] = False

                result["errors"].append(

                    f"Tag {tag_index} : "
                    f"{parameter_name} "
                    f"Above Maximum "
                    f"({numeric_value} > {max_value})"

                )

        return result