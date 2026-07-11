# database/recipe_import_export.py

import os
import pandas as pd

from database.database import get_connection


class RecipeImportExport:

    @staticmethod
    def export_recipe_to_excel(
        recipe_code,
        version,
        file_name
    ):

        conn = get_connection()

        query = """
        SELECT

            display_order,
            plc_array_index,

            parameter_group,
            category,

            parameter_name,
            recipe_parameter_description,

            plc_tag_name,

            parameter_value,

            data_type,

            unit,

            min_value,
            max_value

        FROM recipe_parameters

        WHERE recipe_code = ?
        AND version = ?

        ORDER BY display_order
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=(recipe_code, version)
        )

        conn.close()

        if df.empty:

            print(
                f"Warning : No parameters found for {recipe_code}"
            )

            return False

        # Create export folder automatically

        os.makedirs(
            "recipe_exports",
            exist_ok=True
        )

        full_path = os.path.join(
            "recipe_exports",
            file_name
        )

        df.to_excel(
            full_path,
            index=False
        )

        print(
            f"Recipe Exported : {full_path}"
        )

        return True
    
    @staticmethod
    def import_recipe_from_excel(

        recipe_code,
        version,
        file_path

    ):

        import pandas as pd

        from database.recipe_manager import RecipeManager

        try:

            df = pd.read_excel(file_path)

        except Exception as e:

            print(
                f"Error Reading Excel : {e}"
            )

            return False

        required_columns = [

            "display_order",
            "plc_array_index",

            "parameter_group",
            "category",

            "parameter_name",
            "recipe_parameter_description",

            "plc_tag_name",

            "parameter_value",

            "data_type",

            "unit",

            "min_value",
            "max_value"

        ]

        for column in required_columns:

            if column not in df.columns:

                print(
                    f"Missing Column : {column}"
                )

                return False

        imported_count = 0

        for _, row in df.iterrows():

            try:

                result = RecipeManager.add_parameter(

                    recipe_code=recipe_code,
                    version=version,

                    display_order=int(
                        row["display_order"]
                    ),

                    plc_array_index=int(
                        row["plc_array_index"]
                    ),

                    parameter_group=row["parameter_group"],
                    category=row["category"],

                    parameter_name=row["parameter_name"],

                    recipe_parameter_description=row[
                        "recipe_parameter_description"
                    ],

                    plc_tag_name=row["plc_tag_name"],

                    parameter_value=float(
                        row["parameter_value"]
                    ),

                    data_type=row["data_type"],

                    unit=row["unit"],

                    min_value=float(
                        row["min_value"]
                    ),

                    max_value=float(
                        row["max_value"]
                    )

                )

                if result is not False:

                    imported_count += 1

            except Exception as e:

                print(
                    f"Warning : {e}"
                )

                continue

        print(
            f"Imported {imported_count} Parameters"
        )

        return True