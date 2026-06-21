from database.plc_tag_manager import (
    PLCTagManager
)

PLCTagManager.create_tag(

    machine_id=5,

    stage_id=11,

    tag_name="CRS_Recipe_Data",

    tag_type="REAL",

    is_array=1,

    array_size=501,

    array_start_index=0,

    array_end_index=500

)

tags = (

    PLCTagManager
    .search_tags(

        machine_id=5,

        stage_id=11,

        search_text="recipe"

    )

)

for tag in tags:

    print(tag)