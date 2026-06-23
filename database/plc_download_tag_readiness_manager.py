from database.recipe_manager import (
    RecipeManager
)

from database.database import (
    get_connection
)


class PLCDownloadTagReadinessManager:

    REQUIRED_TAGS = [

        {
            "purpose": "RECIPE_DATA",
            "label": "Recipe Data",
            "expected_type": "REAL",
            "array_required": True,
            "minimum_array_size": 500
        },

        {
            "purpose": "RECIPE_CODE",
            "label": "Recipe Code",
            "expected_type": "STRING",
            "array_required": False,
            "minimum_array_size": None
        },

        {
            "purpose": "DOWNLOAD_ENABLE",
            "label": "Download Enable",
            "expected_type": "BOOL",
            "array_required": False,
            "minimum_array_size": None
        },

        {
            "purpose": "MACHINE_IN_MANUAL",
            "label": "Machine In Manual",
            "expected_type": "BOOL",
            "array_required": False,
            "minimum_array_size": None
        },

        {
            "purpose": "DOWNLOAD_REQUEST",
            "label": "Download Request",
            "expected_type": "BOOL",
            "array_required": False,
            "minimum_array_size": None
        },

        {
            "purpose": "DOWNLOAD_COMPLETE",
            "label": "Download Complete",
            "expected_type": "BOOL",
            "array_required": False,
            "minimum_array_size": None
        }

    ]

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

        for required in PLCDownloadTagReadinessManager.REQUIRED_TAGS:

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

                "expected_type": required["expected_type"],

                "array_required": required["array_required"],

                "minimum_array_size": required["minimum_array_size"],

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

        payload_size=500

    ):

        tag_readiness = (
            PLCDownloadTagReadinessManager
            .check_readiness(
                recipe_id
            )
        )

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

        payload_size=500

    ):

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

        for required in PLCDownloadTagReadinessManager.REQUIRED_TAGS:

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
            required["expected_type"]
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

        if required["array_required"]:

            if tag["is_array"] != 1:

                item["issues"].append(
                    "Tag must be configured as an array."
                )

            array_size = (
                tag["array_size"]
                or
                0
            )

            if array_size < required["minimum_array_size"]:

                item["issues"].append(
                    f"Array size must be at least "
                    f"{required['minimum_array_size']}."
                )

            if (
                tag["array_start_index"] is None
                or
                tag["array_end_index"] is None
            ):

                item["issues"].append(
                    "Array start and end indexes are required."
                )

            elif (
                tag["array_start_index"] > 0
                or
                tag["array_end_index"]
                < required["minimum_array_size"] - 1
            ):

                item["issues"].append(
                    "Array must cover indexes 0 to "
                    f"{required['minimum_array_size'] - 1}."
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
