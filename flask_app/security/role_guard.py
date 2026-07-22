FINAL_ROLES = [
    "ADMIN",
    "ENGINEERING",
    "TECHNOLOGY",
    "PRODUCTION",
    "OPERATOR",
    "VIEWER"
]

# Backward compatibility only. New users should not be created with legacy roles.
LEGACY_ROLES = [
    "EDITOR"
]

VALID_ROLES = FINAL_ROLES + LEGACY_ROLES

ROLE_HIERARCHY = {
    "ADMIN": 100,
    "ENGINEERING": 80,
    "TECHNOLOGY": 60,
    "PRODUCTION": 40,
    "OPERATOR": 20,
    "VIEWER": 10,
    "EDITOR": 30
}

ROLE_CAPABILITIES = {
    "ADMIN": {
        "recipe_view",
        "recipe_download",
        "recipe_edit",
        "recipe_copy",
        "recipe_submit_review",
        "recipe_approve",
        "recipe_archive",
        "recipe_permanent_delete",
        "engineering_config",
        "admin_config",
        "user_manage",
        "session_manage",
        "audit_view"
    },
    # Engineering is below ADMIN. It can maintain engineering/PLC/master data
    # and perform technical recipe work, but it cannot manage users/sessions.
    "ENGINEERING": {
        "recipe_view",
        "recipe_download",
        "recipe_edit",
        "recipe_copy",
        "recipe_submit_review",
        "recipe_approve",
        "engineering_config",
        "audit_view"
    },
    "TECHNOLOGY": {
        "recipe_view",
        "recipe_download",
        "recipe_edit",
        "recipe_copy",
        "recipe_submit_review",
        "recipe_approve"
    },
    "PRODUCTION": {
        "recipe_view",
        "recipe_download",
        "recipe_edit",
        "recipe_copy",
        "recipe_submit_review"
    },
    "OPERATOR": {
        "recipe_view",
        "recipe_download"
    },
    # Viewer is a final CRS role. It can only view current database recipe values
    # and read-only recipe/history screens. It cannot download, upload, save,
    # approve, configure, or manage users/sessions.
    "VIEWER": {
        "recipe_view"
    },
    # Legacy editor remains supported for existing accounts only.
    "EDITOR": {
        "recipe_view",
        "recipe_download",
        "recipe_edit",
        "recipe_copy",
        "recipe_submit_review"
    }
}

ROLE_LABELS = {
    "ADMIN": "Administrator / Super User",
    "ENGINEERING": "Engineering / Technical Maintenance",
    "TECHNOLOGY": "Technology / Approval",
    "PRODUCTION": "Production / Recipe Preparation",
    "OPERATOR": "Operator / Download Only",
    "VIEWER": "Viewer / Read Only",
    "EDITOR": "Legacy Editor"
}

PROTECTED_SUPER_USERS = {
    "admin",
    "hardik"
}


def normalize_role(role):
    return (role or "").upper()


def role_can(role, capability):
    return capability in ROLE_CAPABILITIES.get(
        normalize_role(role),
        set()
    )


def role_options():
    return list(FINAL_ROLES)


def role_label(role):
    return ROLE_LABELS.get(
        normalize_role(role),
        normalize_role(role)
    )


def role_rank(role):
    return ROLE_HIERARCHY.get(
        normalize_role(role),
        0
    )


def is_admin_role(role):
    return normalize_role(role) == "ADMIN"


def is_engineering_or_above(role):
    return role_rank(role) >= ROLE_HIERARCHY["ENGINEERING"]


def is_protected_super_user(username):
    return (username or "").strip().lower() in PROTECTED_SUPER_USERS
