from database.database import get_connection


class PLCManager:

    @staticmethod
    def add_plc(
        plc_name,
        ip_address
    ):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id

        FROM plc_master

        WHERE plc_name = ?
        """, (

            plc_name,

        ))

        existing_plc = cursor.fetchone()

        if existing_plc:

            conn.close()

            print(
                f"PLC Already Exists : {plc_name}"
            )

            return False

        cursor.execute("""
        INSERT INTO plc_master (

            plc_name,
            ip_address

        )

        VALUES (?, ?)
        """, (

            plc_name,
            ip_address

        ))

        conn.commit()
        conn.close()

        print(
            f"PLC Added : {plc_name}"
        )

        return True

    @staticmethod
    def list_plcs():

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT *

        FROM plc_master

        ORDER BY plc_name
        """)

        plcs = cursor.fetchall()

        conn.close()

        return plcs

    @staticmethod
    def get_plc(
        plc_name
    ):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT *

        FROM plc_master

        WHERE plc_name = ?
        """, (

            plc_name,

        ))

        plc = cursor.fetchone()

        conn.close()

        return plc

    @staticmethod
    def disable_plc(
        plc_name
    ):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT active

        FROM plc_master

        WHERE plc_name = ?
        """, (

            plc_name,

        ))

        row = cursor.fetchone()

        if not row:

            conn.close()

            print(
                f"Warning : PLC Not Found : {plc_name}"
            )

            return False

        if row["active"] == 0:

            conn.close()

            print(
                f"Warning : PLC Already Disabled : {plc_name}"
            )

            return False

        cursor.execute("""
        UPDATE plc_master

        SET active = 0

        WHERE plc_name = ?
        """, (

            plc_name,

        ))

        conn.commit()
        conn.close()

        print(
            f"PLC Disabled : {plc_name}"
        )

        return True
    
    @staticmethod
    def update_plc(

        plc_name,

        ip_address=None

    ):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id

        FROM plc_master

        WHERE plc_name = ?
        """, (

            plc_name,

        ))

        existing = cursor.fetchone()

        if not existing:

            conn.close()

            print(
                f"Warning : PLC Not Found : {plc_name}"
            )

            return False

        cursor.execute("""
        UPDATE plc_master

        SET

            ip_address = ?

        WHERE plc_name = ?
        """, (

            ip_address,

            plc_name

        ))

        conn.commit()
        conn.close()

        print(
            f"PLC Updated : {plc_name}"
        )

        return True
    
    @staticmethod
    def get_active_plcs():

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT *

        FROM plc_master

        WHERE active = 1

        ORDER BY plc_name
        """)

        plcs = cursor.fetchall()

        conn.close()

        return plcs