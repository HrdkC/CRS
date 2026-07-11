from pycomm3 import (
    LogixDriver
)

PLC_IP = "172.20.56.169"

with LogixDriver(
    PLC_IP
) as plc:

    tags = [

        "CRS_Download_Request",

        "CRS_Download_Complete",

        "CRS_Download_Error"

    ]

    for tag in tags:

        result = plc.read(
            tag
        )

        print(
            tag,
            "=",
            result.value
        )