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

from database.upload_history_manager import (
    UploadHistoryManager
)

from flask_app.security.role_guard import (
    role_can
)


class PLCBufferOperationManager:

    PAYLOAD_SIZE = 500

    SOURCE_PURPOSE = "RECIPE_DATA"

    DESTINATION_PURPOSE = "TEST_RECIPE_DATA"

    RECIPE_CODE_PURPOSE = "RECIPE_CODE"

    MANUAL_PURPOSE = "MACHINE_IN_MANUAL"

    ENABLE_PURPOSE = "DOWNLOAD_ENABLE"

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

                        username=username

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

        normalized = (
            message
            or
            ""
        ).lower()

        connection_markers = [
            "failed to open a connection",
            "connection refused",
            "timed out",
            "timeout",
            "unreachable",
            "no route to host"
        ]

        return any(
            marker in normalized
            for marker in connection_markers
        )

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

        return (
            "PLC connection failed after database validation. "
            f"CRS could not connect to {plc_name} ({plc_ip}). "
            "Check PLC power, network path, controller mode, and selected "
            f"PLC configuration, then retry. Technical detail: {message}"
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

            "issues": []

        }

        if not recipe:

            context["issues"].append(
                "Recipe not found."
            )

            return context

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

        for purpose in [
            PLCBufferOperationManager.SOURCE_PURPOSE,
            PLCBufferOperationManager.DESTINATION_PURPOSE,
            PLCBufferOperationManager.RECIPE_CODE_PURPOSE,
            PLCBufferOperationManager.MANUAL_PURPOSE,
            PLCBufferOperationManager.ENABLE_PURPOSE
        ]:

            context["tags"][purpose] = (
                PLCTagManager
                .get_tag_by_purpose(

                    machine_id=recipe["machine_id"],

                    stage_id=recipe["stage_id"],

                    tag_purpose=purpose

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
                tag
            ):

                context["issues"].append(
                    f"{purpose} must be configured as REAL[500]."
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
            PLCTagManager
            .get_tag_by_purpose(

                machine_id=recipe["machine_id"],

                stage_id=recipe["stage_id"],

                tag_purpose=PLCBufferOperationManager.RECIPE_CODE_PURPOSE

            )
        )

        payload = (
            PLCBufferOperationManager
            .build_database_payload(
                values
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

            readback = (
                PLCBufferOperationManager
                .read_array_or_block(

                    plc_conn=plc_conn,

                    tag_name=source_tag["tag_name"],

                    result=result,

                    label="Read CRS buffer back",

                    percent=85

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

                user_role=user_role

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
                payload=source_payload
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
                values
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

            destination_readback = (
                PLCBufferOperationManager
                .read_array_or_block(

                    plc_conn=plc_conn,

                    tag_name=destination_tag["tag_name"],

                    result=result,

                    label="Read PLC destination back",

                    percent=95

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

        PLCBufferOperationManager.add_step(
            result,
            "Download verified",
            "OK",
            "CRS_Recipe_Data copied to PLC destination buffer.",
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
                    "CRS buffer downloaded to PLC destination buffer"
                )

            except Exception as exc:

                result["warnings"].append(
                    f"Download history completion record failed: {exc}"
                )

        return result

    @staticmethod
    def upload_plc_buffer_to_crs_buffer(

        result,

        username

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

                )
            )

            PLCBufferOperationManager.validate_payload_or_block(

                result=result,

                recipe_values=values,

                payload=source_payload,

                label="PLC source buffer min/max validation",

                percent=62

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

                )
            )

        compare = PLCBufferOperationManager.compare_payloads(
            source_payload,
            destination_readback
        )

        result["payload_compare"] = compare

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

            UploadHistoryManager.log_upload(

                plc_name=result["plc"]["plc_name"],

                recipe_code=recipe["recipe_code"],

                recipe_version=recipe["version"],

                status="SUCCESS",

                uploaded_by=username,

                remarks="PLC destination buffer copied to CRS buffer"

            )

        except Exception as exc:

            result["warnings"].append(
                f"Upload history record failed: {exc}"
            )

        return result

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

        tag = PLCTagManager.get_tag_by_purpose(

            machine_id=recipe["machine_id"],

            stage_id=recipe["stage_id"],

            tag_purpose=purpose

        )

        if not PLCBufferOperationManager.valid_real_array_tag(
            tag
        ):

            raise Exception(
                f"{label} tag for {purpose} must be configured as REAL[500]."
            )

        return tag

    @staticmethod
    def require_bool_tag(

        recipe,

        purpose,

        label

    ):

        tag = PLCTagManager.get_tag_by_purpose(

            machine_id=recipe["machine_id"],

            stage_id=recipe["stage_id"],

            tag_purpose=purpose

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
    def valid_real_array_tag(

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
        ) < PLCBufferOperationManager.PAYLOAD_SIZE:

            return False

        return True

    @staticmethod
    def build_database_payload(

        recipe_values

    ):

        payload = [
            0.0
            for _ in range(
                PLCBufferOperationManager.PAYLOAD_SIZE
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
                plc_index >= PLCBufferOperationManager.PAYLOAD_SIZE
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

        percent

    ):

        expression = (
            f"{tag_name}"
            f"{{{PLCBufferOperationManager.PAYLOAD_SIZE}}}"
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
            value
        )

        if payload is None:

            PLCBufferOperationManager.fail_with_step(

                result,

                label,

                f"{expression} did not return 500 values.",

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

        value

    ):

        if value is None:

            return None

        try:

            payload = list(
                value
            )

        except Exception:

            return None

        if len(
            payload
        ) < PLCBufferOperationManager.PAYLOAD_SIZE:

            return None

        try:

            return [
                float(
                    payload[index]
                )
                for index in range(
                    PLCBufferOperationManager.PAYLOAD_SIZE
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

        payload

    ):

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
                plc_index >= PLCBufferOperationManager.PAYLOAD_SIZE
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

        user_role

    ):

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
                plc_index >= PLCBufferOperationManager.PAYLOAD_SIZE
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

                change_reason="Recipe Save from CRS_Recipe_Data buffer",

                user_role=user_role

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
