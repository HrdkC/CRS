from database.database import (
    get_connection
)

from ipaddress import ip_address as parse_ip_address


class PLCRegistryManager:

    @staticmethod
    def validate_ip_address(value):

        candidate = str(value or "").strip()

        if not candidate:

            raise ValueError("PLC IP address is required.")

        try:

            parsed = parse_ip_address(candidate)

        except ValueError as exc:

            raise ValueError(
                "PLC IP address must be a valid IPv4 or IPv6 address."
            ) from exc

        if (
            parsed.is_unspecified
            or parsed.is_multicast
            or parsed.is_loopback
        ):

            raise ValueError(
                "PLC IP address cannot be unspecified, multicast, or loopback."
            )

        return str(parsed)

    @staticmethod
    def _required_text(value, label):

        candidate = str(value or "").strip()

        if not candidate:

            raise ValueError(f"{label} is required.")

        return candidate

    @staticmethod
    def create_plc(

        machine_stage_id,

        plc_name,

        ip_address,

        controller_type,

        firmware_revision="",

        program_revision="",

        processor_name="",

        plc_software="",

        description="",

        created_by=None

    ):

        plc_name = PLCRegistryManager._required_text(
            plc_name,
            "PLC name"
        )

        ip_address = PLCRegistryManager.validate_ip_address(
            ip_address
        )

        controller_type = PLCRegistryManager._required_text(
            controller_type,
            "Controller type"
        )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO plc_registry
            (

                machine_stage_id,

                plc_name,

                ip_address,

                controller_type,

                firmware_revision,

                program_revision,

                processor_name,

                plc_software,

                description,

                created_by

            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (

                machine_stage_id,

                plc_name,

                ip_address,

                controller_type,

                firmware_revision,

                program_revision,

                processor_name,

                plc_software,

                description,

                created_by

            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_all_plcs():

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM plc_registry

            ORDER BY plc_name
            """
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    @staticmethod
    def get_plc_by_id(

        plc_id

    ):

        ip_address = PLCRegistryManager.validate_ip_address(
            ip_address
        )

        controller_type = PLCRegistryManager._required_text(
            controller_type,
            "Controller type"
        )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM plc_registry

            WHERE id = ?
            """,
            (
                plc_id,
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None

    @staticmethod
    def plc_name_exists(

        plc_name

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id

            FROM plc_registry

            WHERE UPPER(plc_name) = ?
            """,
            (
                plc_name.upper(),
            )
        )

        row = cursor.fetchone()

        conn.close()

        return row is not None

    @staticmethod
    def update_plc(

        plc_id,

        ip_address,

        controller_type,

        firmware_revision,

        program_revision,

        processor_name,

        plc_software,

        description

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM plc_registry

            WHERE id = ?
            """,
            (
                plc_id,
            )
        )

        old_plc = cursor.fetchone()

        if old_plc is None:

            conn.close()

            raise ValueError("PLC record was not found.")

        cursor.execute(
            """
            UPDATE plc_registry

            SET

                ip_address = ?,

                controller_type = ?,

                firmware_revision = ?,

                program_revision = ?,

                processor_name = ?,

                plc_software = ?,

                description = ?

            WHERE id = ?
            """,
            (

                ip_address,

                controller_type,

                firmware_revision,

                program_revision,

                processor_name,

                plc_software,

                description,

                plc_id

            )
        )

        conn.commit()

        conn.close()

        return dict(
            old_plc
        )

    @staticmethod
    def disable_plc(

        plc_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE plc_registry

            SET active = 0

            WHERE id = ?
            """,
            (
                plc_id,
            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def enable_plc(

        plc_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE plc_registry

            SET active = 1

            WHERE id = ?
            """,
            (
                plc_id,
            )
        )

        conn.commit()

        conn.close()
