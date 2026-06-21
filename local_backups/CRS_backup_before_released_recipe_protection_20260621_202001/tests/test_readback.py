import sys
import os

ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from plc.plc_connection import PLCConnection

plc = PLCConnection(
    "172.20.56.169"
)

if plc.connect():

    value = plc.read_tag(
        "CRS_Recipe_Data"
    )

    print(
        "PLC Value =",
        value
    )

    plc.disconnect()