from flask import redirect, render_template, session


HELP_TOPICS = {
    "user-manual": {
        "title": "User Manual",
        "kicker": "CRS Help",
        "summary": "Role-wise guide for recipe search, editing, review, approval, PLC buffer operations, and audit traceability.",
        "sections": [
            {
                "title": "Operator",
                "items": [
                    "Open Dashboard and select the required recipe stage from Production > Recipe Workspace.",
                    "Open current released recipes for viewing and PLC buffer operation only.",
                    "Do not edit recipe values unless your assigned role allows it."
                ]
            },
            {
                "title": "Production",
                "items": [
                    "Create draft recipes, copy existing recipes, and edit current production values with audit.",
                    "Use Recipe Restore before Download To PLC when the CRS buffer must be refreshed from database values.",
                    "Use Recipe Save after PLC upload when CRS buffer values must update the database."
                ]
            },
            {
                "title": "Technology / Engineering",
                "items": [
                    "Review pending recipes, approve or reject with remarks, and maintain machine/stage configuration.",
                    "Maintain PLC mapping, parameter definitions, units, limits, and phase-control structures.",
                    "Check Audit History after any critical value, PLC, user, or configuration change."
                ]
            }
        ]
    },
    "operator-guide": {
        "title": "Operator Guide",
        "kicker": "Shop Floor",
        "summary": "Minimal operating sequence for safe recipe use on production machines.",
        "sections": [
            {
                "title": "Recipe Download",
                "items": [
                    "Select the correct machine and stage.",
                    "Open the current production recipe.",
                    "Start PLC buffer operation and wait until the progress panel shows success.",
                    "If any warning appears, stop and inform Production or Engineering."
                ]
            },
            {
                "title": "Safety Rules",
                "items": [
                    "No partial download is allowed.",
                    "Recipe values must pass database min/max and PLC readback checks.",
                    "Machine manual mode and PLC interlocks must be true before download."
                ]
            }
        ]
    },
    "engineering-manual": {
        "title": "Engineering Manual",
        "kicker": "Configuration",
        "summary": "Machine-first setup reference for TBM family, machine, stage, PLC, tags, units, and template data.",
        "sections": [
            {
                "title": "Configuration Order",
                "items": [
                    "Create or verify TBM family.",
                    "Create machine and stage records.",
                    "Register PLC for each machine/stage.",
                    "Import or maintain parameter definitions and PLC tag mappings.",
                    "Validate sample recipe and PLC buffer operation before production use."
                ]
            },
            {
                "title": "Change Control",
                "items": [
                    "Use reasons for PLC, parameter, user, and recipe changes.",
                    "Keep historical recipe versions locked.",
                    "Use Audit History and Audit Archive for traceability and retention."
                ]
            }
        ]
    },
    "system-info": {
        "title": "System Information",
        "kicker": "CRS Reference",
        "summary": "Current operating principles and deployment assumptions for Apollo CRS.",
        "sections": [
            {
                "title": "Core Principles",
                "items": [
                    "Database is master.",
                    "SQLite is used for development; MySQL migration is planned for production scaling.",
                    "UTC is stored in database; IST is displayed in the user interface.",
                    "All important changes must be auditable with user, role, reason, old value, new value, machine, stage, and timestamp."
                ]
            },
            {
                "title": "Production Hardening",
                "items": [
                    "Use hashed passwords, role-based access, session controls, parameterized queries, backups, and audit export.",
                    "Keep PLC, database, file, and user-input failures as warnings/errors on screen instead of application crashes.",
                    "Use Waitress or approved production server setup for plant intranet deployment."
                ]
            }
        ]
    }
}


def register_help_routes(app):

    @app.route("/help")
    def help_home():

        if not session.get("logged_in"):
            return redirect("/login")

        return render_template(
            "help/help.html",
            topics=HELP_TOPICS,
            selected_topic=None
        )

    @app.route("/help/<topic_key>")
    def help_topic(topic_key):

        if not session.get("logged_in"):
            return redirect("/login")

        topic = HELP_TOPICS.get(topic_key)
        if not topic:
            return redirect("/help")

        return render_template(
            "help/help.html",
            topics=HELP_TOPICS,
            selected_topic=topic,
            selected_topic_key=topic_key
        )
