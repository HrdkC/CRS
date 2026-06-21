import subprocess

from flask import (
    render_template,
    request,
    redirect,
    session
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

def register_plc_routes(app):

    @app.route("/plcs")
    def plcs():

        if session.get("role") != "ADMIN":

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

        if session.get("role") != "ADMIN":

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

        if session.get(
            "role"
        ) != "ADMIN":

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

        if session.get(
            "role"
        ) != "ADMIN":

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

        if session.get(
            "role"
        ) != "ADMIN":

            return redirect("/")

        plc = (
            PLCRegistryManager
            .get_plc_by_id(
                plc_id
            )
        )

        result = (
            PLCVerificationManager
            .verify_plc(

                plc_id,

                plc[
                    "ip_address"
                ]

            )
        )

        return render_template(

            "plcs/verify_plc.html",

            plc=plc,

            result=result

        )
        
    @app.route("/plcs/disable/<int:plc_id>")
    def disable_plc(

        plc_id

    ):

        if session.get(
            "role"
        ) != "ADMIN":

            return redirect("/")

        PLCRegistryManager.disable_plc(
            plc_id
        )

        return redirect(
            "/plcs"
        )

    @app.route("/plcs/enable/<int:plc_id>")
    def enable_plc(

        plc_id

    ):

        if session.get(
            "role"
        ) != "ADMIN":

            return redirect("/")

        PLCRegistryManager.enable_plc(
            plc_id
        )

        return redirect(
            "/plcs"
        )