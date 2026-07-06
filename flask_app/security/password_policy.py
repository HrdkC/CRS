import os
import re


MIN_PASSWORD_LENGTH = int(os.getenv("CRS_MIN_PASSWORD_LENGTH", "10"))
COMMON_WEAK_PARTS = {
    "admin",
    "apollo",
    "crs",
    "password",
    "operator",
    "production",
    "technology",
    "engineering",
    "welcome",
    "123456",
    "qwerty",
}


def validate_password_strength(password, username=None):
    value = password or ""
    lowered = value.lower()

    if len(value) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."

    if username and username.lower() in lowered:
        return False, "Password must not contain the username."

    if any(part in lowered for part in COMMON_WEAK_PARTS):
        return False, "Password contains a common weak word. Use a stronger password."

    checks = [
        (r"[A-Z]", "one uppercase letter"),
        (r"[a-z]", "one lowercase letter"),
        (r"[0-9]", "one number"),
        (r"[^A-Za-z0-9]", "one symbol"),
    ]

    missing = [label for pattern, label in checks if not re.search(pattern, value)]
    if missing:
        return False, "Password must include " + ", ".join(missing) + "."

    return True, ""
