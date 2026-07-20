from safety import require_supervised_live_plc
require_supervised_live_plc(__file__)

from pycomm3 import (
    LogixDriver
)

PLC_IP = "172.20.56.169"

print(
    "Attempting Connection..."
)

try:

    with LogixDriver(
        PLC_IP
    ) as plc:

        print(
            "CONNECTED"
        )

        print(
            plc.info
        )

except Exception as e:

    print(
        f"ERROR: {e}"
    )