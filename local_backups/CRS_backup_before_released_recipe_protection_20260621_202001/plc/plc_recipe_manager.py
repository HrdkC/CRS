# plc/plc_recipe_manager.py

from database.recipe_manager import RecipeManager
from plc.plc_connection import PLCConnection
from database.plc_manager_legacy import PLCManager
from database.plc_parameter_mapping_manager import (
    PLCParameterMappingManager
)
from database.download_history_manager import (
    DownloadHistoryManager
)

class PLCRecipeManager:

    @staticmethod
    def build_plc_array(

        plc_name,

        recipe_code,

        version=1,

        array_size=350

    ):

        plc_array = [0.0] * array_size

        recipe = RecipeManager.get_recipe(

            recipe_code=recipe_code,

            version=version

        )

        mapping_count = 0

        for parameter in recipe:

            parameter_name = parameter[
                "parameter_name"
            ]

            parameter_value = parameter[
                "parameter_value"
            ]

            mapping = PLCParameterMappingManager.get_mapping(

                plc_name=plc_name,

                parameter_name=parameter_name

            )

            if not mapping:

                print(
                    f"Warning : No Mapping : "
                    f"{parameter_name}"
                )

                continue

            plc_index = mapping[
                "plc_array_index"
            ]

            plc_array[plc_index] = float(
                parameter_value
            )

            mapping_count += 1

        print(
            f"Mapped Parameters : "
            f"{mapping_count}"
        )

        return plc_array
    
    @staticmethod
    def download_recipe_to_plc_bulk(

        plc_name,

        recipe_code,

        version=1,

        array_size=500

    ):

        plc_info = PLCManager.get_plc(
            plc_name
        )

        if not plc_info:

            print(
                f"PLC Not Found : {plc_name}"
            )

            return False

        recipe_data_tag = plc_info[
            "recipe_data_tag"
        ]

        if not recipe_data_tag:

            print(
                f"Recipe Data Tag Not Configured : "
                f"{plc_name}"
            )

            return False

        plc_array = PLCRecipeManager.build_plc_array(

            plc_name=plc_name,

            recipe_code=recipe_code,

            version=version,

            array_size=array_size

        )

        plc = PLCConnection(
            plc_info["ip_address"]
        )

        if not plc.connect():

            return False

        try:

            success = plc.write_tag(

                recipe_data_tag,

                plc_array

            )

            if success:

                print(
                    f"Recipe Downloaded : "
                    f"{recipe_code}"
                )

                print(
                    f"Tag : "
                    f"{recipe_data_tag}"
                )

            return success

        finally:

            plc.disconnect()
            
    @staticmethod
    def download_recipe_to_plc_individual(

        plc_name,

        recipe_code,

        version=1

    ):

        plc_info = PLCManager.get_plc(
            plc_name
        )

        if not plc_info:

            print(
                f"PLC Not Found : {plc_name}"
            )

            return False

        recipe_data_tag = plc_info[
            "recipe_data_tag"
        ]

        recipe = RecipeManager.get_recipe(

            recipe_code=recipe_code,

            version=version

        )

        plc = PLCConnection(
            plc_info["ip_address"]
        )

        if not plc.connect():

            return False

        write_count = 0

        try:

            for parameter in recipe:

                parameter_name = parameter[
                    "parameter_name"
                ]

                parameter_value = parameter[
                    "parameter_value"
                ]

                mapping = PLCParameterMappingManager.get_mapping(

                    plc_name=plc_name,

                    parameter_name=parameter_name

                )

                if not mapping:

                    print(
                        f"Warning : No Mapping : "
                        f"{parameter_name}"
                    )

                    continue

                plc_index = mapping[
                    "plc_array_index"
                ]

                tag_name = (
                    f"{recipe_data_tag}"
                    f"[{plc_index}]"
                )

                plc.write_tag(

                    tag_name,

                    float(parameter_value)

                )

                write_count += 1

            print(
                f"Parameters Written : "
                f"{write_count}"
            )
            
            DownloadHistoryManager.log_download(

                plc_name=plc_name,

                recipe_code=recipe_code,

                recipe_version=version,

                download_status="SUCCESS",

                downloaded_by="system"

            )

            return True

        finally:

            plc.disconnect()