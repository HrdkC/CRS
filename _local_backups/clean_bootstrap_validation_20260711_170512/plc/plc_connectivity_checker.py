import socket
import time


class PLCConnectivityChecker:

    DEFAULT_ETHERNET_IP_PORT = 44818

    @staticmethod
    def check_tcp_port(

        ip_address,

        port=DEFAULT_ETHERNET_IP_PORT,

        timeout_seconds=2.0

    ):

        started_at = time.perf_counter()

        try:

            with socket.create_connection(
                (
                    ip_address,
                    int(port)
                ),
                timeout=float(timeout_seconds)
            ):

                elapsed_ms = int(
                    (
                        time.perf_counter()
                        -
                        started_at
                    )
                    *
                    1000
                )

                return {
                    "reachable": True,
                    "ip_address": ip_address,
                    "port": int(port),
                    "elapsed_ms": elapsed_ms,
                    "message": "TCP Connection Successful"
                }

        except socket.timeout:

            message = "Connection Timed Out"

        except OSError as error:

            message = str(error)

        elapsed_ms = int(
            (
                time.perf_counter()
                -
                started_at
            )
            *
            1000
        )

        return {
            "reachable": False,
            "ip_address": ip_address,
            "port": int(port),
            "elapsed_ms": elapsed_ms,
            "message": message
        }
