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

from database.recipe_download_eligibility_manager import (
    RecipeDownloadEligibilityManager
)

from database.plc_download_preparation_manager import (
    PLCDownloadPreparationManager
)

from database.download_history_manager import (
    DownloadHistoryManager
)

class PLCDownloadManager:

    LIVE_WRITE_ENABLED = False

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

            eligibility = (

                RecipeDownloadEligibilityManager
                .check_eligibility(
                    recipe_id
                )

            )

            if not eligibility["eligible"]:

                return (

                    False,

                    "\n".join(
                        eligibility[
                            "errors"
                        ]
                    )

                )

            preparation = (

                PLCDownloadPreparationManager
                .dry_run(

                    recipe_id=recipe_id,

                    plc_id=plc_id

                )

            )

            if not preparation["ready"]:

                return (

                    False,

                    "\n".join(
                        preparation[
                            "errors"
                        ]
                    )

                )

            plc = preparation[
                "plc"
            ]

            write_plan = preparation[
                "write_plan"
            ]

            payload_size = write_plan.get(
                "payload_size",
                PLCDownloadPreparationManager.PAYLOAD_SIZE
            )

            if not PLCDownloadManager.LIVE_WRITE_ENABLED:

                return (

                    False,

                    "Real PLC write disabled. Dry run passed, "
                    "but live download is not enabled."

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
            ] * payload_size

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

                plc_index = int(
                    plc_index
                )

                if (
                    plc_index < 0
                    or
                    plc_index >= payload_size
                ):

                    continue

                recipe_array[
                    plc_index
                ] = float(
                    value
                )

            payload_validation = (
                PLCDownloadPreparationManager
                .validate_payload_values(

                    recipe_values=values,

                    payload_values=recipe_array

                )
            )

            if not payload_validation["valid"]:

                return (

                    False,

                    "Recipe payload validation failed before PLC write:\n"
                    + "\n".join(
                        payload_validation["errors"][:10]
                    )

                )

            with LogixDriver(
                ip_address
            ) as plc_conn:

                manual_mode = plc_conn.read(
                    write_plan[
                        "machine_in_manual_tag"
                    ]
                )

                manual_mode_error = getattr(
                    manual_mode,
                    "error",
                    None
                )

                manual_mode_value = getattr(
                    manual_mode,
                    "value",
                    None
                )

                if (
                    manual_mode is None
                    or
                    manual_mode_error
                    or
                    not PLCDownloadPreparationManager.is_true_value(
                        manual_mode_value
                    )
                ):

                    DownloadHistoryManager.fail_download_record(

                        download_id,

                        "Machine Not In Manual Mode"

                    )

                    return (

                        False,

                        "Machine is not in manual mode. "
                        "Recipe download blocked to prevent Auto mode write."

                    )

                enable = plc_conn.read(
                    write_plan[
                        "download_enable_tag"
                    ]
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

                        write_plan[
                            "recipe_code_tag"
                        ],

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

                        write_plan[
                            "recipe_data_write_tag"
                        ],

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

                readback = plc_conn.read(
                    write_plan[
                        "recipe_data_write_tag"
                    ]
                )

                readback_error = getattr(
                    readback,
                    "error",
                    None
                )

                readback_values = getattr(
                    readback,
                    "value",
                    None
                )

                if (
                    readback is None
                    or
                    readback_error
                ):

                    DownloadHistoryManager.fail_download_record(

                        download_id,

                        "Recipe Data Readback Failed"

                    )

                    return (

                        False,

                        "Recipe Data Readback Failed"

                    )

                plc_payload_validation = (
                    PLCDownloadPreparationManager
                    .validate_payload_values(

                        recipe_values=values,

                        payload_values=readback_values

                    )
                )

                if not plc_payload_validation["valid"]:

                    DownloadHistoryManager.fail_download_record(

                        download_id,

                        "PLC Payload Min Max Validation Failed"

                    )

                    return (

                        False,

                        "PLC actual recipe values failed min/max validation:\n"
                        + "\n".join(
                            plc_payload_validation["errors"][:10]
                        )

                    )

                plc_conn.write(

                    (

                        write_plan[
                            "download_request_tag"
                        ],

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
