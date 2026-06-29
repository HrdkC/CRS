from database.recipe_manager import (
    RecipeManager
)

from database.database import (
    get_connection
)
from database.stage_plc_tag_requirement_manager import (
    StagePLCTagRequirementManager
)


class PLCDownloadTagReadinessManager:

    @staticmethod
    def check_readiness(

        recipe_id

    ):

        result = {

            "ready": True,

            "status": "READY",

            "errors": [],

            "warnings": [],

            "tags": []

        }

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                recipe_id
            )
        )

        if not recipe:

            result["ready"] = False

            result["status"] = "BLOCKED"

            result["errors"].append(
                "Recipe Not Found"
            )

            return result

        required_tags = (
            StagePLCTagRequirementManager
            .get_stage_requirements(
                machine_id=recipe[
                    "machine_id"
                ],
                stage_id=recipe[
                    "stage_id"
                ],
                requirement_level=StagePLCTagRequirementManager.LEVEL_REQUIRED,
                active_only=True
            )
        )

        result["required_tags"] = required_tags
        result["payload_size"] = (
            StagePLCTagRequirementManager
            .get_payload_size(
                machine_id=recipe["machine_id"],
                stage_id=recipe["stage_id"],
                default=None
            )
        )

        if not result["payload_size"]:

            result["ready"] = False

            result["status"] = "BLOCKED"

            result["errors"].append(
                "Recipe data array size is not configured for this machine/stage."
            )

        all_tags = (
            PLCDownloadTagReadinessManager
            .get_tags_for_stage(

                machine_id=recipe[
                    "machine_id"
                ],

                stage_id=recipe[
                    "stage_id"
                ]

            )
        )

        for required in required_tags:

            tag = (
                PLCDownloadTagReadinessManager
                .find_tag_for_purpose(

                    all_tags,

                    required["purpose"]

                )
            )

            item = {

                "purpose": required["purpose"],

                "label": required["label"],

                "expected_type": required.get("expected_type"),

                "array_required": bool(required.get("array_required")),

                "minimum_array_size": required.get("minimum_array_size"),

                "array_start_index": required.get("array_start_index"),

                "array_end_index": required.get("array_end_index"),

                "configured": tag is not None,

                "ready": True,

                "tag": tag,

                "issues": []

            }

            if not tag:

                item["ready"] = False

                item["issues"].append(
                    f"{required['label']} tag is not configured."
                )

            else:

                PLCDownloadTagReadinessManager.validate_tag(

                    item=item,

                    tag=tag,

                    required=required

                )

            if not item["ready"]:

                result["ready"] = False

                result["errors"].extend(
                    item["issues"]
                )

            result["tags"].append(
                item
            )

        if result["ready"]:

            result["status"] = "READY"

            result["warnings"].append(
                "All required PLC download tags are configured."
            )

        else:

            result["status"] = "BLOCKED"

        return result

    @staticmethod
    def get_write_plan(

        recipe_id,

        payload_size=None

    ):

        tag_readiness = (
            PLCDownloadTagReadinessManager
            .check_readiness(
                recipe_id
            )
        )

        if payload_size is None:
            payload_size = tag_readiness.get("payload_size")

        return (
            PLCDownloadTagReadinessManager
            .build_write_plan(

                tag_readiness=tag_readiness,

                payload_size=payload_size

            )
        )

    @staticmethod
    def build_write_plan(

        tag_readiness,

        payload_size=None

    ):

        if payload_size is None:
            payload_size = tag_readiness.get("payload_size")

        result = {

            "ready": tag_readiness.get(
                "ready",
                False
            ),

            "status": tag_readiness.get(
                "status",
                "BLOCKED"
            ),

            "errors": list(
                tag_readiness.get(
                    "errors",
                    []
                )
            ),

            "warnings": [],

            "payload_size": payload_size,

            "steps": [],

            "recipe_code_tag": "",

            "recipe_data_tag": "",

            "recipe_data_write_tag": "",

            "download_enable_tag": "",

            "machine_in_manual_tag": "",

            "download_request_tag": "",

            "download_complete_tag": ""

        }

        if not payload_size:

            result["ready"] = False

            result["status"] = "BLOCKED"

            result["errors"].append(
                "Write plan cannot be built because recipe data array size is not configured."
            )

            return result

        if not result["ready"]:

            return result

        tags_by_purpose = {}

        for item in tag_readiness.get(
            "tags",
            []
        ):

            if item.get(
                "tag"
            ):

                tags_by_purpose[
                    item["purpose"]
                ] = item["tag"]

        missing_purposes = []

        for required in tag_readiness.get("required_tags") or []:

            purpose = required[
                "purpose"
            ]

            if purpose not in tags_by_purpose:

                missing_purposes.append(
                    purpose
                )

        if missing_purposes:

            result["ready"] = False

            result["status"] = "BLOCKED"

            result["errors"].append(
                "Write plan cannot be built. Missing purposes: "
                + ", ".join(
                    missing_purposes
                )
            )

            return result

        recipe_data_tag = tags_by_purpose[
            "RECIPE_DATA"
        ]["tag_name"]

        recipe_data_write_tag = (
            f"{recipe_data_tag}"
            f"{{{payload_size}}}"
        )

        result["recipe_code_tag"] = tags_by_purpose[
            "RECIPE_CODE"
        ]["tag_name"]

        result["recipe_data_tag"] = recipe_data_tag

        result["recipe_data_write_tag"] = recipe_data_write_tag

        result["download_enable_tag"] = tags_by_purpose[
            "DOWNLOAD_ENABLE"
        ]["tag_name"]

        result["machine_in_manual_tag"] = tags_by_purpose[
            "MACHINE_IN_MANUAL"
        ]["tag_name"]

        result["download_request_tag"] = tags_by_purpose[
            "DOWNLOAD_REQUEST"
        ]["tag_name"]

        result["download_complete_tag"] = tags_by_purpose[
            "DOWNLOAD_COMPLETE"
        ]["tag_name"]

        result["steps"] = [

            {
                "step_no": 1,
                "action": "READ",
                "purpose": "MACHINE_IN_MANUAL",
                "label": "Confirm machine is in manual mode",
                "tag_name": result["machine_in_manual_tag"],
                "write_expression": result["machine_in_manual_tag"],
                "value_source": "PLC BOOL must be TRUE"
            },

            {
                "step_no": 2,
                "action": "READ",
                "purpose": "DOWNLOAD_ENABLE",
                "label": "Confirm download enable",
                "tag_name": result["download_enable_tag"],
                "write_expression": result["download_enable_tag"],
                "value_source": "PLC BOOL must be TRUE"
            },

            {
                "step_no": 3,
                "action": "WRITE",
                "purpose": "RECIPE_CODE",
                "label": "Write recipe code",
                "tag_name": result["recipe_code_tag"],
                "write_expression": result["recipe_code_tag"],
                "value_source": "Recipe code"
            },

            {
                "step_no": 4,
                "action": "WRITE",
                "purpose": "RECIPE_DATA",
                "label": "Write recipe payload array",
                "tag_name": result["recipe_data_tag"],
                "write_expression": result["recipe_data_write_tag"],
                "value_source": f"{payload_size} REAL values"
            },

            {
                "step_no": 5,
                "action": "READ",
                "purpose": "RECIPE_DATA",
                "label": "Verify PLC payload values",
                "tag_name": result["recipe_data_tag"],
                "write_expression": result["recipe_data_write_tag"],
                "value_source": "PLC actual values within min/max"
            },

            {
                "step_no": 6,
                "action": "WRITE",
                "purpose": "DOWNLOAD_REQUEST",
                "label": "Set download request",
                "tag_name": result["download_request_tag"],
                "write_expression": result["download_request_tag"],
                "value_source": "TRUE"
            },

            {
                "step_no": 7,
                "action": "CHECK",
                "purpose": "DOWNLOAD_COMPLETE",
                "label": "Confirm download complete",
                "tag_name": result["download_complete_tag"],
                "write_expression": result["download_complete_tag"],
                "value_source": "PLC BOOL confirmation"
            }

        ]

        result["warnings"].append(
            "PLC write plan is generated from configured PLC tags. "
            "Real PLC write remains disabled."
        )

        return result

    @staticmethod
    def get_tags_for_stage(

        machine_id,

        stage_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM plc_tags

            WHERE

                machine_id = ?

                AND stage_id = ?

            ORDER BY
                tag_name
            """,
            (
                machine_id,
                stage_id
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [

            dict(row)

            for row in rows

        ]

    @staticmethod
    def find_tag_for_purpose(

        tags,

        purpose

    ):

        purpose_upper = purpose.upper()

        purpose_names = (
            PLCDownloadTagReadinessManager
            .get_purpose_names(
                purpose_upper
            )
        )

        for tag in tags:

            tag_purpose = (
                tag.get(
                    "tag_purpose"
                )
                or
                ""
            ).upper()

            tag_type = (
                tag.get(
                    "tag_type"
                )
                or
                ""
            ).upper()

            if tag_purpose in purpose_names:

                return tag

            if tag_type in purpose_names:

                return tag

        expected_names = (
            PLCDownloadTagReadinessManager
            .get_expected_names(
                purpose_upper
            )
        )

        for tag in tags:

            tag_name = (
                tag.get(
                    "tag_name"
                )
                or
                ""
            ).upper()

            if tag_name in expected_names:

                return tag

        return None

    @staticmethod
    def validate_tag(

        item,

        tag,

        required

    ):

        tag_type = (
            tag.get(
                "tag_type"
            )
            or
            ""
        ).upper()

        expected_type = (
            required.get("expected_type")
            or
            ""
        ).upper()

        purpose_names = (
            PLCDownloadTagReadinessManager
            .get_purpose_names(
                required["purpose"]
            )
        )

        if (
            expected_type
            and
            tag_type
            and
            tag_type != expected_type
            and
            tag_type not in purpose_names
        ):

            item["issues"].append(
                f"Expected type {expected_type}, found {tag_type}."
            )

        if required.get("array_required"):

            if tag["is_array"] != 1:

                item["issues"].append(
                    "Tag must be configured as an array."
                )

            array_size = (
                tag["array_size"]
                or
                0
            )

            minimum_array_size = required.get("minimum_array_size") or 0

            if minimum_array_size and array_size < minimum_array_size:

                item["issues"].append(
                    f"Array size must be at least "
                    f"{minimum_array_size}."
                )

            if (
                tag["array_start_index"] is None
                or
                tag["array_end_index"] is None
            ):

                item["issues"].append(
                    "Array start and end indexes are required."
                )

            else:

                required_start = required.get("array_start_index")
                required_end = required.get("array_end_index")

                if required_start is None:
                    required_start = 0

                if required_end is None and minimum_array_size:
                    required_end = required_start + minimum_array_size - 1

                if (
                    required_end is not None
                    and
                    (
                        tag["array_start_index"] > required_start
                        or
                        tag["array_end_index"] < required_end
                    )
                ):

                    item["issues"].append(
                        "Array must cover indexes "
                        f"{required_start} to {required_end}."
                    )

        else:

            if tag["is_array"] == 1:

                item["issues"].append(
                    "Tag should not be configured as an array."
                )

        if item["issues"]:

            item["ready"] = False

    @staticmethod
    def get_expected_names(

        purpose

    ):

        mapping = {

            "RECIPE_DATA": [
                "CRS_RECIPE_DATA"
            ],

            "TEST_RECIPE_DATA": [
                "CRS_TEST_RECIPE_DATA"
            ],

            "RECIPE_CODE": [
                "CRS_RECIPE_CODE"
            ],

            "DOWNLOAD_ENABLE": [
                "CRS_DOWNLOAD_ENABLE"
            ],

            "DOWNLOAD_REQUEST": [
                "CRS_DOWNLOAD_REQUEST"
            ],

            "MACHINE_IN_MANUAL": [
                "MACHINE_IN_MANUAL",
                "CRS_MACHINE_IN_MANUAL",
                "CRS_MACHINE_MANUAL",
                "MACHINE_MANUAL"
            ],

            "DOWNLOAD_COMPLETE": [
                "CRS_DOWNLOAD_COMPLETE"
            ],

            "DOWNLOAD_ACK": [
                "CRS_DOWNLOAD_ACK"
            ],

            "DOWNLOAD_BUSY": [
                "CRS_DOWNLOAD_BUSY"
            ],

            "DOWNLOAD_ERROR": [
                "CRS_DOWNLOAD_ERROR"
            ],

            "DOWNLOAD_RESULT": [
                "CRS_DOWNLOAD_RESULT"
            ],

            "DOWNLOAD_OS": [
                "CRS_DOWNLOAD_OS"
            ],

            "LAST_DOWNLOAD_TIME": [
                "CRS_LAST_DOWNLOAD_TIME"
            ],

            "LAST_DOWNLOAD_USER": [
                "CRS_LAST_DOWNLOAD_USER"
            ]

        }

        return mapping.get(
            purpose,
            []
        )

    @staticmethod
    def get_purpose_names(

        purpose

    ):

        mapping = {

            "MACHINE_IN_MANUAL": [
                "MACHINE_IN_MANUAL",
                "MACHINE_MANUAL",
                "MANUAL_MODE",
                "PLC_MANUAL_MODE"
            ]

        }

        purpose_upper = (
            purpose
            or
            ""
        ).upper()

        return mapping.get(
            purpose_upper,
            [
                purpose_upper
            ]
        )
