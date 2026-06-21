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

        created_by=None

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

        conn.commit()

        conn.close()

    @staticmethod
    def search_tags(

        machine_id,

        stage_id,

        search_text=""

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

                AND
                UPPER(tag_name)
                LIKE
                UPPER(?)

            ORDER BY tag_name
            """,
            (
                machine_id,

                stage_id,

                f"%{search_text}%"
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]
        
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