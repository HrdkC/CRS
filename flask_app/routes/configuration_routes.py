from flask import (
    flash,
    redirect,
    render_template,
    session,
)

from database.configuration_readiness_manager import (
    ConfigurationReadinessManager,
)
from flask_app.security.role_guard import role_can
from flask_app.stage_url_helper import (
    add_machine_stage_url_fields,
    get_machine_stage_context_by_code,
    machine_stage_url,
)


def _engineering_config_allowed():
    return (
        session.get("logged_in")
        and
        role_can(
            session.get("role"),
            "engineering_config",
        )
    )


def _decorate_report(report):
    context = report["context"]
    add_machine_stage_url_fields(context)

    report["setup_url"] = machine_stage_url(
        "/configuration",
        context=context,
    )
    report["recipes_url"] = machine_stage_url(
        "/recipes",
        context=context,
    )
    report["create_recipe_url"] = machine_stage_url(
        "/recipes/create",
        context=context,
    )
    report["parameters_url"] = machine_stage_url(
        "/parameters",
        context=context,
    )
    report["plc_tags_url"] = machine_stage_url(
        "/plc-tags",
        context=context,
    )
    report["phase_master_url"] = machine_stage_url(
        "/phase-controls",
        context=context,
    )
    report["plc_array_import_url"] = machine_stage_url(
        "/plc-array-import",
        context=context,
    )

    for section in report["sections"]:
        for item in section["items"]:
            purpose = item.get("action")
            if purpose:
                item["action_url"] = machine_stage_url(
                    "/plc-tags",
                    context=context,
                    query={
                        "purpose": purpose,
                        "online_search": 1,
                        "search": purpose.replace("_", " ").title(),
                    },
                )

    return report


def register_configuration_routes(app):

    @app.route("/configuration")
    def configuration_center():
        if not _engineering_config_allowed():
            return redirect("/")

        reports = [
            _decorate_report(report)
            for report in ConfigurationReadinessManager.get_all_reports()
        ]

        status_counts = {
            "ready": 0,
            "warning": 0,
            "blocked": 0,
        }
        for report in reports:
            status_counts[report["status_class"]] += 1

        return render_template(
            "configuration/index.html",
            reports=reports,
            status_counts=status_counts,
        )

    @app.route("/configuration/<machine_code>/<stage_code>")
    def configuration_stage(machine_code, stage_code):
        if not _engineering_config_allowed():
            return redirect("/")

        context = get_machine_stage_context_by_code(
            machine_code,
            stage_code,
            include_inactive=True,
        )
        if not context:
            flash("Machine/stage not found.", "error")
            return redirect("/configuration")

        report = ConfigurationReadinessManager.get_report(
            context["machine_id"],
            context["stage_id"],
        )
        if not report:
            flash("Configuration report could not be built.", "error")
            return redirect("/configuration")

        return render_template(
            "configuration/stage_readiness.html",
            report=_decorate_report(report),
            back_url="/configuration",
        )
