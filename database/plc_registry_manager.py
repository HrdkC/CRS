from database.database import get_connection

from ipaddress import ip_address as parse_ip_address


class PLCRegistryManager:
    """PLC registry manager.

    The registry is stage-specific. `plc_registry.machine_stage_id` stores the
    selected row id from `machine_stages`, not the machine id.
    """

    TEXT_FIELDS = (
        "plc_name",
        "ip_address",
        "controller_type",
        "firmware_revision",
        "program_revision",
        "processor_name",
        "plc_software",
        "description",
    )

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
    def _optional_text(value):
        return str(value or "").strip()

    @staticmethod
    def _to_int(value, label):
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} is required.") from exc

    @staticmethod
    def _active_value(value):
        return 1 if str(value or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
            "active",
        } else 0

    @staticmethod
    def _stage_exists(cursor, machine_stage_id):
        cursor.execute(
            """
            SELECT
                s.id,
                s.stage_type,
                m.machine_code
            FROM machine_stages s
            LEFT JOIN tbm_machines m
                ON m.id = s.machine_id
            WHERE s.id = ?
            """,
            (machine_stage_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def _clean_payload(
        machine_stage_id,
        plc_name,
        ip_address,
        controller_type,
        firmware_revision="",
        program_revision="",
        processor_name="",
        plc_software="",
        description="",
        active=1,
    ):
        return {
            "machine_stage_id": PLCRegistryManager._to_int(
                machine_stage_id,
                "Machine/stage",
            ),
            "plc_name": PLCRegistryManager._required_text(
                plc_name,
                "PLC name",
            ),
            "ip_address": PLCRegistryManager.validate_ip_address(ip_address),
            "controller_type": PLCRegistryManager._required_text(
                controller_type,
                "Controller type",
            ),
            "firmware_revision": PLCRegistryManager._optional_text(
                firmware_revision
            ),
            "program_revision": PLCRegistryManager._optional_text(
                program_revision
            ),
            "processor_name": PLCRegistryManager._optional_text(
                processor_name
            ),
            "plc_software": PLCRegistryManager._optional_text(
                plc_software
            ),
            "description": PLCRegistryManager._optional_text(description),
            "active": PLCRegistryManager._active_value(active),
        }

    @staticmethod
    def _fetch_by_id(cursor, plc_id):
        cursor.execute(
            """
            SELECT *
            FROM plc_registry
            WHERE id = ?
            """,
            (plc_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def _validate_duplicate_name(cursor, plc_name, plc_id=None):
        params = [plc_name]
        extra = ""
        if plc_id is not None:
            extra = "AND id != ?"
            params.append(plc_id)

        cursor.execute(
            f"""
            SELECT id, plc_name
            FROM plc_registry
            WHERE UPPER(plc_name) = UPPER(?)
            {extra}
            """,
            tuple(params),
        )
        duplicate = cursor.fetchone()
        if duplicate:
            raise ValueError(
                f"PLC name already exists: {duplicate['plc_name']}."
            )

    @staticmethod
    def save_stage_plc_config(
        machine_stage_id,
        plc_name,
        ip_address,
        controller_type,
        firmware_revision="",
        program_revision="",
        processor_name="",
        plc_software="",
        description="",
        active=1,
        plc_id=None,
        created_by=None,
    ):
        """Create or update one PLC registry row from GUI configuration.

        Returns a dictionary containing old/new rows and changed fields for
        audit logging by the route layer.
        """

        payload = PLCRegistryManager._clean_payload(
            machine_stage_id=machine_stage_id,
            plc_name=plc_name,
            ip_address=ip_address,
            controller_type=controller_type,
            firmware_revision=firmware_revision,
            program_revision=program_revision,
            processor_name=processor_name,
            plc_software=plc_software,
            description=description,
            active=active,
        )

        conn = get_connection()
        cursor = conn.cursor()

        try:
            stage = PLCRegistryManager._stage_exists(
                cursor,
                payload["machine_stage_id"],
            )
            if not stage:
                raise ValueError("Selected machine/stage record was not found.")

            old = None
            is_create = plc_id in (None, "", "new")

            if is_create:
                PLCRegistryManager._validate_duplicate_name(
                    cursor,
                    payload["plc_name"],
                )

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
                        active,
                        created_by
                    )
                    VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["machine_stage_id"],
                        payload["plc_name"],
                        payload["ip_address"],
                        payload["controller_type"],
                        payload["firmware_revision"],
                        payload["program_revision"],
                        payload["processor_name"],
                        payload["plc_software"],
                        payload["description"],
                        payload["active"],
                        created_by,
                    ),
                )
                plc_id = cursor.lastrowid
            else:
                plc_id = PLCRegistryManager._to_int(plc_id, "PLC record")
                old = PLCRegistryManager._fetch_by_id(cursor, plc_id)
                if not old:
                    raise ValueError("PLC record was not found.")

                PLCRegistryManager._validate_duplicate_name(
                    cursor,
                    payload["plc_name"],
                    plc_id=plc_id,
                )

                cursor.execute(
                    """
                    UPDATE plc_registry
                    SET
                        machine_stage_id = ?,
                        plc_name = ?,
                        ip_address = ?,
                        controller_type = ?,
                        firmware_revision = ?,
                        program_revision = ?,
                        processor_name = ?,
                        plc_software = ?,
                        description = ?,
                        active = ?
                    WHERE id = ?
                    """,
                    (
                        payload["machine_stage_id"],
                        payload["plc_name"],
                        payload["ip_address"],
                        payload["controller_type"],
                        payload["firmware_revision"],
                        payload["program_revision"],
                        payload["processor_name"],
                        payload["plc_software"],
                        payload["description"],
                        payload["active"],
                        plc_id,
                    ),
                )

            new = PLCRegistryManager._fetch_by_id(cursor, plc_id)

            conn.commit()

            changes = []
            if old:
                fields = (
                    "machine_stage_id",
                    "plc_name",
                    "ip_address",
                    "controller_type",
                    "firmware_revision",
                    "program_revision",
                    "processor_name",
                    "plc_software",
                    "description",
                    "active",
                )
                for field in fields:
                    if str(old.get(field)) != str(new.get(field)):
                        changes.append(
                            {
                                "field": field,
                                "old": old.get(field),
                                "new": new.get(field),
                            }
                        )
            else:
                changes.append(
                    {
                        "field": "created",
                        "old": None,
                        "new": new.get("plc_name"),
                    }
                )

            return {
                "created": old is None,
                "old": old,
                "new": new,
                "changes": changes,
            }

        finally:
            conn.close()

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
        created_by=None,
        username=None,
        reason=None,
        change_source=None,
        active=1,
    ):
        result = PLCRegistryManager.save_stage_plc_config(
            machine_stage_id=machine_stage_id,
            plc_name=plc_name,
            ip_address=ip_address,
            controller_type=controller_type,
            firmware_revision=firmware_revision,
            program_revision=program_revision,
            processor_name=processor_name,
            plc_software=plc_software,
            description=description,
            active=active,
            created_by=created_by or username,
        )
        return result["new"]["id"]

    @staticmethod
    def get_all_plcs():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                p.*,
                s.stage_type,
                s.machine_id,
                m.machine_code,
                CASE
                    WHEN m.machine_code IS NOT NULL AND s.stage_type IS NOT NULL
                    THEN m.machine_code || ' - ' || s.stage_type
                    ELSE '-'
                END AS stage_display
            FROM plc_registry p
            LEFT JOIN machine_stages s
                ON s.id = p.machine_stage_id
            LEFT JOIN tbm_machines m
                ON m.id = s.machine_id
            ORDER BY
                m.machine_code,
                s.stage_type,
                p.plc_name
            """
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    @staticmethod
    def get_all_plcs_with_machine_stage(include_inactive=True):
        rows = PLCRegistryManager.get_all_plcs()
        if include_inactive:
            return rows
        return [row for row in rows if int(row.get("active", 1) or 0) == 1]

    @staticmethod
    def get_plcs_for_stage(machine_stage_id, include_inactive=True):
        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                p.*,
                s.stage_type,
                s.machine_id,
                m.machine_code,
                m.machine_code || ' - ' || s.stage_type AS stage_display
            FROM plc_registry p
            LEFT JOIN machine_stages s
                ON s.id = p.machine_stage_id
            LEFT JOIN tbm_machines m
                ON m.id = s.machine_id
            WHERE p.machine_stage_id = ?
        """

        params = [machine_stage_id]

        if not include_inactive:
            query += " AND COALESCE(p.active, 1) = 1"

        query += """
            ORDER BY
                COALESCE(p.active, 1) DESC,
                p.plc_name
        """

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    @staticmethod
    def get_plc_by_id(plc_id):
        conn = get_connection()
        cursor = conn.cursor()
        row = PLCRegistryManager._fetch_by_id(cursor, plc_id)
        conn.close()
        return row

    @staticmethod
    def _fetch_by_id_with_stage(cursor, plc_id):
        cursor.execute(
            """
            SELECT
                p.*,
                s.stage_type,
                s.machine_id,
                m.machine_code,
                CASE
                    WHEN m.machine_code IS NOT NULL AND s.stage_type IS NOT NULL
                    THEN m.machine_code || ' - ' || s.stage_type
                    ELSE '-'
                END AS stage_display
            FROM plc_registry p
            LEFT JOIN machine_stages s
                ON s.id = p.machine_stage_id
            LEFT JOIN tbm_machines m
                ON m.id = s.machine_id
            WHERE p.id = ?
            """,
            (plc_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def assign_existing_plc_to_stage(plc_id, machine_stage_id):
        """Assign one existing PLC to a stage and make it the active PLC.

        The existing registry row is moved to the selected machine/stage and
        activated. Any other active PLC rows already assigned to the target
        stage are disabled so readiness has one clear active assignment.
        PLC metadata such as IP, controller, firmware and program is not
        changed by this operation.
        """

        plc_id = PLCRegistryManager._to_int(plc_id, "PLC record")
        machine_stage_id = PLCRegistryManager._to_int(
            machine_stage_id,
            "Machine/stage",
        )

        conn = get_connection()
        cursor = conn.cursor()

        try:
            target_stage = PLCRegistryManager._stage_exists(
                cursor,
                machine_stage_id,
            )
            if not target_stage:
                raise ValueError("Selected machine/stage record was not found.")

            old = PLCRegistryManager._fetch_by_id_with_stage(cursor, plc_id)
            if not old:
                raise ValueError("Selected PLC record was not found.")

            cursor.execute(
                """
                SELECT
                    p.*,
                    s.stage_type,
                    m.machine_code,
                    m.machine_code || ' - ' || s.stage_type AS stage_display
                FROM plc_registry p
                LEFT JOIN machine_stages s
                    ON s.id = p.machine_stage_id
                LEFT JOIN tbm_machines m
                    ON m.id = s.machine_id
                WHERE
                    p.machine_stage_id = ?
                    AND p.id != ?
                    AND COALESCE(p.active, 1) = 1
                ORDER BY p.plc_name
                """,
                (machine_stage_id, plc_id),
            )
            deactivated = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                """
                UPDATE plc_registry
                SET active = 0
                WHERE
                    machine_stage_id = ?
                    AND id != ?
                    AND COALESCE(active, 1) = 1
                """,
                (machine_stage_id, plc_id),
            )

            cursor.execute(
                """
                UPDATE plc_registry
                SET
                    machine_stage_id = ?,
                    active = 1
                WHERE id = ?
                """,
                (machine_stage_id, plc_id),
            )

            new = PLCRegistryManager._fetch_by_id_with_stage(cursor, plc_id)
            conn.commit()

            return {
                "old": old,
                "new": new,
                "deactivated": deactivated,
                "moved_from_stage": old.get("machine_stage_id") != machine_stage_id,
                "activated": int(old.get("active", 1) or 0) != 1,
            }

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def plc_name_exists(plc_name):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id
            FROM plc_registry
            WHERE UPPER(plc_name) = UPPER(?)
            """,
            (str(plc_name or "").strip().upper(),),
        )

        row = cursor.fetchone()
        conn.close()
        return row is not None

    @staticmethod
    def update_plc(
        plc_id,
        ip_address,
        controller_type,
        firmware_revision="",
        program_revision="",
        processor_name="",
        plc_software="",
        description="",
        machine_stage_id=None,
        plc_name=None,
        active=None,
        username=None,
        reason=None,
        change_source=None,
    ):
        old = PLCRegistryManager.get_plc_by_id(plc_id)
        if not old:
            raise ValueError("PLC record was not found.")

        result = PLCRegistryManager.save_stage_plc_config(
            plc_id=plc_id,
            machine_stage_id=machine_stage_id or old["machine_stage_id"],
            plc_name=plc_name or old["plc_name"],
            ip_address=ip_address,
            controller_type=controller_type,
            firmware_revision=firmware_revision,
            program_revision=program_revision,
            processor_name=processor_name,
            plc_software=plc_software,
            description=description,
            active=old.get("active", 1) if active is None else active,
        )

        return result["old"]

    @staticmethod
    def disable_plc(plc_id, username=None, reason=None, change_source=None):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE plc_registry
            SET active = 0
            WHERE id = ?
            """,
            (plc_id,),
        )

        conn.commit()
        conn.close()

    @staticmethod
    def enable_plc(plc_id, username=None, reason=None, change_source=None):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE plc_registry
            SET active = 1
            WHERE id = ?
            """,
            (plc_id,),
        )

        conn.commit()
        conn.close()
