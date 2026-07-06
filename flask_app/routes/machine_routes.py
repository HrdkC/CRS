from flask import (
    render_template,
    request,
    redirect,
    session
)

from database.tbm_family_manager import (
    TBMFamilyManager
)

from database.machine_manager import (
    MachineManager
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


def register_machine_routes(app):

    @app.route("/machines")
    def machines():

        if not _engineering_config_allowed():

            return redirect("/")

        machines = (
            MachineManager.get_all_machines()
        )

        return render_template(

            "machines/machines.html",

            machines=machines

        )

    @app.route(
        "/machines/create",
        methods=["GET", "POST"]
    )
    def create_machine():

        if not _engineering_config_allowed():

            return redirect("/")

        if request.method == "POST":

            machine_code = request.form.get(
                "machine_code"
            )

            if MachineManager.machine_code_exists(
                machine_code
            ):

                families = (
                    TBMFamilyManager
                    .get_all_families()
                )

                return render_template(

                    "machines/create_machine.html",

                    families=families,

                    error="Machine Already Exists"

                )

            MachineManager.create_machine(

                machine_code=machine_code,

                family_id=request.form.get(
                    "family_id"
                ),

                description=request.form.get(
                    "description"
                ),

                created_by=session["username"]

            )

            AuditManager.log_event(

                username=session["username"],

                role=session["role"],

                action="MACHINE_CREATED",

                change_source="WEB",

                record_id=machine_code

            )

            return redirect(
                "/machines"
            )

        families = (
            TBMFamilyManager
            .get_all_families()
        )

        return render_template(

            "machines/create_machine.html",

            families=families

        )

    @app.route(
        "/machines/disable/<int:machine_id>",
        methods=["POST"]
    )
    def disable_machine(

        machine_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        MachineManager.disable_machine(
            machine_id
        )

        AuditManager.log_event(

            username=session["username"],

            role=session["role"],

            action="MACHINE_DISABLED",

            change_source="WEB",

            record_id=str(machine_id)

        )

        return redirect("/machines")

    @app.route(
        "/machines/enable/<int:machine_id>",
        methods=["POST"]
    )
    def enable_machine(

        machine_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        MachineManager.enable_machine(
            machine_id
        )

        AuditManager.log_event(

            username=session["username"],

            role=session["role"],

            action="MACHINE_ENABLED",

            change_source="WEB",

            record_id=str(machine_id)

        )

        return redirect("/machines")
