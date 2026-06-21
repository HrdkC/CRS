from database.plc_registry_manager import (
    PLCRegistryManager
)

PLCRegistryManager.create_plc(

    machine_stage_id=1,

    plc_name="P01_FS_PLC",

    ip_address="192.168.1.101",

    controller_type="ControlLogix",

    firmware_revision="35.011",

    program_revision="V1.00",

    processor_name="1756-L83E",

    plc_software="Studio5000 V35",

    description="P01 First Stage PLC",

    created_by="admin"

)

print(
    "PLC Created"
)