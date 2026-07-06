from database.recipe_manager import (
    RecipeManager
)

from database.recipe_parameter_value_manager import (
    RecipeParameterValueManager
)


class RecipeValidationManager:

    @staticmethod
    def validate_recipe(

        recipe_id,

        require_released=True

    ):

        result = {

            "valid": True,

            "errors": [],

            "summary": {

                "total_parameters": 0,

                "valid_parameters": 0,

                "invalid_parameters": 0

            }

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

        if (

            require_released

            and

            recipe["status"] != "RELEASED"

        ):

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

        result["summary"]["total_parameters"] = len(
            values
        )

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

                result["summary"]["invalid_parameters"] += 1

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

                result["summary"]["invalid_parameters"] += 1

                result["errors"].append(

                    f"Tag {tag_index} : "
                    f"{parameter_name} "
                    f"Invalid Numeric Value"

                )

                continue

            try:

                min_numeric = (
                    float(min_value)
                    if min_value is not None
                    else
                    None
                )

                max_numeric = (
                    float(max_value)
                    if max_value is not None
                    else
                    None
                )

            except Exception:

                result["valid"] = False

                result["summary"]["invalid_parameters"] += 1

                result["errors"].append(

                    f"Tag {tag_index} : "
                    f"{parameter_name} "
                    f"Invalid Min/Max Configuration"

                )

                continue

            if (

                min_numeric is not None

                and

                max_numeric is not None

                and

                min_numeric > max_numeric

            ):

                result["valid"] = False

                result["summary"]["invalid_parameters"] += 1

                result["errors"].append(

                    f"Tag {tag_index} : "
                    f"{parameter_name} "
                    f"Invalid Min/Max Configuration "
                    f"({min_numeric} > {max_numeric})"

                )

                continue

            parameter_valid = True

            if (

                min_numeric is not None

                and

                numeric_value < min_numeric

            ):

                result["valid"] = False

                parameter_valid = False

                result["errors"].append(

                    f"Tag {tag_index} : "
                    f"{parameter_name} "
                    f"Below Minimum "
                    f"({numeric_value} < {min_numeric})"

                )

            if (

                max_numeric is not None

                and

                numeric_value > max_numeric

            ):

                result["valid"] = False

                parameter_valid = False

                result["errors"].append(

                    f"Tag {tag_index} : "
                    f"{parameter_name} "
                    f"Above Maximum "
                    f"({numeric_value} > {max_numeric})"

                )

            if parameter_valid:

                result["summary"]["valid_parameters"] += 1

            else:

                result["summary"]["invalid_parameters"] += 1

        return result
