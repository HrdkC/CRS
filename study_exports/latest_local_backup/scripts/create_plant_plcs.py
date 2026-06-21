# create_plant_plcs.py
import sys
import os

ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if ROOT_DIR not in sys.path:

    sys.path.insert(
        0,
        ROOT_DIR
    )
    
from database.plc_manager_legacy import PLCManager

PLCManager.add_plc(
    plc_name="P01KM",
    ip_address="172.20.56.131"
)

PLCManager.add_plc(
    plc_name="P01PU",
    ip_address="172.20.42.121"
)

PLCManager.add_plc(
    plc_name="P02KM",
    ip_address="172.20.56.141"
)

PLCManager.add_plc(
    plc_name="P02PU",
    ip_address="172.20.42.131"
)

PLCManager.add_plc(
    plc_name="P03KM",
    ip_address="172.20.42.151"
)

PLCManager.add_plc(
    plc_name="P03PU",
    ip_address="172.20.42.141"
)

PLCManager.add_plc(
    plc_name="P05KM",
    ip_address="172.20.42.181"
)

PLCManager.add_plc(
    plc_name="P06KM",
    ip_address="172.20.42.201"
)

PLCManager.add_plc(
    plc_name="P06PU",
    ip_address="172.20.42.211"
)

PLCManager.add_plc(
    plc_name="P09KM",
    ip_address="172.20.43.11"
)

PLCManager.add_plc(
    plc_name="P09PU",
    ip_address="172.20.43.21"
)

PLCManager.add_plc(
    plc_name="P10KM",
    ip_address="172.20.43.31"
)

PLCManager.add_plc(
    plc_name="P10PU",
    ip_address="172.20.43.41"
)

PLCManager.add_plc(
    plc_name="P11KM",
    ip_address="172.20.43.51"
)

PLCManager.add_plc(
    plc_name="P11PU",
    ip_address="172.20.43.61"
)

PLCManager.add_plc(
    plc_name="P12KM",
    ip_address="172.20.43.71"
)

PLCManager.add_plc(
    plc_name="P12PU",
    ip_address="172.20.43.81"
)

PLCManager.add_plc(
    plc_name="P13KM",
    ip_address="172.20.43.201"
)

PLCManager.add_plc(
    plc_name="P13PU",
    ip_address="172.20.43.221"
)

PLCManager.add_plc(
    plc_name="P14KM",
    ip_address="172.20.43.231"
)

PLCManager.add_plc(
    plc_name="P14PU",
    ip_address="172.20.43.241"
)

PLCManager.add_plc(
    plc_name="P15KM",
    ip_address="172.20.56.169"
)

PLCManager.add_plc(
    plc_name="P15PU",
    ip_address="172.20.42.251"
)


