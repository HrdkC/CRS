from database.user_manager import (
    UserManager
)

users = UserManager.list_users()

print(
    f"User Count = {len(users)}"
)

for user in users:

    print(user)