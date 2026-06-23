FINAL_ROLES = [
    "ADMIN",
    "TECHNOLOGY",
    "PRODUCTION",
    "OPERATOR"
]

LEGACY_ROLES = [
    "EDITOR",
    "VIEWER"
]

VALID_ROLES = FINAL_ROLES + LEGACY_ROLES

ROLE_CAPABILITIES = {
    "ADMIN": {
        "recipe_view",
        "recipe_download",
        "recipe_edit",
        "recipe_copy",
        "recipe_submit_review",
        "recipe_approve",
        "admin_config"
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
    "EDITOR": {
        "recipe_view",
        "recipe_download",
        "recipe_edit",
        "recipe_copy",
        "recipe_submit_review"
    },
    "VIEWER": {
        "recipe_view"
    }
}


def normalize_role(role):

    return (
        role
        or
        ""
    ).upper()


def role_can(role, capability):

    return (
        capability
        in
        ROLE_CAPABILITIES.get(
            normalize_role(role),
            set()
        )
    )


def role_options():

    return list(FINAL_ROLES)
