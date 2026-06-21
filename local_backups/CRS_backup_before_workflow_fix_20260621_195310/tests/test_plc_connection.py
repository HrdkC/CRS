import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            ".."
        )
    )
)

from plc.plc_connection import PLCConnection


plc = PLCConnection(
    "172.20.56.169"
)

if plc.connect():

    print("PLC Connection Successful")

    plc.disconnect()

else:

    print("PLC Connection Failed")