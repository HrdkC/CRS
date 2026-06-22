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

            "DOWNLOAD_ENABLE": "Download_Enable",

            "MACHINE_IN_MANUAL": "Manual",

            "DOWNLOAD_REQUEST": "Download_Request",

            "DOWNLOAD_COMPLETE": "Download_Complete"

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

            "DOWNLOAD_ENABLE": "CRS_Download_Enable",

            "MACHINE_IN_MANUAL": "Machine_In_Manual",

            "DOWNLOAD_REQUEST": "CRS_Download_Request",

            "DOWNLOAD_COMPLETE": "CRS_Download_Complete"

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
