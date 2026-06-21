import sys
import os

ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if ROOT_DIR not in sys.path:

    sys.path.insert(
        0,
        ROOT_DIR
    )

from pycomm3 import (
    LogixDriver
)

from database.recipe_manager import (
    RecipeManager
)

from database.recipe_parameter_value_manager import (
    RecipeParameterValueManager
)

from database.recipe_validation_manager import (
    RecipeValidationManager
)

from database.download_history_manager import (
    DownloadHistoryManager
)

from database.plc_registry_manager import (
    PLCRegistryManager
)


class PLCDownloadManager:

    @staticmethod
    def download_recipe(

        recipe_id,

        plc_id,

        downloaded_by

    ):

        download_id = None

        try:

            recipe = (
                RecipeManager
                .get_recipe_by_id(
                    recipe_id
                )
            )

            if not recipe:

                return (

                    False,

                    "Recipe Not Found"

                )

            validation = (

                RecipeValidationManager
                .validate_recipe(
                    recipe_id
                )

            )

            if not validation["valid"]:

                return (

                    False,

                    "\n".join(
                        validation[
                            "errors"
                        ]
                    )

                )

            plc = (

                PLCRegistryManager
                .get_plc_by_id(
                    plc_id
                )

            )

            if not plc:

                return (

                    False,

                    "PLC Not Found"

                )

            plc_name = (
                plc["plc_name"]
            )

            ip_address = (
                plc["ip_address"]
            )

            download_id = (

                DownloadHistoryManager
                .create_download_record(

                    plc_name=
                    plc_name,

                    recipe_code=
                    recipe[
                        "recipe_code"
                    ],

                    recipe_version=
                    recipe[
                        "version"
                    ],

                    downloaded_by=
                    downloaded_by

                )

            )

            values = (

                RecipeParameterValueManager
                .get_recipe_values(
                    recipe_id
                )

            )

            recipe_array = [

                0.0
            ] * 500

            for row in values:

                plc_index = (
                    row[
                        "plc_array_index"
                    ]
                )

                value = (
                    row[
                        "parameter_value"
                    ]
                )

                if plc_index is None:

                    continue

                recipe_array[
                    plc_index
                ] = float(
                    value
                )

            with LogixDriver(
                ip_address
            ) as plc_conn:

                enable = plc_conn.read(
                    "CRS_Download_Enable"
                )

                if (

                    not enable

                    or

                    not enable.value

                ):

                    DownloadHistoryManager.fail_download_record(

                        download_id,

                        "Download Disabled"

                    )

                    return (

                        False,

                        "Download Disabled"

                    )

                result = plc_conn.write(

                    (

                        "CRS_Recipe_Code",

                        recipe[
                            "recipe_code"
                        ]

                    )

                )

                if not result:

                    DownloadHistoryManager.fail_download_record(

                        download_id,

                        "Recipe Code Write Failed"

                    )

                    return (

                        False,

                        "Recipe Code Write Failed"

                    )

                result = plc_conn.write(

                    (

                        "CRS_Recipe_Data{500}",

                        recipe_array

                    )

                )

                if not result:

                    DownloadHistoryManager.fail_download_record(

                        download_id,

                        "Recipe Data Write Failed"

                    )

                    return (

                        False,

                        "Recipe Data Write Failed"

                    )

                plc_conn.write(

                    (

                        "CRS_Download_Request",

                        True

                    )

                )

            DownloadHistoryManager.complete_download_record(

                download_id,

                "Download Successful"

            )

            return (

                True,

                "Download Successful"

            )

        except Exception as ex:

            if download_id:

                DownloadHistoryManager.fail_download_record(

                    download_id,

                    str(ex)

                )

            return (

                False,

                str(ex)

            )