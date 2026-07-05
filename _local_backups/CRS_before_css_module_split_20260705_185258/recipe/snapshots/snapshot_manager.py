from datetime import datetime

from database.recipe_manager import (
    RecipeManager
)

from database.upload_history_manager import (
    UploadHistoryManager
)

class SnapshotManager:

    @staticmethod
    def generate_snapshot_code(

        plc_name

    ):

        timestamp = datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

        return (

            f"PLC_{plc_name}_"
            f"{timestamp}"

        )
        
    @staticmethod
    def save_snapshot(

        plc_name,

        parameters

    ):

        snapshot_code = (

            SnapshotManager
            .generate_snapshot_code(

                plc_name

            )

        )

        RecipeManager.create_recipe(

            recipe_code=snapshot_code,

            recipe_name=f"PLC Snapshot {plc_name}",

            created_by="PLC_UPLOAD",

            recipe_description="Uploaded From PLC"

        )

        for display_order, parameter in enumerate(

            parameters,

            start=1

        ):

            RecipeManager.add_parameter(

                recipe_code=snapshot_code,

                version=1,

                display_order=display_order,

                plc_array_index=parameter[
                    "plc_array_index"
                ],

                parameter_group="PLC_UPLOAD",

                category="SNAPSHOT",

                parameter_name=parameter[
                    "parameter_name"
                ],

                recipe_parameter_description=parameter[
                    "parameter_name"
                ],

                plc_tag_name=(

                    f"CRS_Recipe_Data["
                    f"{parameter['plc_array_index']}]"

                ),

                parameter_value=parameter[
                    "parameter_value"
                ],

                data_type="REAL",

                unit="",

                min_value=None,

                max_value=None

            )

        print(

            f"Snapshot Saved : "
            f"{snapshot_code}"

        )

        UploadHistoryManager.log_upload(

            plc_name=plc_name,

            recipe_code=snapshot_code,

            recipe_version=1,

            status="SUCCESS",

            uploaded_by="PLC_UPLOAD"

        )

        return snapshot_code