from database.plc_parameter_mapping_manager import (
    PLCParameterMappingManager
)

mapping = (
    PLCParameterMappingManager
    .get_mapping_by_index(

        plc_name="P15KM",

        plc_array_index=0

    )
)

if mapping:

    print(
        dict(mapping)
    )

else:

    print(
        "Mapping Not Found"
    )