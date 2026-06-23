from flask import (

    render_template,

    request,

    session,

    redirect

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

            TBMFamilyManager.create_family(

                family_name=family_name,

                description=description,

                created_by=session["username"]

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
        "/families/disable/<int:family_id>"
    )
    def disable_family(

        family_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        TBMFamilyManager.disable_family(
            family_id
        )

        AuditManager.log_event(

            username=session["username"],

            role=session["role"],

            action="TBM_FAMILY_DISABLED",

            change_source="WEB",

            record_id=str(family_id)

        )

        return redirect("/families")

    @app.route(
        "/families/enable/<int:family_id>"
    )
    def enable_family(

        family_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        TBMFamilyManager.enable_family(
            family_id
        )

        AuditManager.log_event(

            username=session["username"],

            role=session["role"],

            action="TBM_FAMILY_ENABLED",

            change_source="WEB",

            record_id=str(family_id)

        )

        return redirect("/families")