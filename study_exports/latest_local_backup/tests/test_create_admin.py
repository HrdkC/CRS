from database.user_manager import (
    UserManager
)

UserManager.create_user(

    username="admin",

    password="admin123",

    role="ADMIN"

)