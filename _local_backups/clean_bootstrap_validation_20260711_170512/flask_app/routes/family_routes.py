from flask import (

    render_template,

    request,

    session,

    redirect,

    flash

)

from database.tbm_family_manager import (
    TBMFamilyManager
)

from database.audit_manager import (
    AuditManager
)


from flask_app.security.role_guard import (
    role_can
)


def _engineering_config_allowed():
    return (
        session.get("logged_in")
        and
        role_can(
            session.get("role"),
            "engineering_config"
        )
    )


def register_family_routes(

    app

):

    @app.route("/families")
    def families():

        if not _engineering_config_allowed():

            return redirect("/")

        families = (
            TBMFamilyManager.get_all_families()
        )

        return render_template(

            "families/families.html",

            families=families

        )

    @app.route(
        "/families/create",
        methods=["GET", "POST"]
    )
    def create_family():

        if not _engineering_config_allowed():

            return redirect("/")

        if request.method == "POST":

            family_name = request.form.get(
                "family_name"
            )

            description = request.form.get(
                "description"
            )

            try:

                TBMFamilyManager.create_family(

                    family_name=family_name,

                    description=description,

                    created_by=session["username"]

                )

            except ValueError as exc:

                flash(str(exc), "warning")

                return render_template(
                    "families/create_family.html",
                    family_name=family_name,
                    description=description
                )

            except Exception:

                flash(
                    "Family could not be created. Check the database setup and try again.",
                    "danger"
                )

                return render_template(
                    "families/create_family.html",
                    family_name=family_name,
                    description=description
                )

            AuditManager.log_event(

                username=session["username"],

                role=session["role"],

                action="TBM_FAMILY_CREATED",

                change_source="WEB",

                record_id=family_name

            )

            return redirect("/families")

        return render_template(
            "families/create_family.html"
        )

    @app.route(
        "/families/edit/<int:family_id>",
        methods=["GET", "POST"]
    )
    def edit_family(

        family_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        family = TBMFamilyManager.get_family_by_id(
            family_id
        )

        if not family:

            flash("Family record was not found.", "warning")

            return redirect("/families")

        linked_machines = TBMFamilyManager.get_linked_machines(
            family_id
        )

        if request.method == "POST":

            family_name = request.form.get(
                "family_name"
            )

            description = request.form.get(
                "description"
            )

            reason = (
                request.form.get("reason")
                or ""
            ).strip()

            if not reason:

                flash(
                    "Change reason is required for family master edit.",
                    "warning"
                )

                return render_template(
                    "families/edit_family.html",
                    family=family,
                    linked_machines=linked_machines,
                    family_name=family_name,
                    description=description
                )

            try:

                result = TBMFamilyManager.update_family(
                    family_id=family_id,
                    family_name=family_name,
                    description=description
                )

            except ValueError as exc:

                flash(str(exc), "warning")

                return render_template(
                    "families/edit_family.html",
                    family=family,
                    linked_machines=linked_machines,
                    family_name=family_name,
                    description=description
                )

            except Exception:

                flash(
                    "Family details could not be saved. No change was confirmed.",
                    "danger"
                )

                return render_template(
                    "families/edit_family.html",
                    family=family,
                    linked_machines=linked_machines,
                    family_name=family_name,
                    description=description
                )

            old = result["old"]
            new = result["new"]

            AuditManager.log_event(
                username=session["username"],
                role=session["role"],
                action="TBM_FAMILY_UPDATED",
                change_source="WEB_MASTER_DATA",
                record_id=str(family_id),
                old_value=(
                    f"{old.get('family_name')} | "
                    f"{old.get('description') or ''}"
                ),
                new_value=(
                    f"{new.get('family_name')} | "
                    f"{new.get('description') or ''}"
                ),
                reason=reason
            )

            flash("TBM family details updated.", "success")

            return redirect("/families")

        return render_template(
            "families/edit_family.html",
            family=family,
            linked_machines=linked_machines
        )

    @app.route(
        "/families/disable/<int:family_id>",
        methods=["POST"]
    )
    def disable_family(

        family_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        try:

            family = TBMFamilyManager.disable_family(
                family_id
            )

        except ValueError as exc:

            flash(str(exc), "warning")

            return redirect("/families")

        except Exception:

            flash(
                "Family could not be disabled. No change was confirmed.",
                "danger"
            )

            return redirect("/families")

        AuditManager.log_event(

            username=session["username"],

            role=session["role"],

            action="TBM_FAMILY_DISABLED",

            change_source="WEB",

            record_id=str(family_id),

            old_value=family.get("family_name"),

            new_value="DISABLED",

            reason="Family disabled from master registry."

        )

        flash("TBM family disabled.", "success")

        return redirect("/families")

    @app.route(
        "/families/enable/<int:family_id>",
        methods=["POST"]
    )
    def enable_family(

        family_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        try:

            family = TBMFamilyManager.enable_family(
                family_id
            )

        except ValueError as exc:

            flash(str(exc), "warning")

            return redirect("/families")

        except Exception:

            flash(
                "Family could not be enabled. No change was confirmed.",
                "danger"
            )

            return redirect("/families")

        AuditManager.log_event(

            username=session["username"],

            role=session["role"],

            action="TBM_FAMILY_ENABLED",

            change_source="WEB",

            record_id=str(family_id),

            old_value=family.get("family_name"),

            new_value="ACTIVE",

            reason="Family enabled from master registry."

        )

        flash("TBM family enabled.", "success")

        return redirect("/families")

    @app.route(
        "/families/delete/<int:family_id>",
        methods=["POST"]
    )
    def delete_family(

        family_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        reason = (
            request.form.get("reason")
            or ""
        ).strip()

        if not reason:

            flash(
                "Delete reason is required. Use disable when family history must be retained.",
                "warning"
            )

            return redirect("/families")

        try:

            family = TBMFamilyManager.delete_family(
                family_id
            )

        except ValueError as exc:

            flash(str(exc), "warning")

            return redirect("/families")

        except Exception:

            flash(
                "Family could not be deleted. No change was confirmed.",
                "danger"
            )

            return redirect("/families")

        AuditManager.log_event(
            username=session["username"],
            role=session["role"],
            action="TBM_FAMILY_DELETED",
            change_source="WEB_MASTER_DATA",
            record_id=str(family_id),
            old_value=(
                f"{family.get('family_name')} | "
                f"{family.get('description') or ''}"
            ),
            new_value="DELETED",
            reason=reason
        )

        flash("Unused TBM family deleted.", "success")

        return redirect("/families")
