from database.parameter_import_manager import (
    ParameterImportManager
)

parameters = (

    ParameterImportManager
    .read_process_sheet(

        r"D:\gt9088.xls"

    )

)

print()

print(
    "PARAMETERS FOUND =",
    len(parameters)
)

print()

errors = (

    ParameterImportManager
    .validate_parameters(

        parameters

    )

)

print(
    "ERROR COUNT =",
    len(errors)
)

print()

for error in errors[:20]:

    print(error)

print()

for row in parameters[:10]:

    print(row)