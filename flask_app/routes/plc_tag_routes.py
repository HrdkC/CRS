from flask import (
    render_template,
    request,
    session,
    redirect,
    flash
)

from urllib.parse import (
    urlencode
)

from database.parameter_definition_manager import (
    ParameterDefinitionManager
)

from database.plc_tag_manager import (
    PLCTagManager
)

from database.audit_manager import (
    AuditManager
)

from database.plc_online_tag_browser_manager import (
    PLCOnlineTagBrowserManager
)

from database.stage_plc_tag_requirement_manager import (
    StagePLCTagRequirementManager
)


from flask_app.security.role_guard import (
    role_can
)

from flask_app.stage_url_helper import (
    get_machine_stage_context_by_code,
    get_machine_stage_context_by_id,
    machine_stage_url,
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



def _tag_purpose_options(machine_id, stage_id):

    requirements = (
        StagePLCTagRequirementManager
        .get_stage_requirements(
            machine_id,
            stage_id,
            active_only=False
        )
    )

    options = []

    for row in requirements:

        purpose = (
            row.get("purpose")
            or
            ""
        ).strip().upper()

        if purpose and purpose not in options:

            options.append(
                purpose
            )

    return options


def _audit_plc_tag_changes(tag_id, tag_name, changes, reason, action="PLC_TAG_CONFIGURATION_UPDATED"):

    for change in changes or []:

        try:

            AuditManager.log_event(
                username=session.get("username"),
                role=session.get("role"),
                action=action,
                change_source="PLC_TAG_GUI_CONFIG",
                record_id=tag_id,
                parameter_name=f"{tag_name}.{change.get('field')}",
                old_value=str(change.get("old") if change.get("old") is not None else ""),
                new_value=str(change.get("new") if change.get("new") is not None else ""),
                reason=reason,
                user_agent=request.headers.get("User-Agent", ""),
                forwarded_for=request.headers.get("X-Forwarded-For"),
                request_host=request.host,
            )

        except Exception:

            pass


def _render_plc_tag_browser(machine_id, stage_id, context=None):

    search_text = request.args.get(
        "search",
        ""
    ).strip()

    purpose_to_assign = request.args.get(
        "purpose",
        ""
    ).strip().upper()

    purpose_requirement = None

    bool_only = request.args.get(
        "bool_only",
        ""
    ).strip()

    array_only = request.args.get(
        "array_only",
        ""
    ).strip()

    online_search = request.args.get(
        "online_search",
        ""
    ).strip() == "1"

    if (
        purpose_to_assign
        and
        not search_text
    ):

        purpose_requirement = (
            StagePLCTagRequirementManager
            .get_stage_requirement(
                machine_id,
                stage_id,
                purpose_to_assign
            )
        )

        search_text = (
            (purpose_requirement or {}).get("search_hint")
            or
            (purpose_requirement or {}).get("default_tag_name")
            or
            PLCTagManager.get_search_hint_for_purpose(
                purpose_to_assign
            )
        )

    elif purpose_to_assign:

        purpose_requirement = (
            StagePLCTagRequirementManager
            .get_stage_requirement(
                machine_id,
                stage_id,
                purpose_to_assign
            )
        )

    tags = (

        PLCTagManager
        .search_tags(

            machine_id=machine_id,

            stage_id=stage_id,

            search_text=search_text,

            bool_only=bool_only == "1"

        )

    )

    if array_only == "1":
        tags = [
            tag
            for tag in tags
            if int(tag.get("is_array") or 0) == 1
        ]

    active_plc = (
        PLCOnlineTagBrowserManager
        .get_active_plc(

            machine_id=machine_id,

            stage_id=stage_id

        )
    )

    online_result = None

    if online_search:

        online_result = (
            PLCOnlineTagBrowserManager
            .search_online_tags(

                machine_id=machine_id,

                stage_id=stage_id,

                search_text=search_text,

                bool_only=bool_only == "1",

                array_only=array_only == "1"

            )
        )

    if context is None:
        context = get_machine_stage_context_by_id(
            machine_id,
            stage_id,
            include_inactive=True
        )

    return render_template(

        "plc_tags/browser.html",

        machine_id=machine_id,

        stage_id=stage_id,

        context=context,

        machine_code=context.get("machine_code") if context else None,

        stage_type=context.get("stage_type") if context else None,

        stage_url_code=context.get("stage_url_code") if context else None,

        machine_stage_title=context.get("machine_stage_display") if context else None,

        plc_tag_browser_url=machine_stage_url("/plc-tags", context=context),

        plc_tag_create_url=machine_stage_url("/plc-tags/create", context=context),

        plc_tag_select_online_url=machine_stage_url("/plc-tags/select-online", context=context),

        plc_array_import_url=machine_stage_url("/plc-array-import", context=context),

        search_text=search_text,

        purpose_to_assign=purpose_to_assign,

        purpose_requirement=purpose_requirement,

        default_tag_name=(
            (purpose_requirement or {}).get("default_tag_name")
            or
            PLCTagManager.get_default_tag_name_for_purpose(
                purpose_to_assign
            )
        ),

        bool_only=bool_only,

        array_only=array_only,

        online_search=online_search,

        active_plc=active_plc,

        online_result=online_result,

        tags=tags,

        tag_purpose_options=_tag_purpose_options(
            machine_id,
            stage_id
        )

    )


def register_plc_tag_routes(app):

    @app.route(
        "/plc-tags/<machine_code>/<stage_code>"
    )
    def plc_tag_browser_named(

        machine_code,

        stage_code

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        context = get_machine_stage_context_by_code(
            machine_code,
            stage_code
        )

        if not context:
            flash(
                "Machine/stage not found. Use friendly route like /plc-tags/P15/FS or /plc-tags/P15/SS.",
                "error"
            )
            return redirect("/machines")

        canonical_url = machine_stage_url(
            "/plc-tags",
            context=context,
            query=request.args
        )
        current_path = f"/plc-tags/{machine_code}/{stage_code}"
        if current_path != canonical_url.split("?")[0]:
            return redirect(canonical_url)

        return _render_plc_tag_browser(
            context["machine_id"],
            context["stage_id"],
            context=context
        )

    @app.route(
        "/plc-tags/<int:machine_id>/<int:stage_id>"
    )
    def plc_tag_browser(

        machine_id,

        stage_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        context = get_machine_stage_context_by_id(
            machine_id,
            stage_id,
            include_inactive=True
        )

        if context:
            return redirect(
                machine_stage_url(
                    "/plc-tags",
                    context=context,
                    query=request.args
                )
            )

        return _render_plc_tag_browser(
            machine_id,
            stage_id,
            context=context
        )


    @app.route(
        "/plc-tags/update/<int:tag_id>",
        methods=["POST"]
    )
    def plc_tag_update(

        tag_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        tag = PLCTagManager.get_tag_by_id(
            tag_id
        )

        if not tag:

            flash(
                "PLC tag not found.",
                "error"
            )

            return redirect(
                request.referrer
                or
                "/dashboard"
            )

        reason = (
            request.form.get("reason")
            or
            "PLC tag configuration updated from GUI"
        ).strip()

        if not reason:

            flash(
                "Enter reason before saving PLC tag configuration.",
                "error"
            )

            return redirect(
                request.form.get("return_url")
                or
                request.referrer
                or
                "/dashboard"
            )

        result = PLCTagManager.update_tag_config(
            tag_id=tag_id,
            tag_name=request.form.get("tag_name", ""),
            tag_type=request.form.get("tag_type", ""),
            is_array=request.form.get("is_array", "0"),
            array_size=request.form.get("array_size", ""),
            array_start_index=request.form.get("array_start_index", ""),
            array_end_index=request.form.get("array_end_index", ""),
            description=request.form.get("description", ""),
            tag_purpose=request.form.get("tag_purpose", ""),
            machine_id=tag["machine_id"],
            stage_id=tag["stage_id"]
        )

        if result.get("success"):

            _audit_plc_tag_changes(
                tag_id=tag_id,
                tag_name=(result.get("new") or {}).get("tag_name") or tag.get("tag_name"),
                changes=result.get("changes"),
                reason=reason
            )

            flash(
                result.get("message") or "PLC tag configuration saved.",
                "success"
            )

        else:

            for error in result.get("errors", [])[:6]:

                flash(
                    error,
                    "error"
                )

        return_url = request.form.get(
            "return_url",
            ""
        )

        if return_url.startswith(
            "/"
        ):

            return redirect(
                return_url
            )

        context = get_machine_stage_context_by_id(
            tag["machine_id"],
            tag["stage_id"],
            include_inactive=True
        )

        return redirect(
            machine_stage_url(
                "/plc-tags",
                context=context
            )
            if context
            else
            (
                request.referrer
                or
                "/dashboard"
            )
        )

    @app.route(
        "/plc-tags/set-purpose/<int:tag_id>",
        methods=["POST"]
    )
    def plc_tag_set_purpose(

        tag_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        tag_purpose = request.form.get(
            "tag_purpose",
            ""
        )

        success, message = (
            PLCTagManager
            .set_tag_purpose(

                tag_id=tag_id,

                tag_purpose=tag_purpose

            )
        )

        if success:

            flash(
                message,
                "success"
            )

        else:

            flash(
                message,
                "error"
            )

        return_url = request.form.get(
            "return_url",
            ""
        )

        if return_url.startswith(
            "/"
        ):

            return redirect(
                return_url
            )

        return redirect(
            request.referrer
            or
            "/dashboard"
        )

    @app.route(
        "/plc-tags/create/<int:machine_id>/<int:stage_id>",
        methods=["POST"]
    )
    def plc_tag_create(

        machine_id,

        stage_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        tag_name = request.form.get(
            "tag_name",
            ""
        ).strip()

        tag_type = request.form.get(
            "tag_type",
            ""
        ).strip().upper()

        tag_purpose = request.form.get(
            "tag_purpose",
            ""
        ).strip().upper()

        if not tag_name:

            flash(
                "PLC tag name is required",
                "error"
            )

            return redirect(
                request.referrer
                or
                machine_stage_url("/plc-tags", machine_id=machine_id, stage_id=stage_id)
            )

        try:

            is_array = int(
                request.form.get(
                    "is_array",
                    "0"
                )
            )

            array_size = request.form.get(
                "array_size",
                ""
            ).strip()

            array_start_index = request.form.get(
                "array_start_index",
                ""
            ).strip()

            array_end_index = request.form.get(
                "array_end_index",
                ""
            ).strip()

            tag_id = PLCTagManager.create_tag(

                machine_id=machine_id,

                stage_id=stage_id,

                tag_name=tag_name,

                tag_type=tag_type,

                is_array=is_array,

                array_size=int(array_size)
                if array_size
                else
                None,

                array_start_index=int(array_start_index)
                if array_start_index
                else
                None,

                array_end_index=int(array_end_index)
                if array_end_index
                else
                None,

                description=request.form.get(
                    "description",
                    ""
                ).strip(),

                created_by=session.get(
                    "username"
                ),

                tag_purpose=tag_purpose
                if tag_purpose
                else
                None

            )

            if tag_purpose:

                PLCTagManager.set_tag_purpose(

                    tag_id=tag_id,

                    tag_purpose=tag_purpose

                )

            flash(
                f"PLC tag {tag_name} created",
                "success"
            )

        except Exception as ex:

            flash(
                f"PLC tag create failed: {ex}",
                "error"
            )

        return redirect(
            request.referrer
            or
            machine_stage_url("/plc-tags", machine_id=machine_id, stage_id=stage_id)
        )

    @app.route(
        "/plc-tags/select-online/<int:machine_id>/<int:stage_id>",
        methods=["POST"]
    )
    def plc_tag_select_online(

        machine_id,

        stage_id

    ):

        if not _engineering_config_allowed():

            return redirect("/")

        tag_name = request.form.get(
            "tag_name",
            ""
        ).strip()

        tag_purpose = request.form.get(
            "tag_purpose",
            ""
        ).strip().upper()

        if not tag_name:

            flash(
                "Online PLC tag name is required",
                "error"
            )

            return redirect(
                request.referrer
                or
                machine_stage_url("/plc-tags", machine_id=machine_id, stage_id=stage_id)
            )

        try:

            tag_id, created = PLCTagManager.upsert_tag(

                machine_id=machine_id,

                stage_id=stage_id,

                tag_name=tag_name,

                tag_type=request.form.get(
                    "tag_type",
                    ""
                ).strip().upper(),

                is_array=int(
                    request.form.get(
                        "is_array",
                        "0"
                    )
                ),

                array_size=(
                    int(
                        request.form[
                            "array_size"
                        ]
                    )
                    if request.form.get(
                        "array_size"
                    )
                    else
                    None
                ),

                array_start_index=(
                    int(
                        request.form[
                            "array_start_index"
                        ]
                    )
                    if request.form.get(
                        "array_start_index"
                    )
                    else
                    None
                ),

                array_end_index=(
                    int(
                        request.form[
                            "array_end_index"
                        ]
                    )
                    if request.form.get(
                        "array_end_index"
                    )
                    else
                    None
                ),

                description="Imported from online PLC tag search",

                created_by=session.get(
                    "username"
                ),

                tag_purpose=tag_purpose
                if tag_purpose
                else
                None

            )

            if created:

                flash(
                    f"PLC tag {tag_name} added to CRS.",
                    "success"
                )

            else:

                flash(
                    f"PLC tag {tag_name} updated in CRS.",
                    "success"
                )

        except Exception as ex:

            flash(
                f"Online PLC tag selection failed: {ex}",
                "error"
            )

        redirect_url = (
            machine_stage_url("/plc-tags", machine_id=machine_id, stage_id=stage_id)
            + "?"
            + urlencode(
                {
                    "purpose": tag_purpose,
                    "search": request.form.get(
                        "search_text",
                        ""
                    ),
                    "bool_only": request.form.get(
                        "bool_only",
                        ""
                    )
                }
            )
        )

        return redirect(
            redirect_url
        )

    @app.route(
        "/plc-tags/create/<machine_code>/<stage_code>",
        methods=["POST"]
    )
    def plc_tag_create_named(

        machine_code,

        stage_code

    ):

        context = get_machine_stage_context_by_code(
            machine_code,
            stage_code
        )

        if not context:
            flash(
                "Machine/stage not found. Use friendly route like /plc-tags/create/P15/FS or /plc-tags/create/P15/SS.",
                "error"
            )
            return redirect("/machines")

        return plc_tag_create(
            context["machine_id"],
            context["stage_id"]
        )

    @app.route(
        "/plc-tags/select-online/<machine_code>/<stage_code>",
        methods=["POST"]
    )
    def plc_tag_select_online_named(

        machine_code,

        stage_code

    ):

        context = get_machine_stage_context_by_code(
            machine_code,
            stage_code
        )

        if not context:
            flash(
                "Machine/stage not found. Use friendly route like /plc-tags/select-online/P15/FS or /plc-tags/select-online/P15/SS.",
                "error"
            )
            return redirect("/machines")

        return plc_tag_select_online(
            context["machine_id"],
            context["stage_id"]
        )

    @app.route(
        "/plc-tags/array/<int:tag_id>"
    )
    def array_browser(

        tag_id

    ):

        if not _engineering_config_allowed():

            flash(
                "Engineering configuration permission is required.",
                "error"
            )

            return redirect("/")

        tag = (

            PLCTagManager
            .get_tag_by_id(

                tag_id

            )

        )

        if not tag:

            flash(
                "PLC tag was not found.",
                "warning"
            )

            return redirect("/machines")

        if not tag.get("is_array") or any(
            tag.get(field) is None
            for field in (
                "array_start_index",
                "array_end_index"
            )
        ):

            flash(
                "Selected PLC tag is not configured as an array.",
                "warning"
            )

            return redirect(
                machine_stage_url(
                    "/plc-tags",
                    machine_id=tag.get("machine_id"),
                    stage_id=tag.get("stage_id")
                )
            )

        search_text = request.args.get(
            "search",
            ""
        ).strip()
        
        status_filter = request.args.get(
            "status",
            ""
        ).strip()
        
        jump_index = request.args.get(
            "jump_index",
            ""
        ).strip()

        parameters = (

            ParameterDefinitionManager
            .get_all_parameters_by_machine_stage(

                machine_id=tag[
                    "machine_id"
                ],

                stage_id=tag[
                    "stage_id"
                ]

            )

        )

        mapped = {}

        for parameter in parameters:

            mapped[
                parameter[
                    "plc_array_index"
                ]
            ] = parameter

        indexes = []

        for index in range(

            tag["array_start_index"],

            tag["array_end_index"] + 1

        ):

            parameter = mapped.get(
                index
            )

            status = "AVAILABLE"

            if parameter:

                if parameter["used"] == 1:

                    status = "MAPPED"

                else:

                    status = "DISABLED"

            row = {

                "index": index,

                "parameter": parameter,

                "status": status

            }

            if search_text:

                search_upper = search_text.upper()

                match = False

                if search_text in str(index):

                    match = True

                if parameter:

                    if search_upper in parameter[
                        "parameter_name"
                    ].upper():

                        match = True

                if not match:

                    continue
                
                if status_filter:

                    if status != status_filter:

                        continue

            indexes.append(
                row
            )
            
            if jump_index:

                try:

                    target_index = int(
                        jump_index
                    )

                    indexes = [

                        row

                        for row in indexes

                        if row["index"]
                        ==
                        target_index

                    ]

                except ValueError:

                    pass

        return render_template(

            "plc_tags/array_browser.html",

            tag=tag,

            indexes=indexes,

            search_text=search_text,
            
            status_filter=status_filter,
            
            jump_index=jump_index

        )

    @app.route(
        "/parameters/create-from-array/<int:tag_id>/<int:array_index>",
        methods=["GET", "POST"]
    )
    def create_parameter_from_array(

        tag_id,

        array_index

    ):

        if not _engineering_config_allowed():

            flash(
                "Engineering configuration permission is required.",
                "error"
            )

            return redirect("/")

        tag = (

            PLCTagManager
            .get_tag_by_id(

                tag_id

            )

        )

        if request.method == "POST":

            parameter_name = (

                request.form[
                    "parameter_name"
                ]
                .strip()
                .title()
            )

            ParameterDefinitionManager.create_parameter(

                machine_id=tag[
                    "machine_id"
                ],

                stage_id=tag[
                    "stage_id"
                ],

                tag_index=array_index,

                plc_array_index=array_index,

                parameter_name=parameter_name,

                unit=request.form[
                    "unit"
                ],

                min_value=float(
                    request.form[
                        "min_value"
                    ]
                ),

                max_value=float(
                    request.form[
                        "max_value"
                    ]
                ),

                default_value=float(
                    request.form[
                        "default_value"
                    ]
                ),

                created_by=session.get(
                    "username"
                )

            )

            return redirect(

                f"/plc-tags/array/{tag_id}"

            )

        return render_template(

            "plc_tags/create_parameter.html",

            tag=tag,

            array_index=array_index

        )
        
    @app.route(
    "/plc-tags/next-available/<int:tag_id>"
)
    def next_available_index(

        tag_id

    ):

        if not _engineering_config_allowed():

            flash(
                "Engineering configuration permission is required.",
                "error"
            )

            return redirect("/")

        tag = (

            PLCTagManager
            .get_tag_by_id(

                tag_id

            )

        )

        if not tag:

            flash(
                "PLC tag was not found.",
                "warning"
            )

            return redirect("/machines")

        if not tag.get("is_array") or any(
            tag.get(field) is None
            for field in (
                "array_start_index",
                "array_end_index"
            )
        ):

            flash(
                "Selected PLC tag is not configured as an array.",
                "warning"
            )

            return redirect(
                machine_stage_url(
                    "/plc-tags",
                    machine_id=tag.get("machine_id"),
                    stage_id=tag.get("stage_id")
                )
            )

        parameters = (

            ParameterDefinitionManager
            .get_all_parameters_by_machine_stage(

                machine_id=tag[
                    "machine_id"
                ],

                stage_id=tag[
                    "stage_id"
                ]

            )

        )

        used_indexes = set()

        for parameter in parameters:

            if parameter["used"] == 1:

                used_indexes.add(

                    parameter[
                        "plc_array_index"
                    ]

                )

        for index in range(

            tag[
                "array_start_index"
            ],

            tag[
                "array_end_index"
            ] + 1

        ):

            if index not in used_indexes:

                return redirect(

                    f"/plc-tags/array/{tag_id}?jump_index={index}"

                )

        return redirect(

            f"/plc-tags/array/{tag_id}"

        )
