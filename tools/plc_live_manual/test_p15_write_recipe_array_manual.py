from safety import require_supervised_live_plc
require_supervised_live_plc(__file__)

from pycomm3 import (
    LogixDriver
)

PLC_IP = "172.20.56.169"

with LogixDriver(
    PLC_IP
) as plc:

    print(
        plc.write(
            (
                "CRS_Recipe_Data[2]",
                123.45
            )
        )
    )

    result = plc.read(
        "CRS_Recipe_Data[2]"
    )

    print(
        "Read Back =",
        result.value
    )