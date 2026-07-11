from plc.plc_recipe_upload import (
    PLCRecipeUpload
)

recipe_array = (
    PLCRecipeUpload
    .read_recipe_array(

        plc_name="P15KM",

        array_size=10

    )
)

parameters = (
    PLCRecipeUpload
    .convert_array_to_parameters(

        plc_name="P15KM",

        recipe_array=recipe_array

    )
)

for parameter in parameters:

    print(
        parameter
    )