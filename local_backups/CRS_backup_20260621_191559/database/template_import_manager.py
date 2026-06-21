import pandas as pd

from database.parameter_definition_manager import (
    ParameterDefinitionManager
)


class TemplateImportManager:

    @staticmethod
    def build_preview(

        excel_file,

        machine_id,

        stage_id

    ):

        df = pd.read_excel(

            excel_file,

            sheet_name="Process Data",

            header=None

        )

        preview_rows = []

        existing_parameters = (

            ParameterDefinitionManager
            .get_all_parameters_by_machine_stage(

                machine_id,

                stage_id

            )

        )

        existing_by_tag = {}

        for parameter in existing_parameters:

            existing_by_tag[
                parameter["tag_index"]
            ] = parameter

        for row_index in range(

            5,

            len(df)

        ):

            row = df.iloc[
                row_index
            ].tolist()

            try:

                tag_index = int(
                    row[8]
                )

            except:

                continue

            parameter_name = ""

            if pd.notna(
                row[9]
            ):

                parameter_name = str(
                    row[9]
                ).strip().upper()

            else:

                parameter_name = str(
                    row[0]
                ).strip().upper()

            unit = ""

            if pd.notna(
                row[1]
            ):

                unit = str(
                    row[1]
                ).strip()

            min_value = row[6]

            max_value = row[5]

            default_value = row[7]

            status = "NEW"

            existing = existing_by_tag.get(
                tag_index
            )

            if existing:

                if (
                    existing[
                        "parameter_name"
                    ].upper()
                    ==
                    parameter_name
                ):

                    status = "EXISTS"

                else:

                    status = "CONFLICT"

            preview_rows.append(

                {

                    "tag_index": tag_index,

                    "parameter_name": parameter_name,

                    "unit": unit,

                    "min_value": min_value,

                    "max_value": max_value,

                    "default_value": default_value,

                    "status": status

                }

            )

        return preview_rows