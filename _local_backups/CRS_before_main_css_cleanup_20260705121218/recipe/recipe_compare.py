from database.recipe_manager import (
    RecipeManager
)


class RecipeCompare:

    @staticmethod
    def compare(

        recipe_1,

        recipe_2,

        version_1=1,

        version_2=1

    ):

        recipe_a = (

            RecipeManager
            .get_recipe_dictionary(

                recipe_1,

                version_1

            )

        )

        recipe_b = (

            RecipeManager
            .get_recipe_dictionary(

                recipe_2,

                version_2

            )

        )

        differences = []

        all_parameters = set(

            recipe_a.keys()

        ).union(

            recipe_b.keys()

        )

        for parameter_name in sorted(

            all_parameters

        ):

            value_a = recipe_a.get(
                parameter_name
            )

            value_b = recipe_b.get(
                parameter_name
            )

            if value_a != value_b:

                differences.append({

                    "parameter_name":
                    parameter_name,

                    "recipe_1_value":
                    value_a,

                    "recipe_2_value":
                    value_b

                })

        return differences