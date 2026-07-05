from database.system_settings_manager import (
    SystemSettingsManager
)

SystemSettingsManager.set_setting(

    "TIMEZONE",

    "Asia/Kolkata",

    "Default Application Timezone"

)

SystemSettingsManager.set_setting(

    "SESSION_TIMEOUT_MINUTES",

    "30",

    "Automatic Session Logout"

)

SystemSettingsManager.set_setting(

    "SINGLE_SESSION_PER_USER",

    "1",

    "Allow Only One Active Session"

)

SystemSettingsManager.set_setting(

    "AUDIT_RETENTION_DAYS",

    "3650",

    "Audit History Retention"

)

print(
    "System Settings Seeded"
)