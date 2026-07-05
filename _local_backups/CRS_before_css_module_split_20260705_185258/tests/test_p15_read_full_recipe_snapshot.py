from pycomm3 import (
    LogixDriver
)

PLC_IP = "172.20.56.169"

with LogixDriver(
    PLC_IP
) as plc:

    result = plc.read(
        "CRS_Recipe_Data{20}"
    )

    for index, value in enumerate(
        result.value
    ):

        print(
            index,
            "=",
            value
        )