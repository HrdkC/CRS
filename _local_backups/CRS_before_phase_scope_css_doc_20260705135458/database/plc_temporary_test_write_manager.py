from pycomm3 import (
    LogixDriver
)

from database.audit_manager import (
    AuditManager
)

from database.plc_download_preparation_manager import (
    PLCDownloadPreparationManager
)

from database.plc_tag_manager import (
    PLCTagManager
)

from database.recipe_parameter_value_manager import (
    RecipeParameterValueManager
)


class PLCTemporaryTestWriteManager:

    TEST_BUFFER_PURPOSE = "TEST_RECIPE_DATA"

    @staticmethod
    def run_test_write(

        recipe_id,

        plc_id,

        username,

        user_role,

        confirmation

    ):

        result = {

            "executed": False,

            "ready": False,

            "status": "BLOCKED",

            "errors": [],

            "warnings": [],

            "recipe": None,

            "plc": None,

            "write_plan": {},

            "test_tags": {},

            "steps": [],

            "status_values": {},

            "payload_compare": {

                "checked": False,

                "matched": False,

                "mismatch_count": 0,

                "mismatches": []

            },

            "request_reset": False,

            "request_used": False

        }

        if confirmation != "YES":

            result["errors"].append(
                "Direct PLC test buffer write confirmation is required."
            )

            return result

        preparation = (
            PLCDownloadPreparationManager
            .dry_run(

                recipe_id=recipe_id,

                plc_id=plc_id

            )
        )

        result["recipe"] = preparation[
            "recipe"
        ]

        result["plc"] = preparation[
            "plc"
        ]

        result["write_plan"] = preparation[
            "write_plan"
        ]

        if not preparation["ready"]:

            result["errors"].extend(
                preparation["errors"]
            )

            return result

        test_tags = (
            PLCTemporaryTestWriteManager
            .get_required_test_tags(
                result["recipe"]
            )
        )

        result["test_tags"] = test_tags[
            "tags"
        ]

        if test_tags["errors"]:

            result["errors"].extend(
                test_tags["errors"]
            )

            return result

        values = (
            RecipeParameterValueManager
            .get_recipe_values(
                recipe_id
            )
        )

        payload_size = (
            result["write_plan"].get(
                "payload_size"
            )
            or
            PLCDownloadPreparationManager.PAYLOAD_SIZE
        )

        if not payload_size:

            result["errors"].append(
                "Recipe data array size is not configured for this machine/stage."
            )

            return result

        recipe_array = (
            PLCTemporaryTestWriteManager
            .build_recipe_array(

                values=values,

                payload_size=payload_size

            )
        )

        database_payload_validation = (
            PLCDownloadPreparationManager
            .validate_payload_values(

                recipe_values=values,

                payload_values=recipe_array

            )
        )

        if not database_payload_validation["valid"]:

            result["errors"].append(
                "Recipe database payload validation failed before PLC test write."
            )

            result["errors"].extend(
                database_payload_validation["errors"][:10]
            )

            return result

        test_data_tag = result["test_tags"][
            PLCTemporaryTestWriteManager.TEST_BUFFER_PURPOSE
        ]["tag_name"]

        test_data_expression = (
            f"{test_data_tag}"
            f"{{{payload_size}}}"
        )

        try:

            with LogixDriver(
                result["plc"]["ip_address"]
            ) as plc_conn:

                manual_check = (
                    PLCTemporaryTestWriteManager
                    .read_required_bool(

                        plc_conn=plc_conn,

                        tag_name=result["write_plan"][
                            "machine_in_manual_tag"
                        ],

                        label="Machine In Manual"

                    )
                )

                result["steps"].append(
                    manual_check
                )

                if not manual_check["ok"]:

                    result["errors"].append(
                        manual_check["message"]
                    )

                    return result

                write_result = (
                    PLCTemporaryTestWriteManager
                    .write_tag(

                        plc_conn=plc_conn,

                        tag_name=test_data_expression,

                        value=recipe_array,

                        label="Write Direct Test Recipe Data Buffer"

                    )
                )

                result["steps"].append(
                    write_result
                )

                if not write_result["ok"]:

                    result["errors"].append(
                        write_result["message"]
                    )

                    return result

                result["executed"] = True

                readback_result = (
                    PLCTemporaryTestWriteManager
                    .read_tag(

                        plc_conn=plc_conn,

                        tag_name=test_data_expression,

                        label="Read Back Direct Test Recipe Data Buffer"

                    )
                )

                result["steps"].append(
                    readback_result
                )

                if not readback_result["ok"]:

                    result["errors"].append(
                        readback_result["message"]
                    )

                    return result

                readback_payload = (
                    PLCTemporaryTestWriteManager
                    .normalize_payload(

                        readback_result["value"],

                        payload_size

                    )
                )

                if readback_payload is None:

                    result["errors"].append(
                        f"PLC test buffer readback did not return {payload_size} values."
                    )

                    return result

                plc_payload_validation = (
                    PLCDownloadPreparationManager
                    .validate_payload_values(

                        recipe_values=values,

                        payload_values=readback_payload

                    )
                )

                validation_step = {

                    "label": "Validate PLC Test Buffer Min Max",

                    "tag_name": test_data_expression,

                    "action": "VALIDATE",

                    "ok": plc_payload_validation["valid"],

                    "value": (
                        f"{plc_payload_validation['checked_parameters']} "
                        "parameters checked"
                    ),

                    "message": (
                        "OK"
                        if plc_payload_validation["valid"]
                        else
                        "PLC test buffer readback has invalid parameter values."
                    )

                }

                result["steps"].append(
                    validation_step
                )

                if not plc_payload_validation["valid"]:

                    result["errors"].append(
                        "PLC test buffer readback validation failed."
                    )

                    result["errors"].extend(
                        plc_payload_validation["errors"][:10]
                    )

                    return result

                result["payload_compare"] = (
                    PLCTemporaryTestWriteManager
                    .compare_payloads(

                        expected=recipe_array,

                        actual=readback_payload

                    )
                )

                compare_step = {

                    "label": "Compare PLC Test Buffer With Recipe Payload",

                    "tag_name": test_data_expression,

                    "action": "COMPARE",

                    "ok": result["payload_compare"]["matched"],

                    "value": (
                        "MATCHED"
                        if result["payload_compare"]["matched"]
                        else
                        result["payload_compare"]["mismatch_count"]
                    ),

                    "message": (
                        "OK"
                        if result["payload_compare"]["matched"]
                        else
                        "PLC test buffer readback does not match recipe payload."
                    )

                }

                result["steps"].append(
                    compare_step
                )

                if not result["payload_compare"]["matched"]:

                    result["errors"].append(
                        "PLC test buffer compare failed."
                    )

                    return result

                result["ready"] = True

                result["status"] = "SUCCESS"

                result["warnings"].append(
                    "Direct test wrote only the configured TEST_RECIPE_DATA "
                    "PLC tag. Download request, acknowledgement, complete, "
                    "and production recipe buffer tags were not used."
                )

                return result

        except Exception as exc:

            result["errors"].append(
                f"PLC direct test buffer write failed: {exc}"
            )

            return result

        finally:

            if (
                result.get(
                    "recipe"
                )
                and
                (
                    result["executed"]
                    or
                    result["steps"]
                )
            ):

                PLCTemporaryTestWriteManager.log_audit(

                    result=result,

                    username=username,

                    user_role=user_role

                )

    @staticmethod
    def get_required_test_tags(

        recipe

    ):

        result = {

            "tags": {},

            "errors": []

        }

        payload_size = (
            PLCDownloadPreparationManager
            .get_payload_size_for_recipe(recipe)
        )

        if not payload_size:

            result["errors"].append(
                "Recipe data array size is not configured for this machine/stage."
            )

            return result

        test_data = (
            PLCTagManager
            .get_tag_by_purpose(

                machine_id=recipe[
                    "machine_id"
                ],

                stage_id=recipe[
                    "stage_id"
                ],

                tag_purpose=PLCTemporaryTestWriteManager.TEST_BUFFER_PURPOSE

            )
        )

        if not test_data:

            result["errors"].append(
                "TEST_RECIPE_DATA PLC tag is not configured."
            )

            return result

        tag_type = (
            test_data.get(
                "tag_type"
            )
            or
            ""
        ).upper()

        if tag_type != "REAL":

            result["errors"].append(
                "TEST_RECIPE_DATA must be configured as REAL."
            )

        if test_data["is_array"] != 1:

            result["errors"].append(
                "TEST_RECIPE_DATA must be configured as an array."
            )

        array_size = (
            test_data["array_size"]
            or
            0
        )

        if array_size < payload_size:

            result["errors"].append(
                f"TEST_RECIPE_DATA array size must be at least {payload_size}."
            )

        result["tags"][
            PLCTemporaryTestWriteManager.TEST_BUFFER_PURPOSE
        ] = test_data

        return result

    @staticmethod
    def build_recipe_array(

        values,

        payload_size

    ):

        recipe_array = [
            0.0
            for _ in range(
                payload_size
            )
        ]

        for row in values:

            plc_index = row[
                "plc_array_index"
            ]

            if plc_index is None:

                continue

            try:

                plc_index = int(
                    plc_index
                )

                parameter_value = float(
                    row[
                        "parameter_value"
                    ]
                )

            except Exception:

                continue

            if (
                plc_index < 0
                or
                plc_index >= payload_size
            ):

                continue

            recipe_array[
                plc_index
            ] = parameter_value

        return recipe_array

    @staticmethod
    def normalize_payload(

        value,

        payload_size

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
        ) < payload_size:

            return None

        return payload[
            :payload_size
        ]

    @staticmethod
    def read_required_bool(

        plc_conn,

        tag_name,

        label

    ):

        read_result = (
            PLCTemporaryTestWriteManager
            .read_tag(

                plc_conn=plc_conn,

                tag_name=tag_name,

                label=label

            )
        )

        if not read_result["ok"]:

            return read_result

        if not PLCDownloadPreparationManager.is_true_value(
            read_result["value"]
        ):

            read_result["ok"] = False

            read_result["message"] = (
                f"{label} is not TRUE. "
                f"Actual value: {read_result['value']}"
            )

        return read_result

    @staticmethod
    def read_tag(

        plc_conn,

        tag_name,

        label

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

        ok = (
            read_result is not None
            and
            not error
        )

        return {

            "label": label,

            "tag_name": tag_name,

            "action": "READ",

            "ok": ok,

            "value": value,

            "message": (
                "OK"
                if ok
                else
                f"{label} read failed: {error}"
            )

        }

    @staticmethod
    def write_tag(

        plc_conn,

        tag_name,

        value,

        label

    ):

        write_result = plc_conn.write(
            (
                tag_name,
                value
            )
        )

        error = getattr(
            write_result,
            "error",
            None
        )

        ok = (
            write_result is not None
            and
            not error
            and
            bool(
                write_result
            )
        )

        return {

            "label": label,

            "tag_name": tag_name,

            "action": "WRITE",

            "ok": ok,

            "value": (
                value
                if not isinstance(
                    value,
                    list
                )
                else
                f"Array[{len(value)}]"
            ),

            "message": (
                "OK"
                if ok
                else
                f"{label} write failed: {error}"
            )

        }

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

        if actual is None:

            result["matched"] = False

            result["mismatch_count"] = len(
                expected
            )

            result["mismatches"].append(
                "Actual PLC test payload is empty."
            )

            return result

        for index, expected_value in enumerate(
            expected
        ):

            try:

                actual_value = float(
                    actual[
                        index
                    ]
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
                ) < 10:

                    result["mismatches"].append(
                        f"Index {index}: expected {expected_value}, "
                        f"actual {actual_value}"
                    )

        return result

    @staticmethod
    def log_audit(

        result,

        username,

        user_role

    ):

        recipe = result.get(
            "recipe"
        )

        plc = result.get(
            "plc"
        )

        if not recipe:

            return

        AuditManager.log_event(

            username=username,

            role=user_role,

            action="PLC_TEMPORARY_TEST_WRITE",

            change_source="PLC_TEST",

            plc_name=plc["plc_name"]
            if plc
            else
            None,

            recipe_code=recipe["recipe_code"],

            recipe_version=recipe["version"],

            old_value=None,

            new_value=result["status"],

            reason=(
                "Direct PLC test buffer write using TEST_RECIPE_DATA only"
            )

        )
