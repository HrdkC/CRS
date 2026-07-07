from flask import (
    render_template,
    request,
    redirect,
    session,
    flash
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
                    .get_active_families()
                )

                flash("Machine already exists.", "warning")

                return render_template(

                    "machines/create_machine.html",

                    families=families,

                    error="Machine Already Exists",

                    machine_code=machine_code,

                    family_id=request.form.get("family_id"),

                    description=request.form.get("description")

                )

            try:

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

            except ValueError as exc:

                families = (
                    TBMFamilyManager
                    .get_active_families()
                )

                flash(str(exc), "warning")

                return render_template(
                    "machines/create_machine.html",
                    families=families,
                    machine_code=machine_code,
                    family_id=request.form.get("family_id"),
                    description=request.form.get("description")
                )

            except Exception:

                families = (
                    TBMFamilyManager
                    .get_active_families()
                )

                flash(
                    "Machine could not be created. Check the database setup and try again.",
                    "danger"
                )

                return render_template(
                    "machines/create_machine.html",
                    families=families,
                    machine_code=machine_code,
                    family_id=request.form.get("family_id"),
                    description=request.form.get("description")
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
            .get_active_families()
        )

        return render_template(

            "machines/create_machine.html",

            families=families

        )

    @app.route(
        "/machines/change-family/<int:machine_id>",
        methods=["GET", "POST"]
    )
    def change_machine_family(

        machine_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        machine = MachineManager.get_machine_with_family_by_id(
            machine_id
        )

        if not machine:

            flash("Machine record was not found.", "warning")

            return redirect("/machines")

        families = [
            family
            for family in (
                TBMFamilyManager
                .get_active_families()
            )
            if str(family["id"]) != str(machine.get("family_id"))
        ]

        if request.method == "POST":

            target_family_id = request.form.get(
                "family_id"
            )

            reason = (
                request.form.get("reason")
                or ""
            ).strip()

            if not reason:

                flash(
                    "Change reason is required for machine family reassignment.",
                    "warning"
                )

                return render_template(
                    "machines/change_family.html",
                    machine=machine,
                    families=families,
                    family_id=target_family_id
                )

            try:

                result = MachineManager.reassign_family(
                    machine_id=machine_id,
                    family_id=target_family_id
                )

            except ValueError as exc:

                flash(str(exc), "warning")

                return render_template(
                    "machines/change_family.html",
                    machine=machine,
                    families=families,
                    family_id=target_family_id
                )

            except Exception:

                flash(
                    "Machine family could not be changed. No change was confirmed.",
                    "danger"
                )

                return render_template(
                    "machines/change_family.html",
                    machine=machine,
                    families=families,
                    family_id=target_family_id
                )

            old = result["old"]
            new = result["new"]

            AuditManager.log_event(
                username=session["username"],
                role=session["role"],
                action="MACHINE_FAMILY_REASSIGNED",
                change_source="WEB_MASTER_DATA",
                record_id=new.get("machine_code"),
                old_value=(
                    f"{old.get('family_name')} "
                    f"(family_id={old.get('family_id')})"
                ),
                new_value=(
                    f"{new.get('family_name')} "
                    f"(family_id={new.get('family_id')})"
                ),
                reason=reason
            )

            flash(
                "Machine family reassigned. Machine-owned recipes, stages, "
                "PLC records, and templates remain linked to this machine.",
                "success"
            )

            return redirect("/machines")

        return render_template(
            "machines/change_family.html",
            machine=machine,
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

        try:

            machine = MachineManager.get_machine_with_family_by_id(
                machine_id
            )

            if not machine:

                raise ValueError("Machine record was not found.")

            MachineManager.disable_machine(
                machine_id
            )

        except ValueError as exc:

            flash(str(exc), "warning")

            return redirect("/machines")

        except Exception:

            flash(
                "Machine could not be disabled. No change was confirmed.",
                "danger"
            )

            return redirect("/machines")

        AuditManager.log_event(

            username=session["username"],

            role=session["role"],

            action="MACHINE_DISABLED",

            change_source="WEB",

            record_id=(
                machine.get("machine_code")
                if machine
                else str(machine_id)
            ),

            old_value="ACTIVE",

            new_value="DISABLED",

            reason="Machine disabled from machine registry."

        )

        flash("Machine disabled.", "success")

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

        try:

            machine = MachineManager.get_machine_with_family_by_id(
                machine_id
            )

            if not machine:

                raise ValueError("Machine record was not found.")

            MachineManager.enable_machine(
                machine_id
            )

        except ValueError as exc:

            flash(str(exc), "warning")

            return redirect("/machines")

        except Exception:

            flash(
                "Machine could not be enabled. No change was confirmed.",
                "danger"
            )

            return redirect("/machines")

        AuditManager.log_event(

            username=session["username"],

            role=session["role"],

            action="MACHINE_ENABLED",

            change_source="WEB",

            record_id=(
                machine.get("machine_code")
                if machine
                else str(machine_id)
            ),

            old_value="DISABLED",

            new_value="ACTIVE",

            reason="Machine enabled from machine registry."

        )

        flash("Machine enabled.", "success")

        return redirect("/machines")
