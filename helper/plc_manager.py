# helper/plc_manager.py

from helper.plc_helper import PLC_Connection


class PLC_Manager:

    def __init__(self):
        self.plcs = {}

    def add_plc(self, plc_name, ip_address):

        if plc_name in self.plcs:
            print(f"PLC '{plc_name}' already exists")
            return False

        self.plcs[plc_name] = PLC_Connection(ip_address)

        return True
    
    def add_multiple_plcs(self, plc_list):

        for plc_name, ip_address in plc_list:
            self.add_plc(plc_name, ip_address)
    
    def has_plc(self, plc_name):

        return plc_name in self.plcs

    def remove_plc(self, plc_name):

        plc = self.plcs.get(plc_name)

        if plc:

            plc.disconnect()

            del self.plcs[plc_name]

            return True

        return False

    def get_plc(self, plc_name):

        return self.plcs.get(plc_name)
    
    def connect_plc(self, plc_name):

        plc = self.get_plc(plc_name)

        if plc is None:
            print(f"PLC '{plc_name}' not found")
            return False

        return plc.connect()
    
    def get_connected_plcs(self):

        return [
            plc_name
            for plc_name, plc in self.plcs.items()
            if plc.is_connected()
        ]
    
    def disconnect_plc(self, plc_name):

        plc = self.get_plc(plc_name)

        if plc is None:
            print(f"PLC '{plc_name}' not found")
            return False

        plc.disconnect()

        return True

    def connect_all(self):

        results = {}

        for plc_name, plc in self.plcs.items():

            results[plc_name] = plc.connect()

        return results

    def disconnect_all(self):

        for plc in self.plcs.values():
            plc.disconnect()
            
    def get_plc_list(self):

        plc_list = []

        for plc_name, plc in self.plcs.items():

            plc_list.append({
                "plc_name": plc_name,
                "ip_address": plc.ip_address,
                "connected": plc.is_connected()
            })

        return plc_list

    def get_all_plcs(self):

        return list(self.plcs.keys())

    def get_status(self):

        status = {}

        for plc_name, plc in self.plcs.items():

            status[plc_name] = plc.is_connected()

        return status

    # ---------------------------
    # Read Functions
    # ---------------------------

    def read_tag(self, plc_name, tag_name):

        plc = self.get_plc(plc_name)

        if plc is None:
            print(f"PLC '{plc_name}' not found")
            return None

        return plc.read_tag(tag_name)

    def read_tags(self, plc_name, tag_list):

        plc = self.get_plc(plc_name)

        if plc is None:
            print(f"PLC '{plc_name}' not found")
            return {}

        return plc.read_tags(tag_list)

    def get_plc_info(self, plc_name):

        plc = self.get_plc(plc_name)

        if plc is None:
            print(f"PLC '{plc_name}' not found")
            return {}

        return plc.get_plc_info()