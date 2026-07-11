from flask import (
    render_template,
    request,
    redirect,
    session
)

import json

from database.audit_actions import (
    PLC_CONNECTIVITY_CHECKED
)

from database.audit_manager import (
    AuditManager
)

from database.plc_registry_manager import (
    PLCRegistryManager
)

from database.plc_registry_import_manager import (
    PLCRegistryImportManager
)

from database.stage_manager import (
    StageManager
)

from database.tbm_family_manager import (
    TBMFamilyManager
)

from plc.plc_connectivity_checker import (
    PLCConnectivityChecker
)


def _admin_required():

    return session.get("role") == "ADMIN"


def _get_username():

    return session.get(
        "username",
        "SYSTEM"
    )


def _get_stages():

    return StageManager.get_all_stages()


def _get_suffix_stage_map():

    suffix_stage_map = {}

    for suffix in [
        "KM",
        "PU"
    ]:

        stage_type = request.form.get(
            f"{suffix.lower()}_stage"
        )

        if stage_type:

            suffix_stage_map[suffix] = stage_type

    return suffix_stage_map


def register_plc_registry_routes(app):

    @app.route("/plcs")
    def plcs():

        if not _admin_required():

            return redirect("/")

        plcs = (
            PLCRegistryManager
            .get_all_plcs_with_machine_stage(
                include_inactive=True
            )
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

        if not _admin_required():

            return redirect("/")

        if request.method == "POST":

            try:

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

                    description=request.form.get(
                        "description"
                    ),

                    username=_get_username(),

                    reason=request.form.get(
                        "reason"
                    ),

                    change_source="WEB"

                )

                return redirect("/plcs")

            except ValueError as error:

                return render_template(

                    "plcs/create_plc.html",

                    stages=_get_stages(),

                    error=str(error),

                    form=request.form

                )

        return render_template(

            "plcs/create_plc.html",

            stages=_get_stages(),

            form={}

        )

    @app.route(
        "/plcs/import",
        methods=["GET", "POST"]
    )
    def import_plcs():

        if not _admin_required():

            return redirect("/")

        families = TBMFamilyManager.get_all_families()

        preview = []

        result = None

        error = None

        form = {
            "km_stage": "FIRST_STAGE",
            "pu_stage": "SECOND_STAGE",
            "create_missing_machines": "",
            "create_missing_stages": "1",
            "default_family_id": ""
        }

        if request.method == "POST":

            form = request.form

            suffix_stage_map = _get_suffix_stage_map()

            create_missing_machines = (
                request.form.get(
                    "create_missing_machines"
                )
                ==
                "1"
            )

            create_missing_stages = (
                request.form.get(
                    "create_missing_stages"
                )
                ==
                "1"
            )

            default_family_id = request.form.get(
                "default_family_id"
            )

            if (
                not create_missing_machines
                or
                not default_family_id
            ):

                default_family_id = None

            try:

                if request.form.get("action_type") == "import":

                    result = (
                        PLCRegistryImportManager
                        .import_from_legacy(

                            suffix_stage_map=suffix_stage_map,

                            username=_get_username(),

                            reason=request.form.get(
                                "reason"
                            ),

                            create_missing_machines=(
                                create_missing_machines
                            ),

                            create_missing_stages=(
                                create_missing_stages
                            ),

                            default_family_id=default_family_id

                        )
                    )

                    preview = result["preview"]

                else:

                    preview = (
                        PLCRegistryImportManager
                        .build_preview(

                            suffix_stage_map=suffix_stage_map,

                            create_missing_machines=(
                                create_missing_machines
                            ),

                            create_missing_stages=(
                                create_missing_stages
                            ),

                            default_family_id=default_family_id

                        )
                    )

            except Exception as exception:

                error = str(exception)

        return render_template(

            "plcs/import_plcs.html",

            families=families,

            preview=preview,

            result=result,

            error=error,

            form=form

        )

    @app.route(
        "/plcs/edit/<int:plc_id>",
        methods=["GET", "POST"]
    )
    def edit_plc(plc_id):

        if not _admin_required():

            return redirect("/")

        plc = PLCRegistryManager.get_plc_by_id(
            plc_id
        )

        if not plc:

            return redirect("/plcs")

        if request.method == "POST":

            try:

                PLCRegistryManager.update_plc(

                    plc_id=plc_id,

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

                    description=request.form.get(
                        "description"
                    ),

                    username=_get_username(),

                    reason=request.form.get(
                        "reason"
                    ),

                    change_source="WEB"

                )

                return redirect("/plcs")

            except ValueError as error:

                return render_template(

                    "plcs/edit_plc.html",

                    plc=plc,

                    stages=_get_stages(),

                    error=str(error),

                    form=request.form

                )

        return render_template(

            "plcs/edit_plc.html",

            plc=plc,

            stages=_get_stages(),

            form={}

        )

    @app.route(
        "/plcs/disable/<int:plc_id>",
        methods=["POST"]
    )
    def disable_plc(plc_id):

        if not _admin_required():

            return redirect("/")

        plc = PLCRegistryManager.get_plc_by_id(
            plc_id
        )

        if not plc:

            return redirect("/plcs")

        if request.method == "POST":

            try:

                PLCRegistryManager.disable_plc(

                    plc_id=plc_id,

                    username=_get_username(),

                    reason=request.form.get(
                        "reason"
                    ),

                    change_source="WEB"

                )

                return redirect("/plcs")

            except ValueError as error:

                return render_template(

                    "plcs/plc_reason.html",

                    plc=plc,

                    action="Disable",

                    post_url=f"/plcs/disable/{plc_id}",

                    error=str(error)

                )

        return render_template(

            "plcs/plc_reason.html",

            plc=plc,

            action="Disable",

            post_url=f"/plcs/disable/{plc_id}"

        )

    @app.route(
        "/plcs/enable/<int:plc_id>",
        methods=["POST"]
    )
    def enable_plc(plc_id):

        if not _admin_required():

            return redirect("/")

        plc = PLCRegistryManager.get_plc_by_id(
            plc_id
        )

        if not plc:

            return redirect("/plcs")

        if request.method == "POST":

            try:

                PLCRegistryManager.enable_plc(

                    plc_id=plc_id,

                    username=_get_username(),

                    reason=request.form.get(
                        "reason"
                    ),

                    change_source="WEB"

                )

                return redirect("/plcs")

            except ValueError as error:

                return render_template(

                    "plcs/plc_reason.html",

                    plc=plc,

                    action="Enable",

                    post_url=f"/plcs/enable/{plc_id}",

                    error=str(error)

                )

        return render_template(

            "plcs/plc_reason.html",

            plc=plc,

            action="Enable",

            post_url=f"/plcs/enable/{plc_id}"

        )

    @app.route(
        "/plcs/check/<int:plc_id>",
        methods=["GET", "POST"]
    )
    def check_plc_connectivity(plc_id):

        if not _admin_required():

            return redirect("/")

        plc = PLCRegistryManager.get_plc_by_id(
            plc_id
        )

        if not plc:

            return redirect("/plcs")

        result = None

        if request.method == "POST":

            result = (
                PLCConnectivityChecker
                .check_tcp_port(

                    ip_address=plc["ip_address"],

                    timeout_seconds=2.0

                )
            )

            AuditManager.log_event(

                username=_get_username(),

                role=session.get(
                    "role",
                    "ADMIN"
                ),

                action=PLC_CONNECTIVITY_CHECKED,

                change_source="WEB",

                plc_name=plc["plc_name"],

                record_id=plc["id"],

                new_value=json.dumps(
                    result,
                    sort_keys=True
                ),

                reason=request.form.get(
                    "reason"
                )

            )

        return render_template(

            "plcs/check_plc.html",

            plc=plc,

            result=result

        )
