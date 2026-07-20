from safety import require_supervised_live_plc
require_supervised_live_plc(__file__)

from pycomm3 import (
    LogixDriver
)

PLC_IP = "172.20.56.169"

with LogixDriver(
    PLC_IP
) as plc:

    for index in range(10):

        tag = (
            f"CRS_Recipe_Data[{index}]"
        )

        result = plc.read(
            tag
        )

        print(
            tag,
            "=",
            result.value
        )