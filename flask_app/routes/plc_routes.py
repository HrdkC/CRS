import subprocess

from flask import (
    render_template,
    request,
    redirect,
    session,
    flash
)

from database.plc_program_history_manager import (
    PLCProgramHistoryManager
)

from database.audit_manager import (
    AuditManager
)

from database.plc_registry_manager import (
    PLCRegistryManager
)

from database.stage_manager import (
    StageManager
)

from database.plc_verification_manager import (
    PLCVerificationManager
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


def _plc_expected_sync_allowed():
    return (
        session.get("logged_in")
        and
        session.get("role") in ("ADMIN", "ENGINEERING")
    )


def _request_metadata():
    forwarded_for = request.headers.get("X-Forwarded-For")
    client_ip = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else request.remote_addr
    )

    return {
        "forwarded_for": forwarded_for,
        "client_ip": client_ip,
        "request_host": request.host,
        "user_agent": request.headers.get("User-Agent"),
        "workstation_name": (
            request.headers.get("X-Workstation-Name")
            or request.headers.get("X-Client-Workstation")
            or request.headers.get("X-Forwarded-Host")
            or request.host
        ),
    }


def register_plc_routes(app):

    @app.route("/plcs")
    def plcs():

        if not _engineering_config_allowed():

            return redirect("/")

        plcs = (
            PLCRegistryManager.get_all_plcs()
        )

        return render_template(

            "plcs/plcs.html",

            plcs=plcs

        )

    @app.route(
        "/plcs/create",
        methods=["GET", "POST"]
    )
    def create_plc():

        if not _engineering_config_allowed():

            return redirect("/")

        if request.method == "POST":

            PLCRegistryManager.create_plc(

                machine_stage_id=request.form.get(
                    "machine_stage_id"
                ),

                plc_name=request.form.get(
                    "plc_name"
                ),

                ip_address=request.form.get(
                    "ip_address"
                ),

                controller_type=request.form.get(
                    "controller_type"
                ),

                firmware_revision=request.form.get(
                    "firmware_revision"
                ),

                program_revision=request.form.get(
                    "program_revision"
                ),

                processor_name=request.form.get(
                    "processor_name"
                ),

                plc_software=request.form.get(
                    "plc_software"
                ),

                description=request.form.get(
                    "description"
                ),

                created_by=session["username"]

            )

            return redirect(
                "/plcs"
            )

        stages = (
            StageManager
            .get_all_stages_with_machine()
        )

        return render_template(

            "plcs/create_plc.html",

            stages=stages

        )
        
    @app.route(
        "/plcs/edit/<int:plc_id>",
        methods=["GET", "POST"]
    )
    def edit_plc(

        plc_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        plc = (
            PLCRegistryManager
            .get_plc_by_id(
                plc_id
            )
        )

        if request.method == "POST":

            old_plc = (

                PLCRegistryManager.update_plc(

                    plc_id=plc_id,

                    ip_address=request.form.get(
                        "ip_address"
                    ),

                    controller_type=request.form.get(
                        "controller_type"
                    ),

                    firmware_revision=request.form.get(
                        "firmware_revision"
                    ),

                    program_revision=request.form.get(
                        "program_revision"
                    ),

                    processor_name=request.form.get(
                        "processor_name"
                    ),

                    plc_software=request.form.get(
                        "plc_software"
                    ),

                    description=request.form.get(
                        "description"
                    )

                )

            )

            if (

                old_plc[
                    "program_revision"
                ]

                !=

                request.form.get(
                    "program_revision"
                )

            ):

                PLCProgramHistoryManager.create_history(

                    plc_id=plc_id,

                    old_program_revision=
                    old_plc[
                        "program_revision"
                    ],

                    new_program_revision=
                    request.form.get(
                        "program_revision"
                    ),

                    username=
                    session[
                        "username"
                    ]

                )

            AuditManager.log_event(

                username=
                session["username"],

                role=
                session["role"],

                action=
                "PLC_UPDATED",

                change_source=
                "WEB",

                record_id=
                str(plc_id)

            )

            return redirect(
                "/plcs"
            )

        return render_template(

            "plcs/edit_plc.html",

            plc=plc

        )
        
    @app.route(
        "/plcs/test_connection/<int:plc_id>"
    )
    def test_connection(

        plc_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        plc = (
            PLCRegistryManager
            .get_plc_by_id(
                plc_id
            )
        )

        try:

            result = subprocess.run(

                [
                    "ping",
                    "-n",
                    "1",
                    plc["ip_address"]
                ],

                capture_output=True,

                text=True,

                timeout=5

            )

            if result.returncode == 0:

                status = "ONLINE"

            else:

                status = "OFFLINE"

        except Exception:

            status = "ERROR"

        return render_template(

            "plcs/test_connection.html",

            plc=plc,

            status=status

        )
        
    @app.route(
        "/plcs/verify/<int:plc_id>"
    )
    def verify_plc(

        plc_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        plc = (
            PLCRegistryManager
            .get_plc_by_id(
                plc_id
            )
        )

        if not plc:

            flash(
                "PLC record not found.",
                "error"
            )

            return redirect("/plcs")

        try:

            result = (
                PLCVerificationManager
                .verify_plc(

                    plc_id,

                    plc[
                        "ip_address"
                    ]

                )
            )

        except Exception as exc:

            result = {

                "expected_processor": "-",

                "actual_processor": "-",

                "expected_firmware": "-",

                "actual_firmware": "-",

                "program_name": "-",

                "serial_number": "-",

                "verification_status": "OFFLINE",

                "message": (
                    "PLC verification could not connect: "
                    f"{exc}"
                )

            }

        return render_template(

            "plcs/verify_plc.html",

            plc=plc,

            result=result,

            sync_expected_allowed=_plc_expected_sync_allowed()

        )

    @app.route(
        "/plcs/verify/<int:plc_id>/sync-expected",
        methods=["POST"]
    )
    def sync_expected_plc_identity(plc_id):

        if not _plc_expected_sync_allowed():

            flash(
                "Only ADMIN or ENGINEERING can sync expected PLC details.",
                "error"
            )

            return redirect(f"/plcs/verify/{plc_id}")

        reason = (
            request.form.get("reason")
            or ""
        ).strip()

        if not reason:

            flash(
                "Reason is required before updating expected PLC details.",
                "warning"
            )

            return redirect(f"/plcs/verify/{plc_id}")

        try:

            meta = _request_metadata()

            PLCVerificationManager.sync_expected_from_actual(
                plc_id=plc_id,
                username=session.get("username", "SYSTEM"),
                role=session.get("role", "SYSTEM"),
                reason=reason,
                workstation_name=meta["workstation_name"],
                client_ip=meta["client_ip"],
                user_agent=meta["user_agent"],
                forwarded_for=meta["forwarded_for"],
                request_host=meta["request_host"],
            )

            flash(
                "Expected PLC details updated from latest online PLC verification. Audit recorded.",
                "success"
            )

        except Exception as exc:

            flash(
                f"Could not sync expected PLC details: {exc}",
                "error"
            )

        return redirect(f"/plcs/verify/{plc_id}")
        
    @app.route("/plcs/disable/<int:plc_id>", methods=["POST"])
    def disable_plc(

        plc_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        PLCRegistryManager.disable_plc(
            plc_id
        )

        return redirect(
            "/plcs"
        )

    @app.route("/plcs/enable/<int:plc_id>", methods=["POST"])
    def enable_plc(

        plc_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        PLCRegistryManager.enable_plc(
            plc_id
        )

        return redirect(
            "/plcs"
        )
