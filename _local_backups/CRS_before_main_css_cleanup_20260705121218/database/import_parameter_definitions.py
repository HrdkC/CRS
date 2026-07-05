import pandas as pd

from database.parameter_definition_manager import (
    ParameterDefinitionManager
)

FILE_PATH = r"D:\P15KM_Parameter_Template.xlsx"

MACHINE_ID = 5
STAGE_ID = 11


def run():

    df = pd.read_excel(

        FILE_PATH,

        sheet_name="ParameterDefinitions"
    )

    imported = 0
    skipped = 0

    for _, row in df.iterrows():

        try:

            ParameterDefinitionManager.create_parameter(

                machine_id=MACHINE_ID,

                stage_id=STAGE_ID,

                tag_index=int(
                    row["tag_index"]
                ),

                plc_array_index=int(
                    row["plc_array_index"]
                ),

                parameter_name=str(
                    row["parameter_name"]
                ),

                unit=str(
                    row["unit"]
                ),

                min_value=float(
                    row["min_value"]
                ),

                max_value=float(
                    row["max_value"]
                ),

                default_value=float(
                    row["default_value"]
                ),

                datatype=str(
                    row["datatype"]
                ),

                english_memo="",

                used=int(
                    row["used"]
                ),

                created_by="excel_import"

            )

            imported += 1

        except Exception as ex:

            skipped += 1

            print(
                f"SKIPPED: {ex}"
            )

    print()
    print(
        f"Imported = {imported}"
    )
    print(
        f"Skipped = {skipped}"
    )
    print()


if __name__ == "__main__":

    run()