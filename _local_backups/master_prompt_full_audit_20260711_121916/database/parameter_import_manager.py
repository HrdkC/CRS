import pandas as pd


class ParameterImportManager:

    @staticmethod
    def read_process_sheet(

        excel_file

    ):

        df = pd.read_excel(

            excel_file,

            sheet_name="Process Data",

            header=None

        )

        parameters = []

        for row_number in range(

            5,

            len(df)

        ):

            row = df.iloc[row_number]

            excel_name = row[0]

            unit = row[1]

            max_value = row[5]

            min_value = row[6]

            default_value = row[7]

            tag_index = row[8]

            memo = row[9]

            if pd.isna(
                tag_index
            ):
                continue

            if pd.isna(
                excel_name
            ):
                continue

            if pd.isna(
                memo
            ):

                parameter_name = str(
                    excel_name
                ).strip()

            else:

                parameter_name = str(
                    memo
                ).strip()

            parameters.append(

                {

                    "tag_index":
                    int(tag_index),

                    "plc_array_index":
                    int(tag_index),

                    "parameter_name":
                    parameter_name,

                    "unit":
                    "" if pd.isna(unit)
                    else str(unit),

                    "min_value":
                    None if pd.isna(min_value)
                    else float(min_value),

                    "max_value":
                    None if pd.isna(max_value)
                    else float(max_value),

                    "default_value":
                    None if pd.isna(default_value)
                    else float(default_value)

                }

            )

        return parameters

    @staticmethod
    def validate_parameters(

        parameters

    ):

        errors = []

        tag_indexes = set()

        parameter_names = set()

        for parameter in parameters:

            tag_index = parameter[
                "tag_index"
            ]

            parameter_name = parameter[
                "parameter_name"
            ]

            if tag_index in tag_indexes:

                errors.append(

                    f"Duplicate Tag Index : {tag_index}"

                )

            tag_indexes.add(
                tag_index
            )

            if parameter_name.upper() in parameter_names:

                errors.append(

                    f"Duplicate Parameter Name : {parameter_name}"

                )

            parameter_names.add(

                parameter_name.upper()

            )

            min_value = parameter[
                "min_value"
            ]

            max_value = parameter[
                "max_value"
            ]

            default_value = parameter[
                "default_value"
            ]

            if (

                min_value is not None

                and

                max_value is not None

                and

                default_value is not None

            ):

                if not (

                    min_value

                    <=

                    default_value

                    <=

                    max_value

                ):

                    errors.append(

                        f"Invalid Range : {parameter_name}"

                    )

        return errors