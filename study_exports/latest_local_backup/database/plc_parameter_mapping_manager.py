# database/plc_parameter_mapping_manager.py

from database.database import get_connection


class PLCParameterMappingManager:

    @staticmethod
    def add_mapping(

        plc_name,

        parameter_name,

        plc_array_index

    ):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id

        FROM plc_parameter_mapping

        WHERE plc_name = ?
        AND parameter_name = ?
        """, (

            plc_name,
            parameter_name

        ))

        existing = cursor.fetchone()

        if existing:

            conn.close()

            print(
                f"Warning : Mapping Already Exists : "
                f"{plc_name} - {parameter_name}"
            )

            return False

        cursor.execute("""
        INSERT INTO plc_parameter_mapping (

            plc_name,

            parameter_name,

            plc_array_index

        )

        VALUES (?, ?, ?)
        """, (

            plc_name,

            parameter_name,

            plc_array_index

        ))

        conn.commit()
        conn.close()

        print(
            f"Mapping Added : "
            f"{plc_name} -> "
            f"{parameter_name} -> "
            f"{plc_array_index}"
        )

        return True

    @staticmethod
    def get_mapping(

        plc_name,

        parameter_name

    ):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT *

        FROM plc_parameter_mapping

        WHERE plc_name = ?
        AND parameter_name = ?
        """, (

            plc_name,
            parameter_name

        ))

        mapping = cursor.fetchone()

        conn.close()

        return mapping

    @staticmethod
    def list_mappings(

        plc_name

    ):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT *

        FROM plc_parameter_mapping

        WHERE plc_name = ?

        ORDER BY plc_array_index
        """, (

            plc_name,

        ))

        mappings = cursor.fetchall()

        conn.close()

        return mappings

    @staticmethod
    def delete_mapping(

        plc_name,

        parameter_name

    ):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        DELETE FROM plc_parameter_mapping

        WHERE plc_name = ?
        AND parameter_name = ?
        """, (

            plc_name,
            parameter_name

        ))

        conn.commit()

        deleted = cursor.rowcount

        conn.close()

        if deleted:

            print(
                f"Mapping Deleted : "
                f"{parameter_name}"
            )

            return True

        print(
            f"Warning : Mapping Not Found"
        )

        return False
    
    @staticmethod
    def get_mapping_by_index(

        plc_name,

        plc_array_index

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
        SELECT *

        FROM plc_parameter_mapping

        WHERE plc_name = ?
        AND plc_array_index = ?
        """, (

            plc_name,

            plc_array_index

        ))

        mapping = cursor.fetchone()

        conn.close()

        return mapping