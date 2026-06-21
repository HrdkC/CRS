from database.parameter_definition_manager import (
    ParameterDefinitionManager
)

try:

    ParameterDefinitionManager.create_parameter(

        machine_id=1,

        stage_id=7,

        tag_index=130,

        plc_array_index=130,

        parameter_name="BEAD_SET",

        parameter_class="BEAD",

        unit="MM",

        min_value=400,

        max_value=800,

        default_value=600,

        datatype="REAL",

        english_memo="RIGHT TURNUP POSITION",

        created_by="admin"

    )

except Exception as e:

    print(e)

rows = (

    ParameterDefinitionManager
    .get_parameters_by_machine_stage(

        machine_id=1,

        stage_id=7

    )

)

for row in rows:

    print(
        row["tag_index"],
        row["parameter_name"]
    )