'''PLC Communication Functions'''

# plc_helper.py

from pycomm3 import LogixDriver
import time


class PLC_Connection:

    def __init__(self, ip_address, reconnect_attempts=3):
        self.ip_address = ip_address
        self.driver = None
        self.connected = False
        self.reconnect_attempts = reconnect_attempts

    def connect(self):

        try:
            self.driver = LogixDriver(self.ip_address)
            self.driver.open()

            self.connected = self.driver.connected

            if self.connected:
                print(f"Connected : {self.ip_address}")

            return self.connected

        except Exception as e:

            print(f"Connection Error : {e}")

            self.connected = False

            return False

    def get_plc_info(self):

        if not self.connected or self.driver is None:

            return {
                "connected": False
            }

        try:

            return {
                "ip_address": self.ip_address,
                "connected": self.connected,
                "product_name": self.driver.info.get("product_name"),
                "product_type": self.driver.info.get("product_type"),
                "revision": self.driver.info.get("revision"),
                "serial": self.driver.info.get("serial"),
            }

        except Exception as e:

            return {
                "error": str(e)
            }

    def is_connected(self):

        return self.connected

    def disconnect(self):

        try:

            if self.driver:
                self.driver.close()

        except Exception as e:

            print(f"Disconnect Error : {e}")

        finally:

            self.connected = False

    def reconnect(self):

        print(f"Reconnecting PLC {self.ip_address}")

        self.disconnect()

        for attempt in range(1, self.reconnect_attempts + 1):

            print(f"Reconnect Attempt {attempt}")

            if self.connect():
                return True

            time.sleep(2)

        return False

    def ensure_connection(self):

        try:

            if self.driver and self.driver.connected:

                self.connected = True

                return True

        except Exception:

            pass

        self.connected = False

        return self.reconnect()

    def read_tag(self, tag_name):

        try:

            if not self.ensure_connection():
                raise Exception("PLC Not Connected")

            result = self.driver.read(tag_name)

            return result.value

        except Exception as e:

            print(f"Read Error [{tag_name}] : {e}")

            return None

    def read_tags(self, tag_list):

        try:

            if not self.ensure_connection():
                raise Exception("PLC Not Connected")

            results = self.driver.read(*tag_list)

            return {
                result.tag: result.value
                for result in results
            }

        except Exception as e:

            print(f"Read Tags Error : {e}")

            return {}

    # Reserved for future Recipe Download functionality

    def write_tag(self, tag_name, value):

        try:

            if not self.ensure_connection():
                raise Exception("PLC Not Connected")

            return self.driver.write((tag_name, value))

        except Exception as e:

            print(f"Write Error [{tag_name}] : {e}")

            return False

    # Reserved for future Recipe Download functionality

    def write_tags(self, tag_dict):

        try:

            if not self.ensure_connection():
                raise Exception("PLC Not Connected")

            write_data = [
                (tag, value)
                for tag, value in tag_dict.items()
            ]

            return self.driver.write(*write_data)

        except Exception as e:

            print(f"Write Tags Error : {e}")

            return False