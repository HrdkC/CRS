from datetime import datetime
import json

from pycomm3 import LogixDriver

from database.database import get_connection
from database.audit_manager import AuditManager


class PLCVerificationManager:

    @staticmethod
    def _safe_text(value):
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def verify_plc(plc_id, ip_address):
        """
        Read online PLC identity and compare with CRS expected identity.

        Expected fields currently stored in plc_registry:
        - processor_name
        - firmware_revision
        - program_revision  (used as expected PLC program name in verification)

        Actual fields stored after online read:
        - actual_processor_name
        - actual_firmware_revision
        - actual_serial_number
        - actual_program_name
        """
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM plc_registry
            WHERE id = ?
            """,
            (plc_id,)
        )
        plc_record = cursor.fetchone()

        if not plc_record:
            conn.close()
            raise ValueError(f"PLC record not found: {plc_id}")

        with LogixDriver(ip_address) as plc:
            info = plc.info

        processor_name = PLCVerificationManager._safe_text(
            info.get("product_name", "")
        )

        revision = info.get("revision", {}) or {}
        firmware_revision = (
            f"{revision.get('major', '')}."
            f"{revision.get('minor', '')}"
        ).strip(".")

        serial_number = PLCVerificationManager._safe_text(
            info.get("serial", "")
        )

        program_name = PLCVerificationManager._safe_text(
            info.get("name", "")
        )

        expected_processor = PLCVerificationManager._safe_text(
            plc_record["processor_name"]
        )
        expected_firmware = PLCVerificationManager._safe_text(
            plc_record["firmware_revision"]
        )
        expected_program = PLCVerificationManager._safe_text(
            plc_record["program_revision"]
        )

        mismatches = []
        verification_status = "PASS"

        if expected_processor and expected_processor != processor_name:
            verification_status = "FAIL"
            mismatches.append("processor")

        if expected_firmware and expected_firmware != firmware_revision:
            verification_status = "FAIL"
            mismatches.append("firmware")

        if expected_program and expected_program != program_name:
            verification_status = "FAIL"
            mismatches.append("program")

        cursor.execute(
            """
            UPDATE plc_registry
            SET
                actual_processor_name = ?,
                actual_firmware_revision = ?,
                actual_serial_number = ?,
                actual_program_name = ?,
                verification_status = ?,
                last_verified_at = CURRENT_TIMESTAMP
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
            "expected_processor": expected_processor,
            "actual_processor": processor_name,
            "expected_firmware": expected_firmware,
            "actual_firmware": firmware_revision,
            "expected_program": expected_program,
            "actual_program": program_name,
            "program_name": program_name,
            "serial_number": serial_number,
            "verification_status": verification_status,
            "mismatches": mismatches,
        }

    @staticmethod
    def sync_expected_from_actual(
        plc_id,
        username,
        role,
        reason,
        workstation_name=None,
        client_ip=None,
        user_agent=None,
        forwarded_for=None,
        request_host=None,
    ):
        """
        Update CRS expected PLC identity from the latest online actual identity.

        This is intentionally based on actual_* fields already written by verify_plc().
        User must first run Verify, then intentionally sync expected values with reason.
        """
        clean_reason = (reason or "").strip()
        if not clean_reason:
            raise ValueError("Reason is required to sync expected PLC details.")

        conn = get_connection()
        conn.row_factory = None
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM plc_registry
            WHERE id = ?
            """,
            (plc_id,)
        )
        plc_record = cursor.fetchone()

        if not plc_record:
            conn.close()
            raise ValueError(f"PLC record not found: {plc_id}")

        # sqlite Row support depends on get_connection row_factory.
        # Convert safely using cursor.description.
        columns = [col[0] for col in cursor.description]
        plc = dict(zip(columns, plc_record))

        actual_processor = PLCVerificationManager._safe_text(
            plc.get("actual_processor_name")
        )
        actual_firmware = PLCVerificationManager._safe_text(
            plc.get("actual_firmware_revision")
        )
        actual_program = PLCVerificationManager._safe_text(
            plc.get("actual_program_name")
        )
        actual_serial = PLCVerificationManager._safe_text(
            plc.get("actual_serial_number")
        )

        if not any([actual_processor, actual_firmware, actual_program, actual_serial]):
            conn.close()
            raise ValueError(
                "No actual online PLC details found. Run Verify first, then sync expected details."
            )

        old_expected = {
            "processor_name": PLCVerificationManager._safe_text(plc.get("processor_name")),
            "firmware_revision": PLCVerificationManager._safe_text(plc.get("firmware_revision")),
            "program_revision": PLCVerificationManager._safe_text(plc.get("program_revision")),
        }

        new_expected = {
            "processor_name": actual_processor,
            "firmware_revision": actual_firmware,
            "program_revision": actual_program,
        }

        cursor.execute(
            """
            UPDATE plc_registry
            SET
                processor_name = ?,
                firmware_revision = ?,
                program_revision = ?,
                verification_status = 'PASS',
                last_verified_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                new_expected["processor_name"],
                new_expected["firmware_revision"],
                new_expected["program_revision"],
                plc_id,
            )
        )

        conn.commit()
        conn.close()

        audit_old = {
            "expected_before": old_expected,
            "latest_actual": {
                "actual_processor_name": actual_processor,
                "actual_firmware_revision": actual_firmware,
                "actual_program_name": actual_program,
                "actual_serial_number": actual_serial,
            },
        }
        audit_new = {
            "expected_after": new_expected,
        }

        AuditManager.log_event(
            username=username or "SYSTEM",
            role=role or "SYSTEM",
            action="PLC_EXPECTED_IDENTITY_UPDATED_FROM_ONLINE",
            change_source="PLC_VERIFICATION",
            plc_name=plc.get("plc_name"),
            record_id=str(plc_id),
            parameter_name="PLC_EXPECTED_IDENTITY",
            old_value=json.dumps(audit_old, ensure_ascii=False),
            new_value=json.dumps(audit_new, ensure_ascii=False),
            reason=clean_reason,
            workstation_name=workstation_name,
            client_ip=client_ip,
            user_agent=user_agent,
            forwarded_for=forwarded_for,
            request_host=request_host,
        )

        return {
            "plc_id": plc_id,
            "plc_name": plc.get("plc_name"),
            "old_expected": old_expected,
            "new_expected": new_expected,
            "actual_serial_number": actual_serial,
        }
