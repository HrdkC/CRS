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
    
from database.user_manager import UserManager

UserManager.create_user(
    username="admin",
    password="admin123",
    role="ADMIN",
    created_by="SYSTEM"
)

UserManager.create_user(
    username="system",
    password="system123",
    role="ADMIN",
    created_by="SYSTEM"
)
