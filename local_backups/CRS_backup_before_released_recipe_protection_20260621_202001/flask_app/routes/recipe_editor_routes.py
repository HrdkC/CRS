from flask import (
    render_template,
    request,
    redirect,
    session,
    flash
)

from database.recipe_manager import (
    RecipeManager
)

from database.recipe_parameter_value_manager import (
    RecipeParameterValueManager
)

from database.recipe_parameter_audit_manager import (
    RecipeParameterAuditManager
)

from database.recipe_version_manager import (
    RecipeVersionManager
)

from database.recipe_phase_control_manager import (
    RecipePhaseControlManager
)

from helper.datetime_helper import (
    utc_to_ist
)

from database.recipe_approval_manager import (
    RecipeApprovalManager
)

from database.recipe_status_history_manager import (
    RecipeStatusHistoryManager
)

def register_recipe_editor_routes(app):

    @app.route(
        "/recipe-editor/<int:recipe_id>"
    )
    def recipe_editor(

        recipe_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        recipe = (

            RecipeManager
            .get_recipe_by_id(
                recipe_id
            )

        )

        search_text = request.args.get(
            "search",
            ""
        )

        modified_only = request.args.get(
            "modified_only",
            "0"
        )

        jump_tag = request.args.get(
            "jump_tag",
            ""
        )

        page = int(
            request.args.get(
                "page",
                1
            )
        )

        page_size = int(
            request.args.get(
                "page_size",
                50
            )
        )

        values = (
            RecipeParameterValueManager
            .get_recipe_values(
                recipe_id
            )
        )

        if search_text:

            values = [

                row

                for row in values

                if search_text.upper()

                in

                row[
                    "parameter_name"
                ].upper()

            ]

        if modified_only == "1":

            values = [

                row

                for row in values

                if row[
                    "is_modified"
                ] == 1

            ]

        if jump_tag:

            try:

                jump_tag_int = int(
                    jump_tag
                )

                for position, row in enumerate(values):

                    if row[
                        "tag_index"
                    ] >= jump_tag_int:

                        page = (
                            position
                            //
                            page_size
                        ) + 1

                        break

            except:

                pass

        total_parameters = len(
            values
        )

        start_index = (
            (page - 1)
            * page_size
        )

        end_index = (
            start_index
            + page_size
        )

        values = values[
            start_index:end_index
        ]

        summary = (
            RecipeParameterAuditManager
            .get_recipe_summary(
                recipe_id
            )
        )
        
        if summary["last_changed_at"] != "-":

            summary["last_changed_at"] = (
                utc_to_ist(
                    summary["last_changed_at"]
                )
            )
        
        phase_control = (
            RecipePhaseControlManager
            .get_recipe_phase_control(
                recipe_id
            )
        )

        return render_template(

            "recipes/editor.html",

            recipe=recipe,

            values=values,

            summary=summary,
            
            phase_control=phase_control,

            search_text=search_text,

            modified_only=modified_only,

            jump_tag=jump_tag,

            page=page,

            page_size=page_size,

            total_parameters=total_parameters,

        )

    @app.route(
        "/recipe-editor/edit/<int:value_id>",
        methods=["GET", "POST"]
    )
    def edit_recipe_value(

        value_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        value = (
            RecipeParameterValueManager
            .get_recipe_value_by_id(
                value_id
            )
        )

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                value["recipe_id"]
            )
        )

        if (
            recipe
            and
            recipe["status"] == "RELEASED"
        ):

            flash(
                "Released recipe cannot be edited directly. Create a new version for changes.",
                "error"
            )

            return redirect(
                f"/recipe-editor/{value['recipe_id']}"
            )

        if request.method == "POST":

            new_value = float(
                request.form[
                    "parameter_value"
                ]
            )

            RecipeParameterValueManager.update_recipe_value(

                value_id=value_id,

                new_value=new_value,

                changed_by=session.get(
                    "username"
                )

            )

            return redirect(
                f"/recipe-editor/{value['recipe_id']}"
            )

        return render_template(

            "recipes/edit_value.html",

            value=value

        )

    @app.route(
        "/recipe-editor/history/<int:value_id>"
    )
    def recipe_value_history(

        value_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        value = (
            RecipeParameterValueManager
            .get_recipe_value_by_id(
                value_id
            )
        )

        history = (
            RecipeParameterAuditManager
            .get_parameter_history(
                value_id
            )
        )

        for row in history:

            row["changed_at_ist"] = (
                utc_to_ist(
                    row["changed_at"]
                )
            )

        return render_template(

            "recipes/value_history.html",

            value=value,

            history=history

        )

    @app.route(
        "/recipe-editor/versions/<int:recipe_id>"
    )
    def recipe_editor_versions(

        recipe_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                recipe_id
            )
        )

        versions = (
            RecipeVersionManager
            .get_versions(
                recipe_id
            )
        )
        
        for row in versions:

            row["created_at_ist"] = (
                utc_to_ist(
                    row["created_at"]
                )
            )

        return render_template(

            "recipes/versions.html",

            recipe=recipe,

            versions=versions

        )

    @app.route(
        "/recipe-editor/create-version/<int:recipe_id>",
        methods=["GET", "POST"]
    )
    def recipe_editor_create_version(

        recipe_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                recipe_id
            )
        )

        if request.method == "POST":

            RecipeVersionManager.create_version(

                recipe_id=recipe_id,

                version_comment=request.form[
                    "version_comment"
                ],

                created_by=session.get(
                    "username"
                )

            )

            return redirect(
                f"/recipe-editor/versions/{recipe_id}"
            )

        return render_template(

            "recipes/create_version.html",

            recipe=recipe

        )

    @app.route(
        "/recipe-editor/restore-version/<int:version_id>"
    )
    def recipe_editor_restore_version(

        version_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        RecipeVersionManager.restore_version(

            recipe_version_id=version_id,

            restored_by=session.get(
                "username"
            )

        )

        return redirect(
            request.referrer
            or "/dashboard"
        )
        
    @app.route(
        "/recipe-editor/status/<int:recipe_id>/<status>",
        methods=["GET", "POST"]
    )
    def recipe_status_change(

        recipe_id,

        status

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        valid_status = [

            "DRAFT",

            "REVIEW",

            "APPROVED"

        ]

        if status not in valid_status:

            return redirect("/")

        remarks = (
            request.form.get("remarks")
            or
            request.args.get("remarks")
            or
            ""
        ).strip()

        if status == "REVIEW":

            success, message = (
                RecipeApprovalManager
                .submit_for_review(

                    recipe_id=recipe_id,

                    username=session["username"],

                    remarks=remarks

                )
            )

        elif status == "APPROVED":

            success, message = (
                RecipeApprovalManager
                .approve_recipe(

                    recipe_id=recipe_id,

                    username=session["username"],

                    remarks=remarks

                )
            )

        elif status == "DRAFT":

            if not remarks:

                flash(
                    "Rejection remarks required",
                    "error"
                )

                return redirect(
                    f"/recipe-editor/{recipe_id}"
                )

            success, message = (
                RecipeApprovalManager
                .reject_recipe(

                    recipe_id=recipe_id,

                    username=session["username"],

                    remarks=remarks

                )
            )

        else:

            success = False

            message = (
                "Direct release is blocked. "
                "Approve recipe to auto release."
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

        return redirect(
            f"/recipe-editor/{recipe_id}"
        )
        
    @app.route(
        "/recipe-editor/status-history/<int:recipe_id>"
    )
    def recipe_status_history(

        recipe_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        history = (
            RecipeStatusHistoryManager
            .get_history(
                recipe_id
            )
        )

        for row in history:

            row["changed_at_ist"] = (
                utc_to_ist(
                    row["changed_at"]
                )
            )

        return render_template(

            "recipes/status_history.html",

            history=history

        )
