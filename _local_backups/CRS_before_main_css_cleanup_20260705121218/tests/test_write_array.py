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

    test_array = [

        111.0,

        222.0,

        333.0,

        444.0,

        555.0

    ]

    plc.write_tag(

        "CRS_Recipe_Data",

        test_array

    )

    plc.disconnect()