from pycomm3 import (
    LogixDriver
)

from database.database import (
    get_connection
)

from datetime import datetime


class PLCVerificationManager:

    @staticmethod
    def verify_plc(

        plc_id,

        ip_address

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

        plc_record = cursor.fetchone()

        with LogixDriver(
            ip_address
        ) as plc:

            info = plc.info

        processor_name = (
            info.get(
                "product_name",
                ""
            )
        )

        revision = (
            info.get(
                "revision",
                {}
            )
        )

        firmware_revision = (

            f"{revision.get('major', '')}."
            f"{revision.get('minor', '')}"

        )

        serial_number = (
            info.get(
                "serial",
                ""
            )
        )

        program_name = (
            info.get(
                "name",
                ""
            )
        )

        verification_status = "PASS"

        if (

            plc_record[
                "processor_name"
            ]

            and

            plc_record[
                "processor_name"
            ] != processor_name

        ):

            verification_status = "FAIL"

        if (

            plc_record[
                "firmware_revision"
            ]

            and

            plc_record[
                "firmware_revision"
            ] != firmware_revision

        ):

            verification_status = "FAIL"

        cursor.execute(
            """
            UPDATE plc_registry

            SET

                actual_processor_name = ?,

                actual_firmware_revision = ?,

                actual_serial_number = ?,

                actual_program_name = ?,

                verification_status = ?,

                last_verified_at =
                CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (

                processor_name,

                firmware_revision,

                serial_number,

                program_name,

                verification_status,

                plc_id

            )
        )

        conn.commit()

        conn.close()

        return {

            "expected_processor":
            plc_record[
                "processor_name"
            ],

            "actual_processor":
            processor_name,

            "expected_firmware":
            plc_record[
                "firmware_revision"
            ],

            "actual_firmware":
            firmware_revision,

            "program_name":
            program_name,

            "serial_number":
            serial_number,

            "verification_status":
            verification_status

        }