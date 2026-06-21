from helper.plc_manager import PLC_Manager

manager = PLC_Manager()

"""Add multiple PLCs"""
# manager.add_plc("P01KM", "172.20.56.131")
# manager.add_plc("P01PU", "172.20.42.121")
# manager.add_plc("P02KM", "172.20.56.141")
# manager.add_plc("P02PU", "172.20.42.131")
# manager.add_plc("P15KM", "172.20.56.169")

plcs = [
    ("P01KM", "172.20.56.131"),
    ("P01PU", "172.20.42.121"),
    ("P02KM", "172.20.56.141"),
    ("P02PU", "172.20.42.131"),
    ("P15KM", "172.20.56.169")
]

manager.add_multiple_plcs(plcs)

manager.connect_all()

'''
recipe_tags = [
    "Running_Recipe_Code",
    "FS_BEAD_BLOW_CT",
    "FS_IL_APPLY_CT",
    "FS_PLY1_APPLY_CT"
]

recipe = manager.read_tags(
    plc_name="P15KM",
    tag_list=recipe_tags
)

for tag, value in recipe.items():

    if isinstance(value, float):
        recipe[tag] = round(value, 3)

print(recipe)
'''
# print(manager.get_plc_list())

print(manager.get_connected_plcs())

manager.disconnect_all()