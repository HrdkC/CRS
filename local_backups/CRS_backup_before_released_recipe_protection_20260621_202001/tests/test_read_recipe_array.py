from plc.plc_connection import PLCConnection

plc = PLCConnection(
    "172.20.56.169"
)

if plc.connect():

    recipe_array = plc.read_tag(
        "CRS_Recipe_Data{10}"
    )

    print(
        recipe_array
    )

    plc.disconnect()