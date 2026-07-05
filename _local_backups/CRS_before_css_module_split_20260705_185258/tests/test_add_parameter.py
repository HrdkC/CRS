from database.recipe_manager import RecipeManager


RecipeManager.add_parameter(

    recipe_code="GT7107",
    version=1,

    display_order=1,
    plc_array_index=0,

    parameter_group="PROCESS_DATA",
    category="SHAPING_HEAD",

    parameter_name="Carcass Setting",

    recipe_parameter_description="Carcass Setting Position",

    plc_tag_name="Recipe_Array[0]",

    parameter_value=385.0,

    data_type="REAL",

    unit="mm",

    min_value=130.0,
    max_value=540.0
)


RecipeManager.add_parameter(

    recipe_code="GT7107",
    version=1,

    display_order=2,
    plc_array_index=1,

    parameter_group="PROCESS_DATA",
    category="SHAPING_HEAD",

    parameter_name="Stretch Position",

    recipe_parameter_description="Stretch Position",

    plc_tag_name="Recipe_Array[1]",

    parameter_value=410.0,

    data_type="REAL",

    unit="mm",

    min_value=130.0,
    max_value=540.0
)

print("Parameters Added")