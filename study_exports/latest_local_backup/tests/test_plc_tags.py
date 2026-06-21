import sys
import os

ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if ROOT_DIR not in sys.path:

    sys.path.insert(
        0,
        ROOT_DIR
    )

from database.plc_tag_manager import (
    PLCTagManager
)

machine_id = 1
stage_id = 1

tags = (
    PLCTagManager
    .search_tags(

        machine_id,

        stage_id
    )
)

for tag in tags:

    print(tag)