from database.user_manager import UserManager

result1 = UserManager.verify_user(
    username="admin",
    password="admin123"
)

print(result1)

result2 = UserManager.verify_user(
    username="system",
    password="system123",
)

print(result2)
