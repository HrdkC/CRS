from database.recipe_download_eligibility_manager import (
    RecipeDownloadEligibilityManager
)

from database.recipe_validation_manager import (
    RecipeValidationManager
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

from database.plc_download_tag_readiness_manager import (
    PLCDownloadTagReadinessManager
)
from database.stage_plc_tag_requirement_manager import (
    StagePLCTagRequirementManager
)

from database.plc_connection_errors import (
    format_plc_connection_failure,
)

from database.database import (
    get_connection
)

from pycomm3 import (
    LogixDriver
)


class PLCDownloadPreparationManager:

    PAYLOAD_SIZE = None

    @staticmethod
    def get_payload_size_for_recipe(recipe):
        if not recipe:
            return PLCDownloadPreparationManager.PAYLOAD_SIZE
        return (
            StagePLCTagRequirementManager
            .get_payload_size(
                machine_id=recipe["machine_id"],
                stage_id=recipe["stage_id"],
                default=None,
            )
        )

    @staticmethod
    def get_available_plcs(

        recipe_id

    ):

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                recipe_id
            )
        )

        if not recipe:

            return []

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                p.*,

                m.machine_code,

                s.stage_type

            FROM plc_registry p

            LEFT JOIN machine_stages s

                ON s.id = p.machine_stage_id

            LEFT JOIN tbm_machines m

                ON m.id = s.machine_id

            WHERE

                p.machine_stage_id = ?

                AND p.active = 1

            ORDER BY
                p.plc_name
            """,
            (
                recipe["stage_id"],
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [

            dict(row)

            for row in rows

        ]

    @staticmethod
    def dry_run(

        recipe_id,

        plc_id

    ):

        result = {

            "ready": True,

            "errors": [],

            "warnings": [],

            "recipe": None,

            "plc": None,

            "payload_summary": {},

            "phase_summary": {},

            "parameter_validation": {},

            "tag_readiness": {},

            "write_plan": {}

        }

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                recipe_id
            )
        )

        if not recipe:

            result["ready"] = False

            result["errors"].append(
                "Recipe Not Found"
            )

            return result

        result["recipe"] = recipe

        payload_size = (
            PLCDownloadPreparationManager
            .get_payload_size_for_recipe(recipe)
        )

        parameter_validation = (
            RecipeValidationManager
            .validate_recipe(

                recipe_id,

                require_released=False

            )
        )

        result["parameter_validation"] = parameter_validation

        if not parameter_validation["valid"]:

            result["ready"] = False

            for error in parameter_validation["errors"]:

                if error not in result["errors"]:

                    result["errors"].append(
                        error
                    )

        eligibility = (
            RecipeDownloadEligibilityManager
            .check_eligibility(
                recipe_id
            )
        )

        if not eligibility["eligible"]:

            result["ready"] = False

            for error in eligibility["errors"]:

                if error not in result["errors"]:

                    result["errors"].append(
                        error
                    )

        plc = (
            PLCDownloadPreparationManager
            .get_plc_for_recipe(
                recipe,
                plc_id
            )
        )

        if not plc:

            result["ready"] = False

            result["errors"].append(
                "Selected PLC is not active for this recipe stage."
            )

        else:

            result["plc"] = plc

        tag_readiness = (
            PLCDownloadTagReadinessManager
            .check_readiness(
                recipe_id
            )
        )

        result["tag_readiness"] = tag_readiness

        write_plan = (
            PLCDownloadTagReadinessManager
            .build_write_plan(

                tag_readiness=tag_readiness,

                payload_size=payload_size

            )
        )

        result["write_plan"] = write_plan

        if not tag_readiness["ready"]:

            result["ready"] = False

            for error in tag_readiness["errors"]:

                if error not in result["errors"]:

                    result["errors"].append(
                        error
                    )

        if not write_plan["ready"]:

            result["ready"] = False

            for error in write_plan["errors"]:

                if error not in result["errors"]:

                    result["errors"].append(
                        error
                    )

        values = (
            RecipeParameterValueManager
            .get_recipe_values(
                recipe_id
            )
        )

        used_indexes = set()

        duplicate_indexes = []

        missing_indexes = []

        out_of_range_indexes = []

        mapped_count = 0

        non_zero_count = 0

        for row in values:

            plc_index = row[
                "plc_array_index"
            ]

            if plc_index is None:

                missing_indexes.append(
                    row["tag_index"]
                )

                continue

            try:

                plc_index = int(
                    plc_index
                )

            except Exception:

                out_of_range_indexes.append(
                    row["tag_index"]
                )

                continue

            if (
                plc_index < 0
                or
                plc_index >= payload_size
            ):

                out_of_range_indexes.append(
                    row["tag_index"]
                )

                continue

            if plc_index in used_indexes:

                duplicate_indexes.append(
                    plc_index
                )

            used_indexes.add(
                plc_index
            )

            mapped_count += 1

            try:

                numeric_value = float(
                    row["parameter_value"]
                )

            except Exception:

                continue

            if numeric_value != 0:

                non_zero_count += 1

        if missing_indexes:

            result["ready"] = False

            result["errors"].append(
                f"{len(missing_indexes)} parameters have no PLC array index."
            )

        if out_of_range_indexes:

            result["ready"] = False

            result["errors"].append(
                f"{len(out_of_range_indexes)} parameters have invalid "
                f"PLC array index."
            )

        if duplicate_indexes:

            result["ready"] = False

            result["errors"].append(
                "Duplicate PLC array indexes found: "
                + ", ".join(
                    [
                        str(index)
                        for index in sorted(
                            set(duplicate_indexes)
                        )
                    ][:10]
                )
            )

        if not values:

            result["ready"] = False

            result["errors"].append(
                "No recipe parameter values found."
            )

        phase_rows = (
            RecipePhaseControlManager
            .get_recipe_phase_control(
                recipe_id
            )
        )

        result["payload_summary"] = {

            "payload_size":
            payload_size,

            "total_parameters":
            len(values),

            "mapped_parameters":
            mapped_count,

            "non_zero_values":
            non_zero_count,

            "minimum_plc_array_index":
            min(used_indexes)
            if used_indexes
            else
            "-",

            "maximum_plc_array_index":
            max(used_indexes)
            if used_indexes
            else
            "-"

        }

        result["phase_summary"] = {

            "total_phase_rows":
            len(phase_rows),

            "ready_phase_rows":
            len(
                [
                    row
                    for row in phase_rows
                    if row["phase_control_id"]
                    and row["sequence_no"] is not None
                ]
            )

        }

        if result["ready"]:

            result["warnings"].append(
                "Dry run passed. Real PLC write remains disabled "
                "until final download workflow is approved."
            )

        return result

    @staticmethod
    def check_manual_mode(

        recipe_id,

        plc_id

    ):

        result = {

            "checked": True,

            "connected": False,

            "ready": False,

            "status": "BLOCKED",

            "errors": [],

            "warnings": [],

            "recipe": None,

            "plc": None,

            "tag_name": "",

            "actual_value": None,

            "read_error": ""

        }

        recipe = (
            RecipeManager
            .get_recipe_by_id(
                recipe_id
            )
        )

        if not recipe:

            result["errors"].append(
                "Recipe Not Found"
            )

            return result

        result["recipe"] = recipe

        payload_size = (
            PLCDownloadPreparationManager
            .get_payload_size_for_recipe(recipe)
        )

        plc = (
            PLCDownloadPreparationManager
            .get_plc_for_recipe(
                recipe,
                plc_id
            )
        )

        if not plc:

            result["errors"].append(
                "Selected PLC is not active for this recipe stage."
            )

            return result

        result["plc"] = plc

        write_plan = (
            PLCDownloadTagReadinessManager
            .get_write_plan(

                recipe_id=recipe_id,

                payload_size=payload_size

            )
        )

        tag_name = write_plan.get(
            "machine_in_manual_tag",
            ""
        )

        result["tag_name"] = tag_name

        if not tag_name:

            result["errors"].append(
                "Machine In Manual tag is not configured."
            )

            return result

        try:

            with LogixDriver(
                plc["ip_address"]
            ) as plc_conn:

                read_result = plc_conn.read(
                    tag_name
                )

            if read_result is None:

                result["errors"].append(
                    "PLC manual mode tag read returned no result."
                )

                return result

            result["connected"] = True

            result["actual_value"] = getattr(
                read_result,
                "value",
                None
            )

            read_error = getattr(
                read_result,
                "error",
                None
            )

            if read_error:

                result["read_error"] = str(
                    read_error
                )

                result["errors"].append(
                    f"PLC manual mode tag read failed: {read_error}"
                )

                return result

            if (
                PLCDownloadPreparationManager
                .is_true_value(
                    result["actual_value"]
                )
            ):

                result["ready"] = True

                result["status"] = "READY"

                result["warnings"].append(
                    "Machine is in manual mode. Recipe write can be enabled after all other checks pass."
                )

            else:

                result["errors"].append(
                    "Machine is not in manual mode. Recipe write is disabled."
                )

        except Exception as ex:

            result["errors"].append(
                format_plc_connection_failure(
                    plc=plc,
                    detail=ex,
                    action="PLC manual mode read",
                )
            )

        return result

    @staticmethod
    def is_true_value(

        value

    ):

        if isinstance(
            value,
            bool
        ):

            return value

        if isinstance(
            value,
            (int, float)
        ):

            return value == 1

        if isinstance(
            value,
            str
        ):

            return value.strip().upper() in [
                "1",
                "TRUE",
                "ON",
                "YES"
            ]

        return False

    @staticmethod
    def validate_payload_values(

        recipe_values,

        payload_values

    ):

        result = {

            "valid": True,

            "errors": [],

            "checked_parameters": 0,

            "invalid_parameters": 0

        }

        if payload_values is None:

            result["valid"] = False

            result["errors"].append(
                "PLC payload values are empty."
            )

            return result

        try:

            payload_length = len(
                payload_values
            )

        except Exception:

            result["valid"] = False

            result["errors"].append(
                "PLC payload values are not readable as an array."
            )

            return result

        for row in recipe_values:

            plc_index = row[
                "plc_array_index"
            ]

            if plc_index is None:

                result["valid"] = False

                result["invalid_parameters"] += 1

                result["errors"].append(
                    f"Tag {row['tag_index']} has no PLC array index."
                )

                continue

            try:

                plc_index = int(
                    plc_index
                )

            except Exception:

                result["valid"] = False

                result["invalid_parameters"] += 1

                result["errors"].append(
                    f"Tag {row['tag_index']} has invalid PLC array index."
                )

                continue

            if (
                plc_index < 0
                or
                plc_index >= payload_length
            ):

                result["valid"] = False

                result["invalid_parameters"] += 1

                result["errors"].append(
                    f"Tag {row['tag_index']} PLC array index "
                    f"{plc_index} is outside payload size."
                )

                continue

            try:

                actual_value = float(
                    payload_values[
                        plc_index
                    ]
                )

            except Exception:

                result["valid"] = False

                result["invalid_parameters"] += 1

                result["errors"].append(
                    f"Tag {row['tag_index']} PLC actual value is not numeric."
                )

                continue

            min_value = row[
                "min_value"
            ]

            max_value = row[
                "max_value"
            ]

            try:

                min_numeric = (
                    float(min_value)
                    if min_value is not None
                    else
                    None
                )

                max_numeric = (
                    float(max_value)
                    if max_value is not None
                    else
                    None
                )

            except Exception:

                result["valid"] = False

                result["invalid_parameters"] += 1

                result["errors"].append(
                    f"Tag {row['tag_index']} has invalid min/max configuration."
                )

                continue

            parameter_valid = True

            if (
                min_numeric is not None
                and
                actual_value < min_numeric
            ):

                parameter_valid = False

                result["errors"].append(
                    f"Tag {row['tag_index']} PLC actual value below minimum "
                    f"({actual_value} < {min_numeric})."
                )

            if (
                max_numeric is not None
                and
                actual_value > max_numeric
            ):

                parameter_valid = False

                result["errors"].append(
                    f"Tag {row['tag_index']} PLC actual value above maximum "
                    f"({actual_value} > {max_numeric})."
                )

            if parameter_valid:

                result["checked_parameters"] += 1

            else:

                result["valid"] = False

                result["invalid_parameters"] += 1

        return result

    @staticmethod
    def get_plc_for_recipe(

        recipe,

        plc_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                p.*,

                m.machine_code,

                s.stage_type

            FROM plc_registry p

            LEFT JOIN machine_stages s

                ON s.id = p.machine_stage_id

            LEFT JOIN tbm_machines m

                ON m.id = s.machine_id

            WHERE

                p.id = ?

                AND p.machine_stage_id = ?

                AND p.active = 1
            """,
            (
                plc_id,
                recipe["stage_id"]
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None
