import os
import sys

sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            ".."
        )
    )
)

from plc.plc_connectivity_checker import (
    PLCConnectivityChecker
)


result = PLCConnectivityChecker.check_tcp_port(

    ip_address="127.0.0.1",

    port=1,

    timeout_seconds=0.2

)

assert result["reachable"] in [
    True,
    False
]

assert result["ip_address"] == "127.0.0.1"

assert result["port"] == 1

assert "elapsed_ms" in result

assert "message" in result

print(
    "PLC Connectivity Checker Test Passed"
)
