# test_list_plcs.py

from database.plc_manager_legacy import PLCManager

plcs = PLCManager.list_plcs()

for plc in plcs:

    print(dict(plc))