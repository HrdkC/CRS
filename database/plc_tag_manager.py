from database.database import (
    get_connection
)


class PLCTagManager:

    @staticmethod
    def create_tag(

        machine_id,

        stage_id,

        tag_name,

        tag_type="",

        is_array=0,

        array_size=None,

        array_start_index=None,

        array_end_index=None,

        description="",

        created_by=None,

        tag_purpose=None

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO plc_tags
            (

                machine_id,

                stage_id,

                tag_name,

                tag_type,

                is_array,

                array_size,

                array_start_index,

                array_end_index,

                description,

                created_by,

                tag_purpose

            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (

                machine_id,

                stage_id,

                tag_name,

                tag_type,

                is_array,

                array_size,

                array_start_index,

                array_end_index,

                description,

                created_by,

                tag_purpose

            )
        )

        tag_id = cursor.lastrowid

        conn.commit()

        conn.close()

        return tag_id

    @staticmethod
    def search_tags(

        machine_id,

        stage_id,

        search_text="",

        bool_only=False

    ):

        conn = get_connection()

        cursor = conn.cursor()

        conditions = [

            "machine_id = ?",

            "stage_id = ?"

        ]

        params = [

            machine_id,

            stage_id

        ]

        if search_text:

            conditions.append(
                """
                (
                    UPPER(tag_name) LIKE UPPER(?)
                    OR UPPER(COALESCE(tag_type, '')) LIKE UPPER(?)
                    OR UPPER(COALESCE(tag_purpose, '')) LIKE UPPER(?)
                    OR UPPER(COALESCE(description, '')) LIKE UPPER(?)
                )
                """
            )

            like_text = f"%{search_text}%"

            params.extend(
                [
                    like_text,
                    like_text,
                    like_text,
                    like_text
                ]
            )

        if bool_only:

            conditions.append(
                "UPPER(COALESCE(tag_type, '')) = 'BOOL'"
            )

        cursor.execute(
            f"""
            SELECT *

            FROM plc_tags

            WHERE
                {' AND '.join(conditions)}

            ORDER BY tag_name
            """,
            tuple(
                params
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    @staticmethod
    def get_search_hint_for_purpose(

        tag_purpose

    ):

        mapping = {

            "RECIPE_DATA": "Recipe_Data",

            "RECIPE_CODE": "Recipe_Code",

            "TEST_RECIPE_DATA": "CRS_Test_Recipe_Data",

            "DOWNLOAD_ENABLE": "Download_Enable",

            "MACHINE_IN_MANUAL": "Manual",

            "DOWNLOAD_REQUEST": "Download_Request",

            "DOWNLOAD_COMPLETE": "Download_Complete",

            "PHASE_CONTROL_STRING": "Phase_Cntrl_String",

            "PHASE_STOP_STRING": "Phase_Cntrl_Stop",

            "PHASE_POSITION_STRING": "Phase_Cntrl_Position",

            "CAP_STRIP_PHASE_CONTROL_STRING": "Phase_Cntrl_String_CapSd",

            "CAP_STRIP_PHASE_STOP_STRING": "Phase_Cntrl_Stop_String_CapSd",

            "BT_PHASE_CONTROL_STRING": "Phase_Cntrl_String",

            "BT_PHASE_STOP_STRING": "Phase_Cntrl_Stop_String",

            "BT_PHASE_POSITION_STRING": "Phase_Cntrl_Pos_String",

            "DOWNLOAD_ACK": "Download_Ack",

            "DOWNLOAD_BUSY": "Download_Busy",

            "DOWNLOAD_ERROR": "Download_Error",

            "DOWNLOAD_RESULT": "Download_Result",

            "DOWNLOAD_OS": "Download_OS",

            "LAST_DOWNLOAD_TIME": "Last_Download_Time",

            "LAST_DOWNLOAD_USER": "Last_Download_User"

        }

        return mapping.get(
            (
                tag_purpose
                or
                ""
            ).upper(),
            ""
        )

    @staticmethod
    def get_default_tag_name_for_purpose(

        tag_purpose

    ):

        mapping = {

            "RECIPE_DATA": "CRS_Recipe_Data",

            "RECIPE_CODE": "CRS_Recipe_Code",

            "TEST_RECIPE_DATA": "CRS_Test_Recipe_Data",

            "DOWNLOAD_ENABLE": "CRS_Download_Enable",

            "MACHINE_IN_MANUAL": "Machine_In_Manual",

            "DOWNLOAD_REQUEST": "CRS_Download_Request",

            "DOWNLOAD_COMPLETE": "CRS_Download_Complete",

            "PHASE_CONTROL_STRING": "CRS_Phase_Cntrl_String",

            "PHASE_STOP_STRING": "CRS_Phase_Cntrl_Stop_String",

            "PHASE_POSITION_STRING": "CRS_Phase_Cntrl_Position_String",

            "CAP_STRIP_PHASE_CONTROL_STRING": "CRS_Phase_Cntrl_String_CapSd",

            "CAP_STRIP_PHASE_STOP_STRING": "CRS_Phase_Cntrl_Stop_String_CapSd",

            "BT_PHASE_CONTROL_STRING": "CRS_Phase_Cntrl_String",

            "BT_PHASE_STOP_STRING": "CRS_Phase_Cntrl_Stop_String",

            "BT_PHASE_POSITION_STRING": "CRS_Phase_Cntrl_Pos_String",

            "DOWNLOAD_ACK": "CRS_Download_Ack",

            "DOWNLOAD_BUSY": "CRS_Download_Busy",

            "DOWNLOAD_ERROR": "CRS_Download_Error",

            "DOWNLOAD_RESULT": "CRS_Download_Result",

            "DOWNLOAD_OS": "CRS_Download_OS",

            "LAST_DOWNLOAD_TIME": "CRS_Last_Download_Time",

            "LAST_DOWNLOAD_USER": "CRS_Last_Download_User"

        }

        return mapping.get(
            (
                tag_purpose
                or
                ""
            ).upper(),
            ""
        )

    @staticmethod
    def set_tag_purpose(

        tag_id,

        tag_purpose

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM plc_tags

            WHERE id = ?
            """,
            (
                tag_id,
            )
        )

        row = cursor.fetchone()

        if not row:

            conn.close()

            return (
                False,
                "PLC tag not found"
            )

        tag_purpose = (
            tag_purpose
            or
            ""
        ).strip().upper()

        if not tag_purpose:

            conn.close()

            return (
                False,
                "PLC tag purpose is required"
            )

        cursor.execute(
            """
            UPDATE plc_tags

            SET tag_purpose = NULL

            WHERE
                machine_id = ?
                AND stage_id = ?
                AND tag_purpose = ?
                AND id != ?
            """,
            (
                row["machine_id"],
                row["stage_id"],
                tag_purpose,
                tag_id
            )
        )

        cursor.execute(
            """
            UPDATE plc_tags

            SET tag_purpose = ?

            WHERE id = ?
            """,
            (
                tag_purpose,
                tag_id
            )
        )

        conn.commit()

        conn.close()

        return (
            True,
            f"{row['tag_name']} selected for {tag_purpose}"
        )

    @staticmethod
    def upsert_tag(

        machine_id,

        stage_id,

        tag_name,

        tag_type="",

        is_array=0,

        array_size=None,

        array_start_index=None,

        array_end_index=None,

        description="",

        created_by=None,

        tag_purpose=None

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
                AND UPPER(tag_name) = UPPER(?)
            """,
            (
                machine_id,
                stage_id,
                tag_name
            )
        )

        row = cursor.fetchone()

        if row:

            tag_id = row[
                "id"
            ]

            cursor.execute(
                """
                UPDATE plc_tags

                SET
                    tag_type = ?,
                    is_array = ?,
                    array_size = ?,
                    array_start_index = ?,
                    array_end_index = ?,
                    description = ?

                WHERE id = ?
                """,
                (
                    tag_type,
                    is_array,
                    array_size,
                    array_start_index,
                    array_end_index,
                    description,
                    tag_id
                )
            )

            created = False

        else:

            cursor.execute(
                """
                INSERT INTO plc_tags
                (
                    machine_id,
                    stage_id,
                    tag_name,
                    tag_type,
                    is_array,
                    array_size,
                    array_start_index,
                    array_end_index,
                    description,
                    created_by
                )
                VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    machine_id,
                    stage_id,
                    tag_name,
                    tag_type,
                    is_array,
                    array_size,
                    array_start_index,
                    array_end_index,
                    description,
                    created_by
                )
            )

            tag_id = cursor.lastrowid

            created = True

        conn.commit()

        conn.close()

        if tag_purpose:

            PLCTagManager.set_tag_purpose(

                tag_id=tag_id,

                tag_purpose=tag_purpose

            )

        return (
            tag_id,
            created
        )
        
    @staticmethod
    def get_tag_by_id(

        tag_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM plc_tags

            WHERE id = ?
            """,
            (
                tag_id,
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None
    
    @staticmethod
    def get_tag_by_purpose(

        machine_id,

        stage_id,

        tag_purpose

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

                AND tag_purpose = ?
            """,
            (

                machine_id,

                stage_id,

                tag_purpose

            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None
    
    @staticmethod
    def get_tag_by_type(

        machine_id,

        stage_id,

        tag_type

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

                AND tag_type = ?
            """,
            (
                machine_id,

                stage_id,

                tag_type
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None



    @staticmethod
    def _to_int_or_none(value):

        if value in (None, ""):

            return None

        try:

            return int(
                float(
                    value
                )
            )

        except Exception:

            return None

    @staticmethod
    def _truthy(value):

        return str(
            value
            or
            "0"
        ).strip().lower() in {
            "1",
            "true",
            "yes",
            "on"
        }

    @staticmethod
    def _clean_tag_config(row):

        tag_name = str(
            row.get("tag_name")
            or
            ""
        ).strip()

        tag_type = str(
            row.get("tag_type")
            or
            ""
        ).strip().upper()

        tag_purpose = str(
            row.get("tag_purpose")
            or
            ""
        ).strip().upper()

        is_array = 1 if PLCTagManager._truthy(
            row.get("is_array")
        ) else 0

        array_size = PLCTagManager._to_int_or_none(
            row.get("array_size")
        )

        array_start_index = PLCTagManager._to_int_or_none(
            row.get("array_start_index")
        )

        array_end_index = PLCTagManager._to_int_or_none(
            row.get("array_end_index")
        )

        if is_array:

            if array_size is None and array_start_index is not None and array_end_index is not None:

                array_size = (array_end_index - array_start_index) + 1

            if array_size and array_start_index is None:

                array_start_index = 0

            if array_size and array_end_index is None:

                array_end_index = (array_start_index or 0) + array_size - 1

        else:

            array_size = None
            array_start_index = None
            array_end_index = None

        return {
            "id": PLCTagManager._to_int_or_none(
                row.get("id")
            ),
            "tag_name": tag_name,
            "tag_type": tag_type,
            "is_array": is_array,
            "array_size": array_size,
            "array_start_index": array_start_index,
            "array_end_index": array_end_index,
            "description": str(
                row.get("description")
                or
                ""
            ).strip(),
            "tag_purpose": tag_purpose or None
        }

    @staticmethod
    def _validate_tag_config(row, stage_requirements=None):

        errors = []

        tag_name = row.get("tag_name") or ""
        tag_type = row.get("tag_type") or ""
        tag_purpose = row.get("tag_purpose") or ""
        is_array = int(row.get("is_array") or 0)
        array_size = row.get("array_size")
        array_start_index = row.get("array_start_index")
        array_end_index = row.get("array_end_index")

        if not tag_name:

            errors.append(
                "PLC tag name is required."
            )

        if not tag_type:

            errors.append(
                f"{tag_name or 'PLC tag'}: data type is required."
            )

        if is_array:

            if not array_size or int(array_size) <= 0:

                errors.append(
                    f"{tag_name or 'PLC tag'}: array size must be greater than zero."
                )

            if array_start_index is None or array_end_index is None:

                errors.append(
                    f"{tag_name or 'PLC tag'}: array start and end index are required."
                )

            elif int(array_start_index) > int(array_end_index):

                errors.append(
                    f"{tag_name or 'PLC tag'}: array start index cannot be greater than end index."
                )

            elif array_size and ((int(array_end_index) - int(array_start_index)) + 1) < int(array_size):

                errors.append(
                    f"{tag_name or 'PLC tag'}: array index span must cover array size {array_size}."
                )

        requirement = None

        if tag_purpose and stage_requirements:

            requirement = stage_requirements.get(
                tag_purpose
            )

        if requirement:

            expected_type = (
                requirement.get("expected_type")
                or
                ""
            ).strip().upper()

            if expected_type and tag_type and tag_type != expected_type:

                errors.append(
                    f"{tag_name}: purpose {tag_purpose} expects {expected_type}, found {tag_type}."
                )

            array_required = int(
                requirement.get("array_required")
                or
                0
            )

            if array_required and not is_array:

                errors.append(
                    f"{tag_name}: purpose {tag_purpose} must be an array tag."
                )

            if not array_required and is_array:

                errors.append(
                    f"{tag_name}: purpose {tag_purpose} must be a scalar tag."
                )

            minimum_array_size = requirement.get("minimum_array_size")

            if array_required and minimum_array_size:

                if not array_size or int(array_size) < int(minimum_array_size):

                    errors.append(
                        f"{tag_name}: purpose {tag_purpose} requires array size at least {minimum_array_size}."
                    )

            required_start = requirement.get("array_start_index")
            required_end = requirement.get("array_end_index")

            if array_required and required_start is not None and array_start_index is not None:

                if int(array_start_index) > int(required_start):

                    errors.append(
                        f"{tag_name}: purpose {tag_purpose} must cover start index {required_start}."
                    )

            if array_required and required_end is not None and array_end_index is not None:

                if int(array_end_index) < int(required_end):

                    errors.append(
                        f"{tag_name}: purpose {tag_purpose} must cover end index {required_end}."
                    )

        return errors

    @staticmethod
    def _stage_requirements_by_purpose(machine_id, stage_id):

        try:

            from database.stage_plc_tag_requirement_manager import (
                StagePLCTagRequirementManager
            )

            return {
                (row.get("purpose") or "").strip().upper(): row
                for row in StagePLCTagRequirementManager.get_stage_requirements(
                    machine_id,
                    stage_id,
                    active_only=False
                )
            }

        except Exception:

            return {}

    @staticmethod
    def get_stage_tags(machine_id, stage_id):

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
                CASE WHEN COALESCE(tag_purpose, '') = '' THEN 1 ELSE 0 END,
                tag_purpose,
                tag_name
            """,
            (
                machine_id,
                stage_id
            )
        )

        rows = [
            dict(row)
            for row in cursor.fetchall()
        ]

        conn.close()

        return rows

    @staticmethod
    def update_tag_config(
        tag_id,
        tag_name,
        tag_type,
        is_array=0,
        array_size=None,
        array_start_index=None,
        array_end_index=None,
        description="",
        tag_purpose=None,
        machine_id=None,
        stage_id=None
    ):

        conn = get_connection()
        cursor = conn.cursor()

        try:

            cursor.execute(
                """
                SELECT *
                FROM plc_tags
                WHERE id = ?
                """,
                (
                    tag_id,
                )
            )

            old_row = cursor.fetchone()

            if not old_row:

                return {
                    "success": False,
                    "message": "PLC tag not found.",
                    "errors": ["PLC tag not found."],
                    "old": None,
                    "new": None,
                    "changes": []
                }

            old = dict(old_row)

            if machine_id is not None and int(old["machine_id"]) != int(machine_id):

                return {
                    "success": False,
                    "message": "PLC tag does not belong to selected machine.",
                    "errors": ["PLC tag does not belong to selected machine."],
                    "old": old,
                    "new": None,
                    "changes": []
                }

            if stage_id is not None and int(old["stage_id"]) != int(stage_id):

                return {
                    "success": False,
                    "message": "PLC tag does not belong to selected stage.",
                    "errors": ["PLC tag does not belong to selected stage."],
                    "old": old,
                    "new": None,
                    "changes": []
                }

            machine_id = old["machine_id"]
            stage_id = old["stage_id"]

            new = PLCTagManager._clean_tag_config({
                "id": tag_id,
                "tag_name": tag_name,
                "tag_type": tag_type,
                "is_array": is_array,
                "array_size": array_size,
                "array_start_index": array_start_index,
                "array_end_index": array_end_index,
                "description": description,
                "tag_purpose": tag_purpose,
            })

            stage_requirements = PLCTagManager._stage_requirements_by_purpose(
                machine_id,
                stage_id
            )

            errors = PLCTagManager._validate_tag_config(
                new,
                stage_requirements=stage_requirements
            )

            cursor.execute(
                """
                SELECT id, tag_name
                FROM plc_tags
                WHERE
                    machine_id = ?
                    AND stage_id = ?
                    AND UPPER(tag_name) = UPPER(?)
                    AND id != ?
                """,
                (
                    machine_id,
                    stage_id,
                    new["tag_name"],
                    tag_id
                )
            )

            duplicate_name = cursor.fetchone()

            if duplicate_name:

                errors.append(
                    f"Tag name already exists for this machine/stage: {new['tag_name']}."
                )

            if new.get("tag_purpose"):

                cursor.execute(
                    """
                    SELECT id, tag_name
                    FROM plc_tags
                    WHERE
                        machine_id = ?
                        AND stage_id = ?
                        AND UPPER(COALESCE(tag_purpose, '')) = UPPER(?)
                        AND id != ?
                    """,
                    (
                        machine_id,
                        stage_id,
                        new["tag_purpose"],
                        tag_id
                    )
                )

                duplicate_purpose = cursor.fetchone()

                if duplicate_purpose:

                    errors.append(
                        f"Purpose {new['tag_purpose']} is already assigned to {duplicate_purpose['tag_name']}. Clear/remap that tag first."
                    )

            if errors:

                return {
                    "success": False,
                    "message": errors[0],
                    "errors": errors,
                    "old": old,
                    "new": new,
                    "changes": []
                }

            fields = [
                "tag_name",
                "tag_type",
                "is_array",
                "array_size",
                "array_start_index",
                "array_end_index",
                "description",
                "tag_purpose"
            ]

            changes = []

            for field in fields:

                old_value = old.get(field)
                new_value = new.get(field)

                if str(old_value if old_value is not None else "") != str(new_value if new_value is not None else ""):

                    changes.append({
                        "field": field,
                        "old": old_value,
                        "new": new_value
                    })

            if not changes:

                return {
                    "success": True,
                    "message": "No PLC tag change detected.",
                    "errors": [],
                    "old": old,
                    "new": new,
                    "changes": []
                }

            cursor.execute(
                """
                UPDATE plc_tags
                SET
                    tag_name = ?,
                    tag_type = ?,
                    is_array = ?,
                    array_size = ?,
                    array_start_index = ?,
                    array_end_index = ?,
                    description = ?,
                    tag_purpose = ?
                WHERE id = ?
                """,
                (
                    new["tag_name"],
                    new["tag_type"],
                    new["is_array"],
                    new["array_size"],
                    new["array_start_index"],
                    new["array_end_index"],
                    new["description"],
                    new["tag_purpose"],
                    tag_id
                )
            )

            conn.commit()

            return {
                "success": True,
                "message": f"PLC tag {new['tag_name']} updated.",
                "errors": [],
                "old": old,
                "new": new,
                "changes": changes
            }

        except Exception as exc:

            conn.rollback()

            return {
                "success": False,
                "message": f"PLC tag update failed: {exc}",
                "errors": [str(exc)],
                "old": None,
                "new": None,
                "changes": []
            }

        finally:

            conn.close()

    @staticmethod
    def bulk_update_stage_tags(machine_id, stage_id, rows):

        cleaned_rows = []

        for row in rows:

            cleaned = PLCTagManager._clean_tag_config(
                row
            )

            if cleaned.get("id"):

                cleaned_rows.append(
                    cleaned
                )

        if not cleaned_rows:

            return {
                "success": True,
                "message": "No PLC tag rows submitted.",
                "errors": [],
                "changes": []
            }

        stage_requirements = PLCTagManager._stage_requirements_by_purpose(
            machine_id,
            stage_id
        )

        errors = []
        names = {}
        purposes = {}

        for row in cleaned_rows:

            errors.extend(
                PLCTagManager._validate_tag_config(
                    row,
                    stage_requirements=stage_requirements
                )
            )

            name_key = (
                row.get("tag_name")
                or
                ""
            ).strip().upper()

            if name_key:

                if name_key in names:

                    errors.append(
                        f"Duplicate PLC tag name in submitted rows: {row['tag_name']}."
                    )

                names[name_key] = row["id"]

            purpose_key = (
                row.get("tag_purpose")
                or
                ""
            ).strip().upper()

            if purpose_key:

                if purpose_key in purposes:

                    errors.append(
                        f"Duplicate PLC purpose in submitted rows: {purpose_key}."
                    )

                purposes[purpose_key] = row["id"]

        conn = get_connection()
        cursor = conn.cursor()

        try:

            row_ids = [
                row["id"]
                for row in cleaned_rows
            ]

            placeholders = ",".join(
                "?"
                for _ in row_ids
            )

            cursor.execute(
                f"""
                SELECT *
                FROM plc_tags
                WHERE
                    machine_id = ?
                    AND stage_id = ?
                    AND id IN ({placeholders})
                """,
                [
                    machine_id,
                    stage_id
                ] + row_ids
            )

            existing = {
                int(row["id"]): dict(row)
                for row in cursor.fetchall()
            }

            for row in cleaned_rows:

                if row["id"] not in existing:

                    errors.append(
                        f"PLC tag id {row['id']} does not belong to this machine/stage."
                    )

            cursor.execute(
                """
                SELECT id, tag_name, tag_purpose
                FROM plc_tags
                WHERE
                    machine_id = ?
                    AND stage_id = ?
                """,
                (
                    machine_id,
                    stage_id
                )
            )

            all_stage_tags = [
                dict(row)
                for row in cursor.fetchall()
            ]

            submitted_by_id = {
                row["id"]: row
                for row in cleaned_rows
            }

            final_name_owner = {}
            final_purpose_owner = {}

            for tag in all_stage_tags:

                tag_id = int(
                    tag["id"]
                )

                final_row = submitted_by_id.get(
                    tag_id,
                    tag
                )

                name_key = (
                    final_row.get("tag_name")
                    or
                    ""
                ).strip().upper()

                if name_key:

                    if name_key in final_name_owner and final_name_owner[name_key] != tag_id:

                        errors.append(
                            f"Tag name conflict after save: {final_row.get('tag_name')}."
                        )

                    final_name_owner[name_key] = tag_id

                purpose_key = (
                    final_row.get("tag_purpose")
                    or
                    ""
                ).strip().upper()

                if purpose_key:

                    if purpose_key in final_purpose_owner and final_purpose_owner[purpose_key] != tag_id:

                        errors.append(
                            f"Purpose conflict after save: {purpose_key}."
                        )

                    final_purpose_owner[purpose_key] = tag_id

            if errors:

                return {
                    "success": False,
                    "message": errors[0],
                    "errors": errors,
                    "changes": []
                }

            cursor.execute(
                "BEGIN"
            )

            changes = []

            fields = [
                "tag_name",
                "tag_type",
                "is_array",
                "array_size",
                "array_start_index",
                "array_end_index",
                "description",
                "tag_purpose"
            ]

            for row in cleaned_rows:

                old = existing[row["id"]]
                row_changes = []

                for field in fields:

                    old_value = old.get(field)
                    new_value = row.get(field)

                    if str(old_value if old_value is not None else "") != str(new_value if new_value is not None else ""):

                        row_changes.append({
                            "field": field,
                            "old": old_value,
                            "new": new_value
                        })

                if not row_changes:

                    continue

                cursor.execute(
                    """
                    UPDATE plc_tags
                    SET
                        tag_name = ?,
                        tag_type = ?,
                        is_array = ?,
                        array_size = ?,
                        array_start_index = ?,
                        array_end_index = ?,
                        description = ?,
                        tag_purpose = ?
                    WHERE
                        id = ?
                        AND machine_id = ?
                        AND stage_id = ?
                    """,
                    (
                        row["tag_name"],
                        row["tag_type"],
                        row["is_array"],
                        row["array_size"],
                        row["array_start_index"],
                        row["array_end_index"],
                        row["description"],
                        row["tag_purpose"],
                        row["id"],
                        machine_id,
                        stage_id
                    )
                )

                changes.append({
                    "id": row["id"],
                    "tag_name": row["tag_name"],
                    "old": old,
                    "new": row,
                    "changes": row_changes
                })

            conn.commit()

            return {
                "success": True,
                "message": f"PLC tag configuration saved. {len(changes)} tag(s) updated.",
                "errors": [],
                "changes": changes
            }

        except Exception as exc:

            conn.rollback()

            return {
                "success": False,
                "message": f"PLC tag bulk update failed: {exc}",
                "errors": [str(exc)],
                "changes": []
            }

        finally:

            conn.close()

    @staticmethod
    def update_tag(

        tag_id,

        tag_name,

        tag_type,

        is_array,

        array_size,

        array_start_index,

        array_end_index,

        description

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE plc_tags

            SET

                tag_name = ?,

                tag_type = ?,

                is_array = ?,

                array_size = ?,

                array_start_index = ?,

                array_end_index = ?,

                description = ?

            WHERE id = ?
            """,
            (

                tag_name,

                tag_type,

                is_array,

                array_size,

                array_start_index,

                array_end_index,

                description,

                tag_id

            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def delete_tag(

        tag_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM plc_tags

            WHERE id = ?
            """,
            (
                tag_id,
            )
        )

        conn.commit()

        conn.close()
