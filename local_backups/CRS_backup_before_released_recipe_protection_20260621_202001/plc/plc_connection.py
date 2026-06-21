# plc/plc_connection.py

from pycomm3 import LogixDriver


class PLCConnection:

    def __init__(self, ip_address):

        self.ip_address = ip_address

        self.plc = None

    def connect(self):

        try:

            self.plc = LogixDriver(self.ip_address)

            self.plc.open()

            print(
                f"Connected To PLC : {self.ip_address}"
            )

            return True

        except Exception as e:

            print(
                f"PLC Connection Failed : {e}"
            )

            return False

    def disconnect(self):

        try:

            if self.plc:

                self.plc.close()

                print(
                    f"Disconnected : {self.ip_address}"
                )

        except Exception as e:

            print(
                f"Disconnect Error : {e}"
            )

    def read_tag(
        self,
        tag_name
    ):

        try:

            result = self.plc.read(tag_name)

            return result.value

        except Exception as e:

            print(
                f"Read Error : {e}"
            )

            return None

    def write_tag(
        self,
        tag_name,
        value
    ):

        try:

            result = self.plc.write(
                (tag_name, value)
            )

            print(
                f"Write Result : {result}"
            )

            if result:

                print(
                    f"Tag Written : {tag_name}"
                )

                return True

            return False

        except Exception as e:

            print(
                f"Write Error : {e}"
            )

            return False