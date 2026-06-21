from database.plc_tag_manager import (
    PLCTagManager
)

tag = PLCTagManager.get_tag_by_id(1)

print(tag)