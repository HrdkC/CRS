import time
from datetime import datetime

from pycomm3 import (
    LogixDriver
)

from database.audit_manager import (
    AuditManager
)

from database.download_history_manager import (
    DownloadHistoryManager
)

from database.plc_download_preparation_manager import (
    PLCDownloadPreparationManager
)

from database.plc_download_tag_readiness_manager import (
    PLCDownloadTagReadinessManager
)

from database.plc_connection_errors import (
    format_plc_connection_failure,
    is_plc_connection_error as _is_plc_connection_error,
)

from database.plc_operation_job_manager import (
    PLCOperationJobManager
)

from database.plc_tag_manager import (
    PLCTagManager
)

from database.recipe_manager import (
    RecipeManager
)

from database.recipe_parameter_value_manager import (
    RecipeParameterValueManager
)
from database.recipe_phase_control_manager import (
    RecipePhaseControlManager
)

from database.upload_history_manager import (
    UploadHistoryManager
)

from flask_app.security.role_guard import (
    role_can
)


class PLCBufferOperationManager:

    PAYLOAD_SIZE = None

    SOURCE_PURPOSE = "RECIPE_DATA"

    DESTINATION_PURPOSE = "TEST_RECIPE_DATA"

    RECIPE_CODE_PURPOSE = "RECIPE_CODE"

    PHASE_STRING_PURPOSE = "PHASE_CONTROL_STRING"

    PHASE_STOP_PURPOSE = "PHASE_STOP_STRING"

    PHASE_POSITION_PURPOSE = "PHASE_POSITION_STRING"

    CAP_STRIP_PHASE_STRING_PURPOSE = "CAP_STRIP_PHASE_CONTROL_STRING"

    BT_PHASE_STRING_PURPOSE = "BT_PHASE_CONTROL_STRING"

    MANUAL_PURPOSE = "MACHINE_IN_MANUAL"

    ENABLE_PURPOSE = "DOWNLOAD_ENABLE"

    REQUEST_PURPOSE = "DOWNLOAD_REQUEST"

    COMPLETE_PURPOSE = "DOWNLOAD_COMPLETE"

    ACK_PURPOSE = "DOWNLOAD_ACK"

    BUSY_PURPOSE = "DOWNLOAD_BUSY"

    ERROR_PURPOSE = "DOWNLOAD_ERROR"

    RESULT_PURPOSE = "DOWNLOAD_RESULT"

    OS_PURPOSE = "DOWNLOAD_OS"

    LAST_DOWNLOAD_TIME_PURPOSE = "LAST_DOWNLOAD_TIME"

    LAST_DOWNLOAD_USER_PURPOSE = "LAST_DOWNLOAD_USER"

    PHASE_PURPOSES = [
        PHASE_STRING_PURPOSE,
        PHASE_STOP_PURPOSE,
        PHASE_POSITION_PURPOSE,
    ]

    # Final P15 Second Stage recipe contract is selection-only.
    SECOND_STAGE_PHASE_PURPOSES = [
        CAP_STRIP_PHASE_STRING_PURPOSE,
        BT_PHASE_STRING_PURPOSE,
    ]

    DOWNLOAD_HANDSHAKE_TIMEOUT_SECONDS = 20

    LIVE_STATUS_PURPOSES = [
        {
            "group": "Interlocks",
            "purpose": "MACHINE_IN_MANUAL",
            "label": "Machine Manual Mode",
            "healthy_when": True,
            "bad_message": "Machine must be in manual mode before download."
        },
        {
            "group": "Interlocks",
            "purpose": "DOWNLOAD_ENABLE",
            "label": "Download Enable",
            "healthy_when": True,
            "bad_message": "Download enable must be TRUE before download."
        },
        {
            "group": "Handshake",
            "purpose": "DOWNLOAD_REQUEST",
            "label": "Download Request",
            "healthy_when": False,
            "bad_message": "Request should normally be FALSE before a new command."
        },
        {
            "group": "Handshake",
            "purpose": "DOWNLOAD_COMPLETE",
            "label": "Download Complete",
            "healthy_when": None,
            "bad_message": "Complete tag should be readable as BOOL."
        },
        {
            "group": "Handshake",
            "purpose": "DOWNLOAD_ACK",
            "label": "Download Ack",
            "healthy_when": False,
            "bad_message": "Ack should normally be FALSE before a new command."
        },
        {
            "group": "Handshake",
            "purpose": "DOWNLOAD_BUSY",
            "label": "Download Busy",
            "healthy_when": False,
            "bad_message": "Busy TRUE means PLC is already processing a command."
        },
        {
            "group": "Handshake",
            "purpose": "DOWNLOAD_ERROR",
            "label": "Download Error",
            "healthy_when": False,
            "bad_message": "Error TRUE means PLC download logic needs checking."
        },
        {
            "group": "Handshake",
            "purpose": "DOWNLOAD_RESULT",
            "label": "Download Result",
            "healthy_when": None,
            "bad_message": "Result tag should be readable."
        },
    ]

    OPERATIONS = {

        "recipe_restore": {
            "title": "Recipe Restore",
            "action": "RECIPE_RESTORE_TO_CRS_BUFFER"
        },

        "recipe_save": {
            "title": "Recipe Save",
            "action": "CRS_BUFFER_SAVE_TO_RECIPE"
        },

        "download_to_plc": {
            "title": "Download To PLC",
            "action": "CRS_BUFFER_DOWNLOAD_TO_PLC"
        },

        "upload_from_plc": {
            "title": "Upload From PLC",
            "action": "PLC_UPLOAD_TO_CRS_BUFFER"
        }

    }

    OPERATION_CAPABILITIES = {
        "recipe_restore": "recipe_download",
        "download_to_plc": "recipe_download",
        "recipe_save": "recipe_edit",
        "upload_from_plc": "recipe_edit"
    }

    @staticmethod
    def run_operation(

        recipe_id,

        plc_id,

        operation,

        username,

        user_role,

        status_job_id=None

    ):

        result = (
            PLCBufferOperationManager
            .make_result(
                operation,
                status_job_id=status_job_id
            )
        )

        PLCBufferOperationManager.publish_status(
            result=result,
            status_override="RUNNING"
        )

        if operation not in PLCBufferOperationManager.OPERATIONS:

            result["errors"].append(
                "Unknown PLC buffer operation."
            )

            PLCBufferOperationManager.finish(
                result,
                False,
                "Unknown operation"
            )

            return result

        required_capability = (
            PLCBufferOperationManager
            .OPERATION_CAPABILITIES
            .get(
                operation,
                "recipe_download"
            )
        )

        if not role_can(
            user_role,
            required_capability
        ):

            result["errors"].append(
                "Your role cannot run this PLC buffer operation."
            )

            PLCBufferOperationManager.finish(
                result,
                False,
                "PLC buffer operation blocked by role"
            )

            return result

        recipe = RecipeManager.get_recipe_by_id(
            recipe_id
        )

        if not recipe:

            result["errors"].append(
                "Recipe not found."
            )

            PLCBufferOperationManager.finish(
                result,
                False,
                "Recipe not found"
            )

            return result

        result["recipe"] = recipe
        result["payload_size"] = (
            PLCDownloadPreparationManager
            .get_payload_size_for_recipe(recipe)
        )

        if not result["payload_size"]:

            result["errors"].append(
                "Recipe data array size is not configured for this machine/stage."
            )

            PLCBufferOperationManager.finish(
                result,
                False,
                "Recipe data array size not configured"
            )

            return result

        plc = (
            PLCDownloadPreparationManager
            .get_plc_for_recipe(

                recipe=recipe,

                plc_id=plc_id

            )
        )

        if not plc:

            result["errors"].append(
                "Selected PLC is not active for this recipe stage."
            )

            PLCBufferOperationManager.finish(
                result,
                False,
                "PLC not active for recipe stage"
            )

            return result

        result["plc"] = plc

        blocked_reason = (
            PLCBufferOperationManager
            .check_recipe_usage_allowed(
                recipe
            )
        )

        if blocked_reason:

            result["errors"].append(
                blocked_reason
            )

            PLCBufferOperationManager.finish(
                result,
                False,
                "Recipe usage blocked"
            )

            return result

        try:

            if operation == "recipe_restore":

                result = (
                    PLCBufferOperationManager
                    .restore_recipe_to_crs_buffer(
                        result
                    )
                )

            elif operation == "recipe_save":

                result = (
                    PLCBufferOperationManager
                    .save_crs_buffer_to_recipe(

                        result=result,

                        username=username,

                        user_role=user_role

                    )
                )

            elif operation == "download_to_plc":

                result = (
                    PLCBufferOperationManager
                    .download_crs_buffer_to_plc(

                        result=result,

                        username=username

                    )
                )

            elif operation == "upload_from_plc":

                result = (
                    PLCBufferOperationManager
                    .upload_plc_buffer_to_crs_buffer(

                        result=result,

                        username=username,

                        user_role=user_role

                    )
                )

        except Exception as exc:

            raw_message = str(
                exc
            )

            message = (
                PLCBufferOperationManager
                .format_operation_exception(
                    raw_message,
                    result
                )
            )

            if message not in result["errors"]:

                result["errors"].append(
                    message
                )

            if (
                PLCBufferOperationManager
                .is_plc_connection_error(
                    raw_message
                )
            ):

                PLCBufferOperationManager.add_step(
                    result,
                    "PLC connection",
                    "FAILED",
                    message,
                    min(
                        max(
                            result.get(
                                "progress_percent",
                                0
                            ) + 5,
                            30
                        ),
                        45
                    )
                )

            if not result["success"]:

                PLCBufferOperationManager.finish(
                    result,
                    False,
                    message
                )

        finally:

            if (
                operation == "download_to_plc"
                and
                result.get(
                    "download_id"
                )
                and
                not result.get(
                    "success"
                )
            ):

                try:

                    DownloadHistoryManager.fail_download_record(

                        result["download_id"],

                        result["current_step"]

                    )

                except Exception as exc:

                    result["warnings"].append(
                        f"Download history failure record failed: {exc}"
                    )

            PLCBufferOperationManager.log_operation(

                result=result,

                username=username,

                user_role=user_role

            )

        return result

    @staticmethod
    def is_plc_connection_error(

        message

    ):

        return _is_plc_connection_error(message)

    @staticmethod
    def format_operation_exception(

        message,

        result

    ):

        if not PLCBufferOperationManager.is_plc_connection_error(
            message
        ):

            return message

        plc = result.get(
            "plc"
        ) or {}

        plc_name = plc.get(
            "plc_name",
            "selected PLC"
        )

        plc_ip = plc.get(
            "ip_address",
            "unknown IP"
        )

        return format_plc_connection_failure(
            plc={"plc_name": plc_name, "ip_address": plc_ip},
            detail=message,
            action="PLC buffer operation",
        )

    @staticmethod
    def get_operation_context(

        recipe_id,

        plc_id=None

    ):

        recipe = RecipeManager.get_recipe_by_id(
            recipe_id
        )

        context = {

            "recipe": recipe,

            "plc": None,

            "tags": {},

            "status": "NOT_READY",

            "issues": [],

            "payload_size": None

        }

        if not recipe:

            context["issues"].append(
                "Recipe not found."
            )

            return context

        context["payload_size"] = (
            PLCDownloadPreparationManager
            .get_payload_size_for_recipe(recipe)
        )

        available_plcs = (
            PLCDownloadPreparationManager
            .get_available_plcs(
                recipe_id
            )
        )

        selected_plc = None

        if plc_id:

            for plc in available_plcs:

                if str(
                    plc["id"]
                ) == str(
                    plc_id
                ):

                    selected_plc = plc

                    break

        elif available_plcs:

            selected_plc = available_plcs[0]

        context["plc"] = selected_plc

        if not selected_plc:

            context["issues"].append(
                "No active PLC selected for this recipe stage."
            )

        configured_phase_purposes = (
            PLCBufferOperationManager.get_phase_purposes_for_recipe(recipe)
        )

        for purpose in [
            PLCBufferOperationManager.SOURCE_PURPOSE,
            PLCBufferOperationManager.DESTINATION_PURPOSE,
            PLCBufferOperationManager.RECIPE_CODE_PURPOSE,
            PLCBufferOperationManager.MANUAL_PURPOSE,
            PLCBufferOperationManager.ENABLE_PURPOSE,
            PLCBufferOperationManager.REQUEST_PURPOSE,
            PLCBufferOperationManager.COMPLETE_PURPOSE,
            PLCBufferOperationManager.ACK_PURPOSE,
            PLCBufferOperationManager.BUSY_PURPOSE,
            PLCBufferOperationManager.ERROR_PURPOSE,
            PLCBufferOperationManager.RESULT_PURPOSE,
            PLCBufferOperationManager.OS_PURPOSE,
            PLCBufferOperationManager.LAST_DOWNLOAD_TIME_PURPOSE,
            PLCBufferOperationManager.LAST_DOWNLOAD_USER_PURPOSE
        ] + configured_phase_purposes:

            context["tags"][purpose] = (
                PLCBufferOperationManager
                .get_tag_for_purpose(
                    recipe,
                    purpose
                )
            )

        for purpose in [
            PLCBufferOperationManager.SOURCE_PURPOSE,
            PLCBufferOperationManager.DESTINATION_PURPOSE
        ]:

            tag = context["tags"].get(
                purpose
            )

            if not PLCBufferOperationManager.valid_real_array_tag(
                tag,
                payload_size=context.get("payload_size")
            ):

                expected_array = (
                    f"REAL[{context.get('payload_size')}]"
                    if context.get("payload_size")
                    else
                    "REAL array with configured stage payload size"
                )

                context["issues"].append(
                    f"{purpose} must be configured as {expected_array}."
                )

        for purpose in configured_phase_purposes:

            tag = context["tags"].get(
                purpose
            )

            if not PLCBufferOperationManager.valid_string_array_tag(
                tag
            ):

                context["issues"].append(
                    f"{purpose} must be configured as a STRING array."
                )

        for purpose in [
            PLCBufferOperationManager.MANUAL_PURPOSE,
            PLCBufferOperationManager.ENABLE_PURPOSE,
            PLCBufferOperationManager.REQUEST_PURPOSE,
            PLCBufferOperationManager.COMPLETE_PURPOSE
        ]:

            tag = context["tags"].get(
                purpose
            )

            if not PLCBufferOperationManager.valid_bool_tag(
                tag
            ):

                context["issues"].append(
                    f"{purpose} must be configured as BOOL."
                )

        if context["issues"]:

            context["status"] = "NOT_READY"

        else:

            context["status"] = "READY"

        return context

    @staticmethod
    def restore_recipe_to_crs_buffer(

        result

    ):

        recipe = result["recipe"]

        values = RecipeParameterValueManager.get_recipe_values(
            recipe["id"]
        )

        source_tag = (
            PLCBufferOperationManager
            .require_array_tag(

                recipe,

                PLCBufferOperationManager.SOURCE_PURPOSE,

                "CRS recipe buffer"

            )
        )

        recipe_code_tag = (
            PLCBufferOperationManager
            .get_tag_for_purpose(
                recipe,
                PLCBufferOperationManager.RECIPE_CODE_PURPOSE
            )
        )

        payload = (
            PLCBufferOperationManager
            .build_database_payload(
                values,
                payload_size=result.get("payload_size")
            )
        )

        PLCBufferOperationManager.add_step(
            result,
            "Recipe selected",
            "OK",
            "Database recipe loaded.",
            10
        )

        PLCBufferOperationManager.validate_payload_or_block(

            result=result,

            recipe_values=values,

            payload=payload,

            label="Database min/max validation",

            percent=30

        )

        with LogixDriver(
            result["plc"]["ip_address"]
        ) as plc_conn:

            PLCBufferOperationManager.add_step(
                result,
                "PLC connected",
                "OK",
                result["plc"]["ip_address"],
                45
            )

            if recipe_code_tag:

                PLCBufferOperationManager.write_or_block(

                    plc_conn=plc_conn,

                    tag_name=recipe_code_tag["tag_name"],

                    value=recipe["recipe_code"],

                    result=result,

                    label="Write CRS recipe code",

                    percent=55

                )

            else:

                result["warnings"].append(
                    "RECIPE_CODE tag is not configured. Recipe data was restored only."
                )

            PLCBufferOperationManager.write_or_block(

                plc_conn=plc_conn,

                tag_name=source_tag["tag_name"],

                value=payload,

                result=result,

                label="Write database recipe to CRS buffer",

                percent=70

            )

            PLCBufferOperationManager.write_phase_control_arrays(
                plc_conn=plc_conn,
                recipe=recipe,
                result=result,
                write_percent=78,
                verify_percent=84
            )

            readback = (
                PLCBufferOperationManager
                .read_array_or_block(

                    plc_conn=plc_conn,

                    tag_name=source_tag["tag_name"],

                    result=result,

                    label="Read CRS buffer back",

                    percent=88

                ,

                    payload_size=result.get("payload_size")

                )
            )

        PLCBufferOperationManager.validate_payload_or_block(

            result=result,

            recipe_values=values,

            payload=readback,

            label="CRS buffer min/max validation",

            percent=92

        )

        compare = PLCBufferOperationManager.compare_payloads(
            payload,
            readback
        )

        result["payload_compare"] = compare

        if not compare["matched"]:

            PLCBufferOperationManager.fail_with_step(
                result,
                "CRS buffer compare",
                "CRS buffer readback does not match database recipe.",
                96
            )

        PLCBufferOperationManager.add_step(
            result,
            "CRS buffer verified",
            "OK",
            "Database recipe restored to CRS_Recipe_Data.",
            100
        )

        PLCBufferOperationManager.finish(
            result,
            True,
            "Recipe restored to CRS buffer"
        )

        return result

    @staticmethod
    def save_crs_buffer_to_recipe(

        result,

        username,

        user_role

    ):

        recipe = result["recipe"]

        values = RecipeParameterValueManager.get_recipe_values(
            recipe["id"]
        )

        source_tag = (
            PLCBufferOperationManager
            .require_array_tag(

                recipe,

                PLCBufferOperationManager.SOURCE_PURPOSE,

                "CRS recipe buffer"

            )
        )

        PLCBufferOperationManager.add_step(
            result,
            "Recipe selected",
            "OK",
            "Database target ready.",
            10
        )

        with LogixDriver(
            result["plc"]["ip_address"]
        ) as plc_conn:

            PLCBufferOperationManager.add_step(
                result,
                "PLC connected",
                "OK",
                result["plc"]["ip_address"],
                25
            )

            source_payload = (
                PLCBufferOperationManager
                .read_array_or_block(

                    plc_conn=plc_conn,

                    tag_name=source_tag["tag_name"],

                    result=result,

                    label="Read CRS buffer",

                    percent=45

                ,

                    payload_size=result.get("payload_size")

                )
            )

        PLCBufferOperationManager.validate_payload_or_block(

            result=result,

            recipe_values=values,

            payload=source_payload,

            label="CRS buffer min/max validation",

            percent=65

        )

        changed_count = (
            PLCBufferOperationManager
            .update_recipe_values_from_payload(

                recipe_values=values,

                payload=source_payload,

                username=username,

                user_role=user_role,

                change_source="CRS_BUFFER_SAVE_TO_RECIPE",

                change_reason="Recipe Save from CRS_Recipe_Data buffer",

                payload_size=result.get("payload_size")

            )
        )

        result["metrics"]["changed_parameters"] = changed_count

        PLCBufferOperationManager.add_step(
            result,
            "Database updated",
            "OK",
            f"{changed_count} changed parameter values saved.",
            90
        )

        fresh_values = RecipeParameterValueManager.get_recipe_values(
            recipe["id"]
        )

        database_compare = (
            PLCBufferOperationManager
            .compare_recipe_values_to_payload(
                recipe_values=fresh_values,
                payload=source_payload,
                payload_size=result.get("payload_size")
            )
        )

        result["payload_compare"] = database_compare

        result["metrics"]["verified_parameters"] = (
            database_compare["checked_parameters"]
        )

        if not database_compare["matched"]:

            PLCBufferOperationManager.fail_with_step(
                result,
                "Database readback verification",
                (
                    "Database values do not match CRS_Recipe_Data after "
                    "Recipe Save."
                ),
                96
            )

        PLCBufferOperationManager.add_step(
            result,
            "Database readback verified",
            "OK",
            (
                f"{database_compare['checked_parameters']} database "
                "parameters match CRS_Recipe_Data."
            ),
            96
        )

        PLCBufferOperationManager.add_step(
            result,
            "Save complete",
            "OK",
            "CRS buffer values saved to selected database recipe.",
            100
        )

        PLCBufferOperationManager.finish(
            result,
            True,
            "CRS buffer saved to database"
        )

        return result

    @staticmethod
    def download_crs_buffer_to_plc(

        result,

        username

    ):

        recipe = result["recipe"]

        download_id = None

        try:

            download_id = (
                DownloadHistoryManager
                .create_download_record(

                    plc_name=result["plc"]["plc_name"],

                    recipe_code=recipe["recipe_code"],

                    recipe_version=recipe["version"],

                    downloaded_by=username

                )
            )

            result["download_id"] = download_id

        except Exception as exc:

            result["warnings"].append(
                f"Download history start record failed: {exc}"
            )

        values = RecipeParameterValueManager.get_recipe_values(
            recipe["id"]
        )

        database_payload = (
            PLCBufferOperationManager
            .build_database_payload(
                values,
                payload_size=result.get("payload_size")
            )
        )

        source_tag = (
            PLCBufferOperationManager
            .require_array_tag(

                recipe,

                PLCBufferOperationManager.SOURCE_PURPOSE,

                "CRS recipe buffer"

            )
        )

        destination_tag = (
            PLCBufferOperationManager
            .require_array_tag(

                recipe,

                PLCBufferOperationManager.DESTINATION_PURPOSE,

                "PLC recipe destination buffer"

            )
        )

        manual_tag = (
            PLCBufferOperationManager
            .require_bool_tag(

                recipe,

                PLCBufferOperationManager.MANUAL_PURPOSE,

                "Machine manual mode"

            )
        )

        enable_tag = (
            PLCBufferOperationManager
            .require_bool_tag(

                recipe,

                PLCBufferOperationManager.ENABLE_PURPOSE,

                "Recipe download enable"

            )
        )

        PLCBufferOperationManager.add_step(
            result,
            "Recipe selected",
            "OK",
            "Download request received.",
            8
        )

        PLCBufferOperationManager.validate_payload_or_block(

            result=result,

            recipe_values=values,

            payload=database_payload,

            label="Database min/max validation",

            percent=20

        )

        with LogixDriver(
            result["plc"]["ip_address"]
        ) as plc_conn:

            PLCBufferOperationManager.add_step(
                result,
                "PLC connected",
                "OK",
                result["plc"]["ip_address"],
                35
            )

            source_payload = (
                PLCBufferOperationManager
                .read_array_or_block(

                    plc_conn=plc_conn,

                    tag_name=source_tag["tag_name"],

                    result=result,

                    label="Read CRS buffer",

                    percent=48

                ,

                    payload_size=result.get("payload_size")

                )
            )

            PLCBufferOperationManager.validate_payload_or_block(

                result=result,

                recipe_values=values,

                payload=source_payload,

                label="CRS buffer min/max validation",

                percent=58

            )

            compare = PLCBufferOperationManager.compare_payloads(
                database_payload,
                source_payload
            )

            result["payload_compare"] = compare

            if not compare["matched"]:

                PLCBufferOperationManager.fail_with_step(
                    result,
                    "CRS buffer database compare",
                    (
                        "CRS buffer is different from the selected database "
                        "recipe. Press Recipe Save before Download To PLC."
                    ),
                    62
                )

            PLCBufferOperationManager.add_step(
                result,
                "CRS buffer matches database",
                "OK",
                "Selected recipe and CRS buffer are aligned.",
                62
            )

            PLCBufferOperationManager.read_true_or_block(

                plc_conn=plc_conn,

                tag_name=manual_tag["tag_name"],

                result=result,

                label="Machine manual mode",

                percent=70

            )

            PLCBufferOperationManager.read_true_or_block(

                plc_conn=plc_conn,

                tag_name=enable_tag["tag_name"],

                result=result,

                label="Recipe download enable",

                percent=78

            )

            PLCBufferOperationManager.write_or_block(

                plc_conn=plc_conn,

                tag_name=destination_tag["tag_name"],

                value=source_payload,

                result=result,

                label="Write CRS buffer to PLC destination",

                percent=88

            )

            PLCBufferOperationManager.write_phase_control_arrays(
                plc_conn=plc_conn,
                recipe=recipe,
                result=result,
                write_percent=91,
                verify_percent=94
            )

            destination_readback = (
                PLCBufferOperationManager
                .read_array_or_block(

                    plc_conn=plc_conn,

                    tag_name=destination_tag["tag_name"],

                    result=result,

                    label="Read PLC destination back",

                    percent=96

                ,

                    payload_size=result.get("payload_size")

                )
            )

        destination_compare = PLCBufferOperationManager.compare_payloads(
            source_payload,
            destination_readback
        )

        result["destination_compare"] = destination_compare

        if not destination_compare["matched"]:

            PLCBufferOperationManager.fail_with_step(
                result,
                "PLC destination compare",
                "PLC destination readback does not match CRS buffer.",
                98
            )

        with LogixDriver(
            result["plc"]["ip_address"]
        ) as plc_conn:

            PLCBufferOperationManager.perform_download_handshake(
                plc_conn=plc_conn,
                result=result,
                recipe=recipe,
                username=username
            )

        PLCBufferOperationManager.add_step(
            result,
            "Download verified",
            "OK",
            "PLC destination buffer and download handshake completed.",
            100
        )

        PLCBufferOperationManager.finish(
            result,
            True,
            "Download To PLC completed"
        )

        if download_id:

            try:

                DownloadHistoryManager.complete_download_record(
                    download_id,
                    "CRS buffer downloaded to PLC destination buffer and handshake completed"
                )

            except Exception as exc:

                result["warnings"].append(
                    f"Download history completion record failed: {exc}"
                )

        return result

    @staticmethod
    def upload_plc_buffer_to_crs_buffer(

        result,

        username,

        user_role

    ):

        recipe = result["recipe"]

        values = RecipeParameterValueManager.get_recipe_values(
            recipe["id"]
        )

        source_tag = (
            PLCBufferOperationManager
            .require_array_tag(

                recipe,

                PLCBufferOperationManager.DESTINATION_PURPOSE,

                "PLC recipe source buffer"

            )
        )

        destination_tag = (
            PLCBufferOperationManager
            .require_array_tag(

                recipe,

                PLCBufferOperationManager.SOURCE_PURPOSE,

                "CRS recipe buffer"

            )
        )

        PLCBufferOperationManager.add_step(
            result,
            "Upload requested",
            "OK",
            "PLC source buffer selected.",
            10
        )

        with LogixDriver(
            result["plc"]["ip_address"]
        ) as plc_conn:

            PLCBufferOperationManager.add_step(
                result,
                "PLC connected",
                "OK",
                result["plc"]["ip_address"],
                25
            )

            source_payload = (
                PLCBufferOperationManager
                .read_array_or_block(

                    plc_conn=plc_conn,

                    tag_name=source_tag["tag_name"],

                    result=result,

                    label="Read PLC source buffer",

                    percent=45

                ,

                    payload_size=result.get("payload_size")

                )
            )

            PLCBufferOperationManager.validate_payload_or_block(

                result=result,

                recipe_values=values,

                payload=source_payload,

                label="PLC source buffer min/max validation",

                percent=62

            )

            database_compare = (
                PLCBufferOperationManager
                .compare_recipe_values_to_payload(

                    recipe_values=values,

                    payload=source_payload,

                    payload_size=result.get("payload_size")

                )
            )

            result["payload_compare"] = database_compare

            result["metrics"]["upload_candidate_changes"] = (
                database_compare["mismatch_count"]
            )

            result["metrics"]["validated_parameters"] = (
                database_compare["checked_parameters"]
            )

            PLCBufferOperationManager.add_step(
                result,
                "PLC upload compared to database",
                "OK",
                (
                    f"{database_compare['mismatch_count']} candidate "
                    "parameter change(s) found. Use Recipe Save to "
                    "write these PLC values to the recipe database with audit."
                ),
                72
            )

            PLCBufferOperationManager.write_or_block(

                plc_conn=plc_conn,

                tag_name=destination_tag["tag_name"],

                value=source_payload,

                result=result,

                label="Write PLC source to CRS buffer",

                percent=82

            )

            destination_readback = (
                PLCBufferOperationManager
                .read_array_or_block(

                    plc_conn=plc_conn,

                    tag_name=destination_tag["tag_name"],

                    result=result,

                    label="Read CRS buffer back",

                    percent=95

                ,

                    payload_size=result.get("payload_size")

                )
            )

        compare = PLCBufferOperationManager.compare_payloads(
            source_payload,
            destination_readback
        )

        result["destination_compare"] = compare

        if not compare["matched"]:

            PLCBufferOperationManager.fail_with_step(
                result,
                "CRS buffer compare",
                "CRS buffer readback does not match PLC source buffer.",
                98
            )

        PLCBufferOperationManager.add_step(
            result,
            "Upload verified",
            "OK",
            "PLC source buffer copied to CRS_Recipe_Data.",
            100
        )

        PLCBufferOperationManager.finish(
            result,
            True,
            "Upload From PLC completed"
        )

        try:

            upload_candidate_changes = result["metrics"].get(
                "upload_candidate_changes",
                0
            )

            validated_parameters = result["metrics"].get(
                "validated_parameters",
                0
            )

            UploadHistoryManager.log_upload(

                plc_name=result["plc"]["plc_name"],

                recipe_code=recipe["recipe_code"],

                recipe_version=recipe["version"],

                status="SUCCESS",

                uploaded_by=username,

                remarks=(
                    "PLC destination buffer copied to CRS buffer. "
                    f"Candidate recipe changes: {upload_candidate_changes}. "
                    "Use Recipe Save to commit database values with audit."
                ),

                user_role=user_role,

                plc_id=result["plc"].get("id"),

                source_tag=source_tag["tag_name"],

                destination_tag=destination_tag["tag_name"],

                candidate_change_count=upload_candidate_changes,

                validated_parameters=validated_parameters,

                payload_mismatch_count=result["payload_compare"].get(
                    "mismatch_count",
                    0
                )

            )

            AuditManager.log_event(

                username=username,

                role=user_role,

                action="PLC_UPLOAD_FROM_PLC",

                change_source="PLC_UPLOAD_TO_CRS_BUFFER",

                plc_name=result["plc"]["plc_name"],

                recipe_code=recipe["recipe_code"],

                recipe_version=recipe["version"],

                old_value="PLC destination buffer",

                new_value="CRS_Recipe_Data",

                reason=(
                    "PLC buffer uploaded to CRS buffer. "
                    "Recipe Save is required for database update and "
                    "parameter-level audit."
                )

            )

        except Exception as exc:

            result["warnings"].append(
                f"Upload history/audit record failed: {exc}"
            )

        return result


    @staticmethod
    def perform_download_handshake(

        plc_conn,

        result,

        recipe,

        username

    ):

        request_tag = PLCBufferOperationManager.require_bool_tag(

            recipe,

            PLCBufferOperationManager.REQUEST_PURPOSE,

            "Download request"

        )

        complete_tag = PLCBufferOperationManager.require_bool_tag(

            recipe,

            PLCBufferOperationManager.COMPLETE_PURPOSE,

            "Download complete"

        )

        ack_tag = PLCBufferOperationManager.get_optional_tag(

            recipe,

            PLCBufferOperationManager.ACK_PURPOSE

        )

        busy_tag = PLCBufferOperationManager.get_optional_tag(

            recipe,

            PLCBufferOperationManager.BUSY_PURPOSE

        )

        error_tag = PLCBufferOperationManager.get_optional_tag(

            recipe,

            PLCBufferOperationManager.ERROR_PURPOSE

        )

        result_tag = PLCBufferOperationManager.get_optional_tag(

            recipe,

            PLCBufferOperationManager.RESULT_PURPOSE

        )

        PLCBufferOperationManager.write_or_block(

            plc_conn=plc_conn,

            tag_name=request_tag["tag_name"],

            value=False,

            result=result,

            label="Reset download request",

            percent=96

        )

        if ack_tag:

            PLCBufferOperationManager.write_or_block(

                plc_conn=plc_conn,

                tag_name=ack_tag["tag_name"],

                value=False,

                result=result,

                label="Reset download acknowledge",

                percent=96

            )

        PLCBufferOperationManager.write_optional_download_metadata(

            plc_conn=plc_conn,

            recipe=recipe,

            username=username,

            result=result

        )

        PLCBufferOperationManager.write_or_block(

            plc_conn=plc_conn,

            tag_name=request_tag["tag_name"],

            value=True,

            result=result,

            label="Set download request",

            percent=97

        )

        handshake = PLCBufferOperationManager.wait_for_download_complete(

            plc_conn=plc_conn,

            complete_tag=complete_tag,

            error_tag=error_tag,

            busy_tag=busy_tag,

            result_tag=result_tag,

            result=result

        )

        result["metrics"]["handshake_wait_seconds"] = handshake[
            "wait_seconds"
        ]

        if handshake.get(
            "result_value"
        ) is not None:

            result["metrics"]["download_result_code"] = handshake[
                "result_value"
            ]

        if not handshake["success"]:

            PLCBufferOperationManager.write_or_block(

                plc_conn=plc_conn,

                tag_name=request_tag["tag_name"],

                value=False,

                result=result,

                label="Reset download request after failure",

                percent=99

            )

            PLCBufferOperationManager.fail_with_step(

                result,

                "Download handshake",

                handshake["message"],

                99

            )

        PLCBufferOperationManager.add_step(

            result,

            "Download complete confirmed",

            "OK",

            handshake["message"],

            99

        )

        PLCBufferOperationManager.write_or_block(

            plc_conn=plc_conn,

            tag_name=request_tag["tag_name"],

            value=False,

            result=result,

            label="Reset download request",

            percent=99

        )

        if ack_tag:

            PLCBufferOperationManager.write_or_block(

                plc_conn=plc_conn,

                tag_name=ack_tag["tag_name"],

                value=True,

                result=result,

                label="Pulse download acknowledge",

                percent=99

            )

            time.sleep(
                0.3
            )

            PLCBufferOperationManager.write_or_block(

                plc_conn=plc_conn,

                tag_name=ack_tag["tag_name"],

                value=False,

                result=result,

                label="Reset download acknowledge",

                percent=99

            )

    @staticmethod
    def wait_for_download_complete(

        plc_conn,

        complete_tag,

        error_tag,

        busy_tag,

        result_tag,

        result

    ):

        timeout_seconds = (
            PLCBufferOperationManager.DOWNLOAD_HANDSHAKE_TIMEOUT_SECONDS
        )

        start_time = time.monotonic()

        last_busy_value = None

        last_result_value = None

        while True:

            elapsed = time.monotonic() - start_time

            complete_value = PLCBufferOperationManager.read_bool_value(

                plc_conn,

                complete_tag["tag_name"]

            )

            if error_tag:

                error_value = PLCBufferOperationManager.read_bool_value(

                    plc_conn,

                    error_tag["tag_name"]

                )

                if error_value:

                    if result_tag:

                        last_result_value = (
                            PLCBufferOperationManager.read_scalar_value(
                                plc_conn,
                                result_tag["tag_name"]
                            )
                        )

                    return {
                        "success": False,
                        "message": (
                            "PLC download error bit became TRUE. "
                            f"Result code: {last_result_value}"
                        ),
                        "wait_seconds": round(
                            elapsed,
                            2
                        ),
                        "result_value": last_result_value
                    }

            if complete_value:

                if result_tag:

                    last_result_value = PLCBufferOperationManager.read_scalar_value(
                        plc_conn,
                        result_tag["tag_name"]
                    )

                return {
                    "success": True,
                    "message": (
                        "PLC download complete bit confirmed TRUE. "
                        f"Result code: {last_result_value}"
                    ),
                    "wait_seconds": round(
                        elapsed,
                        2
                    ),
                    "result_value": last_result_value
                }

            if busy_tag:

                last_busy_value = PLCBufferOperationManager.read_bool_value(

                    plc_conn,

                    busy_tag["tag_name"]

                )

            if elapsed >= timeout_seconds:

                return {
                    "success": False,
                    "message": (
                        "PLC download handshake timeout. "
                        f"Complete did not become TRUE within {timeout_seconds} seconds. "
                        f"Busy: {last_busy_value}."
                    ),
                    "wait_seconds": round(
                        elapsed,
                        2
                    ),
                    "result_value": last_result_value
                }

            time.sleep(
                0.25
            )

    @staticmethod
    def write_optional_download_metadata(

        plc_conn,

        recipe,

        username,

        result

    ):

        time_tag = PLCBufferOperationManager.get_optional_tag(

            recipe,

            PLCBufferOperationManager.LAST_DOWNLOAD_TIME_PURPOSE

        )

        user_tag = PLCBufferOperationManager.get_optional_tag(

            recipe,

            PLCBufferOperationManager.LAST_DOWNLOAD_USER_PURPOSE

        )

        if time_tag:

            PLCBufferOperationManager.write_or_block(

                plc_conn=plc_conn,

                tag_name=time_tag["tag_name"],

                value=datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

                result=result,

                label="Write last download time",

                percent=96

            )

        if user_tag:

            PLCBufferOperationManager.write_or_block(

                plc_conn=plc_conn,

                tag_name=user_tag["tag_name"],

                value=str(
                    username
                    or
                    "system"
                )[:80],

                result=result,

                label="Write last download user",

                percent=96

            )

    @staticmethod
    def get_optional_tag(

        recipe,

        purpose

    ):

        return PLCBufferOperationManager.get_tag_for_purpose(
            recipe,
            purpose
        )

    @staticmethod
    def get_tag_for_purpose(

        recipe,

        purpose

    ):

        if not recipe or not purpose:

            return None

        tag = PLCTagManager.get_tag_by_purpose(

            machine_id=recipe["machine_id"],

            stage_id=recipe["stage_id"],

            tag_purpose=purpose

        )

        if tag:

            return tag

        try:

            stage_tags = (
                PLCDownloadTagReadinessManager
                .get_tags_for_stage(
                    machine_id=recipe["machine_id"],
                    stage_id=recipe["stage_id"]
                )
            )

            return (
                PLCDownloadTagReadinessManager
                .find_tag_for_purpose(
                    stage_tags,
                    purpose
                )
            )

        except Exception:

            return None

    @staticmethod
    def is_second_stage_recipe(recipe):
        stage_type = str((recipe or {}).get("stage_type") or "").strip().upper()
        if stage_type:
            return stage_type == "SECOND_STAGE"

        try:
            conn = get_connection()
            row = conn.execute(
                """
                SELECT stage_type
                FROM machine_stages
                WHERE id = ?
                """,
                (recipe["stage_id"],),
            ).fetchone()
            conn.close()
            return str(row["stage_type"] if row else "").strip().upper() == "SECOND_STAGE"
        except Exception:
            return False

    @staticmethod
    def get_phase_purposes_for_recipe(recipe):
        if PLCBufferOperationManager.is_second_stage_recipe(recipe):
            return list(PLCBufferOperationManager.SECOND_STAGE_PHASE_PURPOSES)
        return [
            PLCBufferOperationManager.PHASE_STRING_PURPOSE,
            PLCBufferOperationManager.PHASE_STOP_PURPOSE,
            PLCBufferOperationManager.PHASE_POSITION_PURPOSE
        ]

    @staticmethod
    def get_live_tag_status(

        recipe_id,

        plc_id=None

    ):

        result = {
            "connected": False,
            "status": "NOT_CHECKED",
            "summary": "Live PLC status was not checked.",
            "groups": [],
            "issues": []
        }

        recipe = RecipeManager.get_recipe_by_id(
            recipe_id
        )

        if not recipe:

            result["status"] = "BLOCKED"
            result["summary"] = "Recipe not found."
            result["issues"].append(
                "Recipe not found."
            )

            return result

        plc = PLCDownloadPreparationManager.get_plc_for_recipe(
            recipe,
            plc_id
        )

        if not plc:

            result["status"] = "BLOCKED"
            result["summary"] = "No active PLC selected."
            result["issues"].append(
                "No active PLC selected for live interlock check."
            )

            return result

        groups = {}

        for rule in PLCBufferOperationManager.LIVE_STATUS_PURPOSES:

            groups.setdefault(
                rule["group"],
                []
            ).append({
                "purpose": rule["purpose"],
                "label": rule["label"],
                "tag": PLCBufferOperationManager.get_tag_for_purpose(
                    recipe,
                    rule["purpose"]
                ),
                "value": None,
                "expected_text": (
                    "Readable"
                    if rule.get("healthy_when") is None
                    else (
                        "TRUE"
                        if rule.get("healthy_when") is True
                        else
                        "FALSE"
                    )
                ),
                "status": "missing",
                "status_text": "Missing",
                "message": "Tag is not mapped.",
            })

        try:

            with LogixDriver(
                plc["ip_address"]
            ) as plc_conn:

                result["connected"] = True

                for rule in PLCBufferOperationManager.LIVE_STATUS_PURPOSES:

                    item = None

                    for candidate in groups[rule["group"]]:

                        if candidate["purpose"] == rule["purpose"]:

                            item = candidate
                            break

                    if not item or not item.get("tag"):

                        result["issues"].append(
                            f"{rule['purpose']} is not mapped."
                        )

                        continue

                    tag = item["tag"]

                    try:

                        read_result = plc_conn.read(
                            tag["tag_name"]
                        )

                        read_error = getattr(
                            read_result,
                            "error",
                            None
                        )

                        if read_result is None or read_error:

                            item["status"] = "bad"
                            item["status_text"] = "Read Error"
                            item["message"] = str(
                                read_error
                                or
                                "No read result"
                            )
                            result["issues"].append(
                                f"{tag['tag_name']} read failed: {item['message']}"
                            )
                            continue

                        value = getattr(
                            read_result,
                            "value",
                            None
                        )

                        item["value"] = value

                        expected = rule.get(
                            "healthy_when"
                        )

                        if expected is None:

                            item["status"] = "ok"
                            item["status_text"] = "Readable"
                            item["message"] = "Tag is readable from PLC."

                        else:

                            bool_value = (
                                PLCDownloadPreparationManager
                                .is_true_value(
                                    value
                                )
                            )

                            if bool_value == expected:

                                item["status"] = "ok"
                                item["status_text"] = "Healthy"
                                item["message"] = "Good to go."

                            else:

                                item["status"] = "bad"
                                item["status_text"] = "Check"
                                item["message"] = rule.get(
                                    "bad_message",
                                    "PLC state is not healthy."
                                )
                                result["issues"].append(
                                    f"{rule['label']}: {item['message']} Actual value: {value}"
                                )

                    except Exception as exc:

                        item["status"] = "bad"
                        item["status_text"] = "Read Error"
                        item["message"] = str(
                            exc
                        )
                        result["issues"].append(
                            f"{rule['label']} read failed: {exc}"
                        )

        except Exception as exc:

            result["status"] = "BLOCKED"
            result["summary"] = format_plc_connection_failure(
                plc=plc,
                detail=exc,
                action="Live PLC status check",
            )
            result["issues"].append(
                result["summary"]
            )

            # Keep mapped tags visible even when live read fails.
            result["groups"] = [
                {
                    "title": group_name,
                    "items": items
                }
                for group_name, items in groups.items()
            ]

            return result

        bad_count = sum(
            1
            for items in groups.values()
            for item in items
            if item.get("status") in ["bad", "missing"]
        )

        result["groups"] = [
            {
                "title": group_name,
                "items": items
            }
            for group_name, items in groups.items()
        ]

        if bad_count:

            result["status"] = "BLOCKED"
            result["summary"] = f"{bad_count} live PLC interlock/handshake item(s) need checking."

        else:

            result["status"] = "READY"
            result["summary"] = "All readable live PLC interlocks are healthy."

        return result

    @staticmethod
    def read_bool_value(

        plc_conn,

        tag_name

    ):

        read_result = plc_conn.read(
            tag_name
        )

        error = getattr(
            read_result,
            "error",
            None
        )

        if (
            read_result is None
            or
            error
        ):

            raise Exception(
                f"{tag_name} read failed: {error}"
            )

        return PLCDownloadPreparationManager.is_true_value(
            getattr(
                read_result,
                "value",
                None
            )
        )

    @staticmethod
    def read_scalar_value(

        plc_conn,

        tag_name

    ):

        read_result = plc_conn.read(
            tag_name
        )

        error = getattr(
            read_result,
            "error",
            None
        )

        if (
            read_result is None
            or
            error
        ):

            return None

        return getattr(
            read_result,
            "value",
            None
        )

    @staticmethod
    def make_result(

        operation,

        status_job_id=None

    ):

        operation_info = PLCBufferOperationManager.OPERATIONS.get(
            operation,
            {}
        )

        return {

            "operation": operation,

            "title": operation_info.get(
                "title",
                "PLC Buffer Operation"
            ),

            "success": False,

            "status": "BLOCKED",

            "progress_percent": 0,

            "current_step": "Waiting",

            "recipe": None,

            "plc": None,

            "steps": [],

            "errors": [],

            "warnings": [],

            "metrics": {},

            "payload_compare": {
                "checked": False,
                "matched": False,
                "mismatch_count": 0,
                "mismatches": []
            },

            "destination_compare": {
                "checked": False,
                "matched": False,
                "mismatch_count": 0,
                "mismatches": []
            },

            "download_id": None,

            "status_job_id": status_job_id

        }

    @staticmethod
    def add_step(

        result,

        label,

        status,

        message,

        percent

    ):

        result["steps"].append({

            "label": label,

            "status": status,

            "message": message,

            "percent": percent

        })

        result["progress_percent"] = percent

        result["current_step"] = label

        PLCBufferOperationManager.publish_status(
            result=result,
            status_override="RUNNING"
        )

    @staticmethod
    def finish(

        result,

        success,

        message

    ):

        result["success"] = success

        result["status"] = (
            "SUCCESS"
            if success
            else
            "BLOCKED"
        )

        result["current_step"] = message

        if success:

            result["progress_percent"] = 100

        elif result["progress_percent"] == 0:

            result["progress_percent"] = 5

        PLCBufferOperationManager.publish_status(
            result=result,
            completed=True
        )

    @staticmethod
    def publish_status(

        result,

        status_override=None,

        completed=False

    ):

        status_job_id = result.get(
            "status_job_id"
        )

        if not status_job_id:

            return

        try:

            PLCOperationJobManager.update_from_result(

                job_id=status_job_id,

                result=result,

                status_override=status_override,

                completed=completed

            )

        except Exception as exc:

            warning = (
                f"Operation status update failed: {exc}"
            )

            if warning not in result.get(
                "warnings",
                []
            ):

                result.setdefault(
                    "warnings",
                    []
                ).append(
                    warning
                )

    @staticmethod
    def fail_with_step(

        result,

        label,

        message,

        percent

    ):

        PLCBufferOperationManager.add_step(

            result,

            label,

            "FAILED",

            message,

            percent

        )

        result["errors"].append(
            message
        )

        PLCBufferOperationManager.finish(
            result,
            False,
            message
        )

        raise Exception(
            message
        )

    @staticmethod
    def check_recipe_usage_allowed(

        recipe

    ):

        if (
            recipe.get(
                "version_usage_status"
            )
            ==
            "HISTORY_RELEASED"
        ):

            return (
                "Historical released recipe cannot use PLC buffer operations. "
                "Open the current production version."
            )

        return ""

    @staticmethod
    def require_array_tag(

        recipe,

        purpose,

        label

    ):

        tag = PLCBufferOperationManager.get_tag_for_purpose(
            recipe,
            purpose
        )

        payload_size = (
            PLCDownloadPreparationManager
            .get_payload_size_for_recipe(recipe)
        )

        if not PLCBufferOperationManager.valid_real_array_tag(
            tag,
            payload_size=payload_size
        ):

            raise Exception(
                f"{label} tag for {purpose} must be configured as REAL[{payload_size}]."
            )

        return tag

    @staticmethod
    def require_bool_tag(

        recipe,

        purpose,

        label

    ):

        tag = PLCBufferOperationManager.get_tag_for_purpose(
            recipe,
            purpose
        )

        tag_type = (
            tag.get(
                "tag_type"
            )
            if tag
            else
            ""
        )

        if (
            not tag
            or
            str(
                tag_type
            ).upper() != "BOOL"
            or
            tag.get(
                "is_array"
            ) == 1
        ):

            raise Exception(
                f"{label} tag for {purpose} must be configured as BOOL."
            )

        return tag

    @staticmethod
    def require_string_array_tag(

        recipe,

        purpose,

        label

    ):

        tag = PLCBufferOperationManager.get_tag_for_purpose(
            recipe,
            purpose
        )

        if not PLCBufferOperationManager.valid_string_array_tag(
            tag
        ):

            raise Exception(
                f"{label} tag for {purpose} must be configured as STRING array."
            )

        return tag

    @staticmethod
    def get_array_size_from_tag(

        tag

    ):

        if not tag:

            return None

        try:

            size = int(
                tag.get(
                    "array_size"
                )
                or
                0
            )

        except Exception:

            size = 0

        if size > 0:

            return size

        start = tag.get(
            "array_start_index"
        )

        end = tag.get(
            "array_end_index"
        )

        if start is None or end is None:

            return None

        try:

            start = int(
                start
            )

            end = int(
                end
            )

        except Exception:

            return None

        if end < start:

            return None

        return (
            end - start + 1
        )

    @staticmethod
    def get_array_start_from_tag(

        tag

    ):

        if not tag:

            return 0

        try:

            return int(
                tag.get(
                    "array_start_index"
                )
                or
                0
            )

        except Exception:

            return 0

    @staticmethod
    def valid_real_array_tag(

        tag,

        payload_size=None

    ):

        if payload_size is None:

            payload_size = PLCBufferOperationManager.PAYLOAD_SIZE

        if not payload_size:

            return False

        if not tag:

            return False

        if str(
            tag.get(
                "tag_type"
            )
            or
            ""
        ).upper() != "REAL":

            return False

        if tag.get(
            "is_array"
        ) != 1:

            return False

        if (
            tag.get(
                "array_size"
            )
            or
            0
        ) < payload_size:

            return False

        return True

    @staticmethod
    def valid_bool_tag(

        tag

    ):

        if not tag:

            return False

        if str(
            tag.get(
                "tag_type"
            )
            or
            ""
        ).upper() != "BOOL":

            return False

        if tag.get(
            "is_array"
        ) == 1:

            return False

        return True

    @staticmethod
    def valid_string_array_tag(

        tag

    ):

        if not tag:

            return False

        if str(
            tag.get(
                "tag_type"
            )
            or
            ""
        ).upper() != "STRING":

            return False

        if tag.get(
            "is_array"
        ) != 1:

            return False

        array_size = PLCBufferOperationManager.get_array_size_from_tag(
            tag
        )

        return bool(
            array_size
            and
            array_size > 0
        )

    @staticmethod
    def get_phase_payload_size(

        tags

    ):

        sizes = []

        for tag in tags:

            size = PLCBufferOperationManager.get_array_size_from_tag(
                tag
            )

            if not size:

                raise Exception(
                    "Phase control array size is not configured."
                )

            sizes.append(
                size
            )

        unique_sizes = set(
            sizes
        )

        if len(
            unique_sizes
        ) != 1:

            raise Exception(
                "Phase control name, stop, and position arrays must use the same size."
            )

        return sizes[0]

    @staticmethod
    def build_phase_control_payload(

        recipe,

        payload_size

    ):

        rows = RecipePhaseControlManager.get_recipe_phase_control(
            recipe["id"]
        )

        if len(
            rows
        ) > payload_size:

            raise Exception(
                "Configured phase control rows exceed PLC phase array size "
                f"({len(rows)} rows > {payload_size} array elements)."
            )

        phase_names = []

        stop_values = []

        position_values = []

        for row in rows:

            phase_name = str(
                row.get(
                    "phase_control_name"
                )
                or
                ""
            )

            if phase_name.strip().upper() == "EMPTY PHASE":

                phase_name = ""

            phase_names.append(
                phase_name
            )

            stop_values.append(
                str(
                    row.get(
                        "stop_option"
                    )
                    or
                    "No"
                )
            )

            position_values.append(
                str(
                    row.get(
                        "position_option"
                    )
                    or
                    "No"
                )
            )

        while len(
            phase_names
        ) < payload_size:

            phase_names.append(
                ""
            )

            stop_values.append(
                "No"
            )

            position_values.append(
                "No"
            )

        return {
            "rows": rows,
            "phase_names": phase_names,
            "stop_values": stop_values,
            "position_values": position_values,
            "payload_size": payload_size
        }

    @staticmethod
    def write_string_array_or_block(

        plc_conn,

        tag,

        values,

        result,

        label,

        percent

    ):

        start_index = PLCBufferOperationManager.get_array_start_from_tag(
            tag
        )

        tag_name = tag[
            "tag_name"
        ]

        for offset, value in enumerate(
            values
        ):

            element_tag = (
                f"{tag_name}"
                f"[{start_index + offset}]"
            )

            write_result = plc_conn.write(
                (
                    element_tag,
                    value
                )
            )

            error = getattr(
                write_result,
                "error",
                None
            )

            if (
                write_result is None
                or
                error
                or
                not bool(
                    write_result
                )
            ):

                PLCBufferOperationManager.fail_with_step(

                    result,

                    label,

                    f"{element_tag} write failed: {error}",

                    percent

                )

        PLCBufferOperationManager.add_step(

            result,

            label,

            "OK",

            f"{tag_name}[{start_index}] to {tag_name}[{start_index + len(values) - 1}] written.",

            percent

        )

    @staticmethod
    def read_string_array_or_block(

        plc_conn,

        tag,

        result,

        label,

        percent

    ):

        size = PLCBufferOperationManager.get_array_size_from_tag(
            tag
        )

        start_index = PLCBufferOperationManager.get_array_start_from_tag(
            tag
        )

        tag_name = tag[
            "tag_name"
        ]

        payload = []

        for offset in range(
            size
        ):

            element_tag = (
                f"{tag_name}"
                f"[{start_index + offset}]"
            )

            read_result = plc_conn.read(
                element_tag
            )

            error = getattr(
                read_result,
                "error",
                None
            )

            if (
                read_result is None
                or
                error
            ):

                PLCBufferOperationManager.fail_with_step(

                    result,

                    label,

                    f"{element_tag} read failed: {error}",

                    percent

                )

            value = getattr(
                read_result,
                "value",
                ""
            )

            payload.append(
                ""
                if value is None
                else
                str(
                    value
                )
            )

        PLCBufferOperationManager.add_step(

            result,

            label,

            "OK",

            f"{tag_name}[{start_index}] to {tag_name}[{start_index + size - 1}] read successfully.",

            percent

        )

        return payload

    @staticmethod
    def compare_string_payloads(

        expected,

        actual

    ):

        mismatches = []

        for index, expected_value in enumerate(
            expected
        ):

            actual_value = (
                actual[index]
                if actual and index < len(actual)
                else
                None
            )

            if str(
                actual_value
                if actual_value is not None
                else
                ""
            ) != str(
                expected_value
                if expected_value is not None
                else
                ""
            ):

                mismatches.append(
                    {
                        "index": index,
                        "expected": expected_value,
                        "actual": actual_value
                    }
                )

        return {
            "matched": not mismatches,
            "mismatch_count": len(
                mismatches
            ),
            "mismatches": mismatches
        }

    @staticmethod
    def find_stage_string_array_tag_by_name(
        recipe,
        tag_name
    ):
        if not recipe or not tag_name:
            return None

        try:
            tags = PLCTagManager.get_stage_tags(
                recipe["machine_id"],
                recipe["stage_id"]
            )
        except Exception:
            return None

        expected = str(tag_name or "").strip().upper()
        for tag in tags:
            if str(tag.get("tag_name") or "").strip().upper() != expected:
                continue

            if PLCBufferOperationManager.valid_string_array_tag(tag):
                return tag

        return None

    @staticmethod
    def probe_string_array_tag(
        plc_conn,
        tag_name,
        array_size,
        start_index=0
    ):
        try:
            read_result = plc_conn.read(
                f"{tag_name}[{start_index}]"
            )
        except Exception:
            return None

        error = getattr(
            read_result,
            "error",
            None
        )

        if (
            read_result is None
            or
            error
            or
            not bool(read_result)
        ):
            return None

        return {
            "tag_name": tag_name,
            "tag_type": "STRING",
            "is_array": 1,
            "array_size": int(array_size),
            "array_start_index": int(start_index),
            "array_end_index": int(start_index) + int(array_size) - 1
        }

    @staticmethod
    def normalize_phase_control_plc_text(row):
        phase_name = str(
            row.get("phase_control_name")
            or
            ""
        )

        if phase_name.strip().upper() == "EMPTY PHASE":
            return ""

        return phase_name

    @staticmethod
    def phase_row_has_payload(row):
        phase_name = PLCBufferOperationManager.normalize_phase_control_plc_text(
            row
        )

        stop_value = str(
            row.get("stop_option")
            or
            "No"
        )

        position_value = str(
            row.get("position_option")
            or
            "No"
        )

        return bool(
            phase_name.strip()
            or
            stop_value.strip().upper() == "YES"
            or
            position_value.strip().upper() == "YES"
        )

    @staticmethod
    def build_phase_control_payload_from_rows(
        rows,
        payload_size
    ):
        if payload_size is None or int(payload_size) <= 0:
            raise Exception("Phase control array size is not configured.")

        payload_size = int(payload_size)

        overflow_rows = [
            row for row in rows[payload_size:]
            if PLCBufferOperationManager.phase_row_has_payload(row)
        ]

        if overflow_rows:
            first = overflow_rows[0]
            raise Exception(
                "Configured phase control rows exceed PLC phase array size "
                f"for group {first.get('phase_group_name') or first.get('phase_group_code')}. "
                f"Array size is {payload_size}."
            )

        phase_names = []
        stop_values = []
        position_values = []

        for row in rows[:payload_size]:
            phase_names.append(
                PLCBufferOperationManager.normalize_phase_control_plc_text(row)
            )
            stop_values.append(
                str(
                    row.get("stop_option")
                    or
                    "No"
                )
            )
            position_values.append(
                str(
                    row.get("position_option")
                    or
                    "No"
                )
            )

        while len(phase_names) < payload_size:
            phase_names.append("")
            stop_values.append("No")
            position_values.append("No")

        return {
            "phase_names": phase_names,
            "stop_values": stop_values,
            "position_values": position_values,
            "payload_size": payload_size
        }

    @staticmethod
    def split_phase_rows_by_group(rows):
        grouped = {}

        for row in rows:
            group_code = str(
                row.get("phase_group_code")
                or
                "MAIN"
            ).strip().upper()

            grouped.setdefault(
                group_code,
                []
            ).append(row)

        return grouped

    @staticmethod
    def compare_split_phase_tag(
        plc_conn,
        tag,
        values,
        result,
        label,
        verify_percent
    ):
        readback = PLCBufferOperationManager.read_string_array_or_block(
            plc_conn=plc_conn,
            tag=tag,
            result=result,
            label=f"Read {label} back",
            percent=verify_percent
        )

        compare = PLCBufferOperationManager.compare_string_payloads(
            values,
            readback
        )

        if not compare["matched"]:
            first = compare["mismatches"][0]
            PLCBufferOperationManager.fail_with_step(
                result,
                f"Verify {label}",
                (
                    f"Mismatch at index {first['index']}: "
                    f"expected {first['expected']!r}, actual {first['actual']!r}."
                ),
                verify_percent
            )

    @staticmethod
    def write_phase_split_tag(
        plc_conn,
        tag,
        values,
        result,
        label,
        write_percent,
        verify_percent
    ):
        PLCBufferOperationManager.write_string_array_or_block(
            plc_conn=plc_conn,
            tag=tag,
            values=values,
            result=result,
            label=f"Write {label}",
            percent=write_percent
        )

        PLCBufferOperationManager.compare_split_phase_tag(
            plc_conn=plc_conn,
            tag=tag,
            values=values,
            result=result,
            label=label,
            verify_percent=verify_percent
        )

    @staticmethod
    def write_split_second_stage_phase_arrays(
        plc_conn,
        recipe,
        result,
        write_percent,
        verify_percent,
        bt_phase_tag,
    ):
        """Write P15 Second Stage recipe phase selections only.

        SHAPING_SIDE and all stop/position strings are fixed PLC behavior and
        are deliberately excluded from the CRS recipe payload.
        """
        rows = RecipePhaseControlManager.get_recipe_phase_control(recipe["id"])
        grouped = PLCBufferOperationManager.split_phase_rows_by_group(rows)
        cap_rows = grouped.get("CAP_STRIP_SIDE", [])
        bt_rows = grouped.get("BT_SIDE", [])

        cap_phase_tag = PLCBufferOperationManager.get_tag_for_purpose(
            recipe, PLCBufferOperationManager.CAP_STRIP_PHASE_STRING_PURPOSE
        )
        if not PLCBufferOperationManager.valid_string_array_tag(cap_phase_tag):
            cap_phase_tag = PLCBufferOperationManager.find_stage_string_array_tag_by_name(
                recipe, "CRS_Phase_Cntrl_String_CapSd"
            )
        if not cap_phase_tag:
            cap_phase_tag = PLCBufferOperationManager.probe_string_array_tag(
                plc_conn, "CRS_Phase_Cntrl_String_CapSd", 2
            )
        if not cap_phase_tag:
            raise Exception(
                "Cap strip phase names tag must be configured as a STRING array."
            )

        written_elements = 0
        cap_payload = PLCBufferOperationManager.build_phase_control_payload_from_rows(
            cap_rows, PLCBufferOperationManager.get_array_size_from_tag(cap_phase_tag)
        )
        PLCBufferOperationManager.write_phase_split_tag(
            plc_conn=plc_conn, tag=cap_phase_tag,
            values=cap_payload["phase_names"], result=result,
            label="cap strip phase names", write_percent=write_percent,
            verify_percent=verify_percent
        )
        written_elements += cap_payload["payload_size"]

        bt_payload = PLCBufferOperationManager.build_phase_control_payload_from_rows(
            bt_rows, PLCBufferOperationManager.get_array_size_from_tag(bt_phase_tag)
        )
        PLCBufferOperationManager.write_phase_split_tag(
            plc_conn=plc_conn, tag=bt_phase_tag,
            values=bt_payload["phase_names"], result=result,
            label="B&T phase names", write_percent=write_percent,
            verify_percent=verify_percent
        )
        written_elements += bt_payload["payload_size"]

        PLCBufferOperationManager.add_step(
            result,
            "Phase control selections verified",
            "OK",
            "Second-stage CAP_STRIP_SIDE and BT_SIDE phase selections written and verified; "
            "SHAPING_SIDE and stop/position remain PLC-fixed non-recipe data.",
            verify_percent
        )
        result["metrics"]["phase_control_elements"] = written_elements
        return {
            "rows": rows,
            "grouped": True,
            "payload_size": written_elements,
            "recipe_phase_fields": ["phase_group_code", "line_no", "phase_control_id"],
        }

    @staticmethod
    def require_phase_string_array_tag(
        recipe,
        purpose,
        label,
        fallback_tag_names=None
    ):
        try:
            return PLCBufferOperationManager.require_string_array_tag(
                recipe,
                purpose,
                label
            )
        except Exception as exc:
            for tag_name in fallback_tag_names or []:
                tag = PLCBufferOperationManager.find_stage_string_array_tag_by_name(
                    recipe,
                    tag_name
                )

                if tag:
                    return tag

            raise exc

    @staticmethod
    def write_phase_control_arrays(

        plc_conn,

        recipe,

        result,

        write_percent,

        verify_percent

    ):

        if PLCBufferOperationManager.is_second_stage_recipe(recipe):
            bt_phase_tag = PLCBufferOperationManager.require_phase_string_array_tag(
                recipe,
                PLCBufferOperationManager.BT_PHASE_STRING_PURPOSE,
                "B&T phase control names",
                ["CRS_Phase_Cntrl_String", "CRS_Phase_Control_String"]
            )
            return PLCBufferOperationManager.write_split_second_stage_phase_arrays(
                plc_conn=plc_conn,
                recipe=recipe,
                result=result,
                write_percent=write_percent,
                verify_percent=verify_percent,
                bt_phase_tag=bt_phase_tag,
            )

        phase_tag = PLCBufferOperationManager.require_phase_string_array_tag(
            recipe,
            PLCBufferOperationManager.PHASE_STRING_PURPOSE,
            "Phase control names",
            ["CRS_Phase_Cntrl_String", "CRS_Phase_Control_String"]
        )
        stop_tag = PLCBufferOperationManager.require_phase_string_array_tag(
            recipe,
            PLCBufferOperationManager.PHASE_STOP_PURPOSE,
            "Phase control stop",
            ["CRS_Phase_Cntrl_Stop_String", "CRS_Phase_Control_Stop_String"]
        )
        position_tag = PLCBufferOperationManager.require_phase_string_array_tag(
            recipe,
            PLCBufferOperationManager.PHASE_POSITION_PURPOSE,
            "Phase control position",
            [
                "CRS_Phase_Cntrl_Pos_String",
                "CRS_Phase_Cntrl_Position_String",
                "CRS_Phase_Control_Position_String"
            ]
        )

        phase_size = PLCBufferOperationManager.get_phase_payload_size(
            [
                phase_tag,
                stop_tag,
                position_tag
            ]
        )

        payload = PLCBufferOperationManager.build_phase_control_payload(
            recipe,
            phase_size
        )

        PLCBufferOperationManager.write_string_array_or_block(
            plc_conn=plc_conn,
            tag=phase_tag,
            values=payload["phase_names"],
            result=result,
            label="Write phase control names",
            percent=write_percent
        )

        PLCBufferOperationManager.write_string_array_or_block(
            plc_conn=plc_conn,
            tag=stop_tag,
            values=payload["stop_values"],
            result=result,
            label="Write phase stop options",
            percent=write_percent
        )

        PLCBufferOperationManager.write_string_array_or_block(
            plc_conn=plc_conn,
            tag=position_tag,
            values=payload["position_values"],
            result=result,
            label="Write phase position options",
            percent=write_percent
        )

        phase_readback = PLCBufferOperationManager.read_string_array_or_block(
            plc_conn=plc_conn,
            tag=phase_tag,
            result=result,
            label="Read phase control names back",
            percent=verify_percent
        )

        stop_readback = PLCBufferOperationManager.read_string_array_or_block(
            plc_conn=plc_conn,
            tag=stop_tag,
            result=result,
            label="Read phase stop options back",
            percent=verify_percent
        )

        position_readback = PLCBufferOperationManager.read_string_array_or_block(
            plc_conn=plc_conn,
            tag=position_tag,
            result=result,
            label="Read phase position options back",
            percent=verify_percent
        )

        compare_results = [
            (
                "phase names",
                PLCBufferOperationManager.compare_string_payloads(
                    payload["phase_names"],
                    phase_readback
                )
            ),
            (
                "phase stop options",
                PLCBufferOperationManager.compare_string_payloads(
                    payload["stop_values"],
                    stop_readback
                )
            ),
            (
                "phase position options",
                PLCBufferOperationManager.compare_string_payloads(
                    payload["position_values"],
                    position_readback
                )
            )
        ]

        for label, compare in compare_results:

            if not compare["matched"]:

                first = compare["mismatches"][0]

                PLCBufferOperationManager.fail_with_step(
                    result,
                    f"Verify {label}",
                    (
                        f"Mismatch at index {first['index']}: "
                        f"expected {first['expected']!r}, actual {first['actual']!r}."
                    ),
                    verify_percent
                )

        PLCBufferOperationManager.add_step(
            result,
            "Phase control arrays verified",
            "OK",
            f"{phase_size} phase-control elements written and verified.",
            verify_percent
        )

        result["metrics"]["phase_control_elements"] = phase_size

        return payload

    @staticmethod
    def build_database_payload(

        recipe_values,

        payload_size=None

    ):

        if payload_size is None:

            payload_size = PLCBufferOperationManager.PAYLOAD_SIZE

        if not payload_size:

            return []

        payload = [
            0.0
            for _ in range(
                payload_size
            )
        ]

        for row in recipe_values:

            plc_index = row[
                "plc_array_index"
            ]

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

            payload[plc_index] = float(
                row[
                    "parameter_value"
                ]
            )

        return payload

    @staticmethod
    def validate_payload_or_block(

        result,

        recipe_values,

        payload,

        label,

        percent

    ):

        validation = (
            PLCDownloadPreparationManager
            .validate_payload_values(

                recipe_values=recipe_values,

                payload_values=payload

            )
        )

        result["metrics"][
            f"{label}_checked"
        ] = validation[
            "checked_parameters"
        ]

        if not validation["valid"]:

            detail = (
                "; ".join(
                    validation["errors"][:5]
                )
            )

            PLCBufferOperationManager.fail_with_step(

                result,

                label,

                detail,

                percent

            )

        PLCBufferOperationManager.add_step(

            result,

            label,

            "OK",

            f"{validation['checked_parameters']} parameters validated.",

            percent

        )

    @staticmethod
    def read_array_or_block(

        plc_conn,

        tag_name,

        result,

        label,

        percent,

        payload_size=None

    ):

        if payload_size is None:

            payload_size = result.get("payload_size") or PLCBufferOperationManager.PAYLOAD_SIZE

        if not payload_size:

            PLCBufferOperationManager.add_step(
                result,
                label,
                "FAILED",
                "PLC array read skipped because recipe data array size is not configured.",
                percent
            )

            return None

        expression = (
            f"{tag_name}"
            f"{{{payload_size}}}"
        )

        read_result = plc_conn.read(
            expression
        )

        error = getattr(
            read_result,
            "error",
            None
        )

        value = getattr(
            read_result,
            "value",
            None
        )

        if (
            read_result is None
            or
            error
        ):

            PLCBufferOperationManager.fail_with_step(

                result,

                label,

                f"{expression} read failed: {error}",

                percent

            )

        payload = PLCBufferOperationManager.normalize_payload(
            value,
            payload_size=payload_size
        )

        if payload is None:

            PLCBufferOperationManager.fail_with_step(

                result,

                label,

                f"{expression} did not return {payload_size} values.",

                percent

            )

        PLCBufferOperationManager.add_step(

            result,

            label,

            "OK",

            f"{expression} read successfully.",

            percent

        )

        return payload

    @staticmethod
    def write_or_block(

        plc_conn,

        tag_name,

        value,

        result,

        label,

        percent

    ):

        write_tag_name = (
            PLCBufferOperationManager
            .get_write_tag_name(
                tag_name,
                value
            )
        )

        write_result = plc_conn.write(
            (
                write_tag_name,
                value
            )
        )

        error = getattr(
            write_result,
            "error",
            None
        )

        if (
            write_result is None
            or
            error
            or
            not bool(
                write_result
            )
        ):

            PLCBufferOperationManager.fail_with_step(

                result,

                label,

                f"{write_tag_name} write failed: {error}",

                percent

            )

        display_value = (
            f"Array[{len(value)}]"
            if isinstance(
                value,
                list
            )
            else
            str(
                value
            )
        )

        PLCBufferOperationManager.add_step(

            result,

            label,

            "OK",

            f"{write_tag_name} written: {display_value}",

            percent

        )

    @staticmethod
    def get_write_tag_name(

        tag_name,

        value

    ):

        if isinstance(
            value,
            list
        ):

            return (
                f"{tag_name}"
                f"{{{len(value)}}}"
            )

        return tag_name

    @staticmethod
    def read_true_or_block(

        plc_conn,

        tag_name,

        result,

        label,

        percent

    ):

        read_result = plc_conn.read(
            tag_name
        )

        error = getattr(
            read_result,
            "error",
            None
        )

        value = getattr(
            read_result,
            "value",
            None
        )

        if (
            read_result is None
            or
            error
        ):

            PLCBufferOperationManager.fail_with_step(

                result,

                label,

                f"{tag_name} read failed: {error}",

                percent

            )

        if not PLCDownloadPreparationManager.is_true_value(
            value
        ):

            PLCBufferOperationManager.fail_with_step(

                result,

                label,

                f"{tag_name} is not TRUE. Actual value: {value}",

                percent

            )

        PLCBufferOperationManager.add_step(

            result,

            label,

            "OK",

            f"{tag_name} is TRUE.",

            percent

        )

    @staticmethod
    def normalize_payload(

        value,

        payload_size=None

    ):

        if value is None:

            return None

        try:

            payload = list(
                value
            )

        except Exception:

            return None

        if payload_size is None:

            payload_size = PLCBufferOperationManager.PAYLOAD_SIZE

        if not payload_size:

            return None

        if len(
            payload
        ) < payload_size:

            return None

        try:

            return [
                float(
                    payload[index]
                )
                for index in range(
                    payload_size
                )
            ]

        except Exception:

            return None

    @staticmethod
    def compare_payloads(

        expected,

        actual

    ):

        result = {

            "checked": True,

            "matched": True,

            "mismatch_count": 0,

            "mismatches": []

        }

        for index, expected_value in enumerate(
            expected
        ):

            try:

                actual_value = float(
                    actual[index]
                )

            except Exception:

                actual_value = None

            if (
                actual_value is None
                or
                abs(
                    float(
                        expected_value
                    )
                    -
                    actual_value
                ) > 0.0001
            ):

                result["matched"] = False

                result["mismatch_count"] += 1

                if len(
                    result["mismatches"]
                ) < 8:

                    result["mismatches"].append(
                        f"Index {index}: expected {expected_value}, actual {actual_value}"
                    )

        return result

    @staticmethod
    def compare_recipe_values_to_payload(

        recipe_values,

        payload,

        payload_size=None

    ):

        if payload_size is None:

            payload_size = PLCBufferOperationManager.PAYLOAD_SIZE

        if not payload_size:

            result = {

                "checked": False,

                "valid": False,

                "issues": [
                    "Recipe data array size is not configured for this machine/stage."
                ],

                "issue_count": 1

            }

            return result

        result = {

            "checked": True,

            "matched": True,

            "mismatch_count": 0,

            "checked_parameters": 0,

            "mismatches": []

        }

        for row in recipe_values:

            plc_index = row[
                "plc_array_index"
            ]

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

            result["checked_parameters"] += 1

            expected_value = float(
                payload[
                    plc_index
                ]
            )

            actual_value = float(
                row[
                    "parameter_value"
                ]
            )

            if abs(
                expected_value
                -
                actual_value
            ) <= 0.0001:

                continue

            result["matched"] = False

            result["mismatch_count"] += 1

            if len(
                result["mismatches"]
            ) < 8:

                result["mismatches"].append(
                    (
                        f"Tag {row['tag_index']} / index {plc_index}: "
                        f"CRS_Recipe_Data {expected_value}, "
                        f"database {actual_value}"
                    )
                )

        return result

    @staticmethod
    def update_recipe_values_from_payload(

        recipe_values,

        payload,

        username,

        user_role,

        change_source="CRS_BUFFER_SAVE_TO_RECIPE",

        change_reason="Recipe Save from CRS_Recipe_Data buffer",

        payload_size=None

    ):

        if payload_size is None:

            payload_size = PLCBufferOperationManager.PAYLOAD_SIZE

        if not payload_size:

            return 0

        changed_count = 0

        for row in recipe_values:

            plc_index = row[
                "plc_array_index"
            ]

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

            old_value = float(
                row[
                    "parameter_value"
                ]
            )

            new_value = float(
                payload[
                    plc_index
                ]
            )

            if abs(
                old_value - new_value
            ) <= 0.0001:

                continue

            RecipeParameterValueManager.update_recipe_value(

                value_id=row["id"],

                new_value=new_value,

                changed_by=username,

                change_reason=change_reason,

                user_role=user_role,

                change_source=change_source

            )

            changed_count += 1

        return changed_count

    @staticmethod
    def log_operation(

        result,

        username,

        user_role

    ):

        recipe = result.get(
            "recipe"
        )

        operation = result.get(
            "operation"
        )

        operation_info = PLCBufferOperationManager.OPERATIONS.get(
            operation,
            {}
        )

        if not recipe:

            return

        plc = result.get(
            "plc"
        )

        AuditManager.log_event(

            username=username,

            role=user_role,

            action=operation_info.get(
                "action",
                "PLC_BUFFER_OPERATION"
            ),

            change_source="PLC_BUFFER",

            plc_name=plc["plc_name"]
            if plc
            else
            None,

            recipe_code=recipe["recipe_code"],

            recipe_version=recipe["version"],

            new_value=result["status"],

            reason=result["current_step"]

        )
