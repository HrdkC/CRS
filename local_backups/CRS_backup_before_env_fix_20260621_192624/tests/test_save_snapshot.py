from plc.plc_recipe_upload import (
    PLCRecipeUpload
)

from recipe.snapshots.snapshot_manager import (
    SnapshotManager
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

snapshot_code = (

    SnapshotManager
    .save_snapshot(

        plc_name="P15KM",

        parameters=parameters

    )

)

print(

    snapshot_code

)