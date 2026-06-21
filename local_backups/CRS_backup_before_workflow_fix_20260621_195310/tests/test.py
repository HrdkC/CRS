from helper.plc_helper import PLC_Connection
from recipe.recipe_reader import RecipeReader

plc = PLC_Connection("172.20.56.169")

if plc.connect():
    
    # print(plc.driver.info)

    print("Connection Successful")
    print(plc.get_plc_info())
    '''
    tags = [
        "Running_Recipe_Code",
        "FS_BEAD_BLOW_CT",
        "FS_IL_APPLY_CT",
        "FS_PLY1_APPLY_CT",
    ]
    
    values = plc.read_tags(tags)
    
    print(values)
    '''
    
    recipe_tags = [
    "Running_Recipe_Code",
    "FS_BEAD_BLOW_CT",
    "FS_IL_APPLY_CT",
    "FS_PLY1_APPLY_CT"
]

    recipe_reader = RecipeReader(plc)

    recipe = recipe_reader.read_recipe(recipe_tags)

    print(recipe)

    plc.disconnect()

else:
    print("Connection Failed")