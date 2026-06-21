from plc.plc_connection import PLCConnection

from database.plc_manager_legacy import PLCManager

from database.plc_parameter_mapping_manager import (
    PLCParameterMappingManager
)


class PLCRecipeUpload:

    @staticmethod
    def read_recipe_array(

        plc_name,

        array_size=10

    ):

        plc_info = PLCManager.get_plc(
            plc_name
        )

        if not plc_info:

            print(
                f"PLC Not Found : {plc_name}"
            )

            return None

        recipe_tag = plc_info[
            "recipe_data_tag"
        ]

        plc = PLCConnection(
            plc_info["ip_address"]
        )

        if not plc.connect():

            return None

        try:

            return plc.read_tag(
                f"{recipe_tag}{{{array_size}}}"
            )

        finally:

            plc.disconnect()

    @staticmethod
    def convert_array_to_parameters(

        plc_name,

        recipe_array

    ):

        parameters = []

        for index, value in enumerate(
            recipe_array
        ):

            mapping = (
                PLCParameterMappingManager
                .get_mapping_by_index(

                    plc_name=plc_name,

                    plc_array_index=index

                )
            )

            if not mapping:

                continue

            parameters.append({

                "parameter_name":
                mapping[
                    "parameter_name"
                ],

                "parameter_value":
                value,

                "plc_array_index":
                index

            })

        return parameters