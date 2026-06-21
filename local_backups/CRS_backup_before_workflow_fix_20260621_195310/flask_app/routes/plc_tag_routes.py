from flask import (
    render_template,
    request,
    session,
    redirect
)

from database.parameter_definition_manager import (
    ParameterDefinitionManager
)

from database.plc_tag_manager import (
    PLCTagManager
)


def register_plc_tag_routes(app):

    @app.route(
        "/plc-tags/<int:machine_id>/<int:stage_id>"
    )
    def plc_tag_browser(

        machine_id,

        stage_id

    ):

        if not session.get(
            "username"
        ):

            return redirect("/")

        search_text = request.args.get(
            "search",
            ""
        )

        tags = (

            PLCTagManager
            .search_tags(

                machine_id=machine_id,

                stage_id=stage_id,

                search_text=search_text

            )

        )

        return render_template(

            "plc_tags/browser.html",

            machine_id=machine_id,

            stage_id=stage_id,

            search_text=search_text,

            tags=tags

        )

    @app.route(
        "/plc-tags/array/<int:tag_id>"
    )
    def array_browser(

        tag_id

    ):

        tag = (

            PLCTagManager
            .get_tag_by_id(

                tag_id

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

        tag = (

            PLCTagManager
            .get_tag_by_id(

                tag_id

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