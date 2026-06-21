import re

from database.audit_manager import (
    AuditManager
)

from database.database import (
    get_connection
)

from database.machine_manager import (
    MachineManager
)

from database.plc_registry_manager import (
    PLCRegistryManager
)

from database.stage_manager import (
    StageManager
)


class PLCRegistryImportManager:

    PLC_NAME_PATTERN = re.compile(
        r"^(P\d+)([A-Za-z]+)$"
    )

    @staticmethod
    def _get_legacy_plcs():

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM plc_master

            WHERE active = 1

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
    def _get_machine_by_code(
        machine_code
    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM tbm_machines

            WHERE UPPER(machine_code) = UPPER(?)

            ORDER BY active DESC, id

            LIMIT 1
            """,
            (
                machine_code,
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None

    @staticmethod
    def _get_stage_by_machine_and_type(
        machine_id,
        stage_type
    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM machine_stages

            WHERE machine_id = ?
            AND stage_type = ?

            LIMIT 1
            """,
            (
                machine_id,
                stage_type
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None

    @staticmethod
    def _active_registry_plc_exists(
        machine_stage_id
    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id

            FROM plc_registry

            WHERE machine_stage_id = ?
            AND active = 1

            LIMIT 1
            """,
            (
                machine_stage_id,
            )
        )

        row = cursor.fetchone()

        conn.close()

        return row is not None

    @staticmethod
    def build_preview(
        suffix_stage_map,
        create_missing_machines=False,
        create_missing_stages=False,
        default_family_id=None
    ):

        preview = []

        for plc in PLCRegistryImportManager._get_legacy_plcs():

            plc_name = plc["plc_name"]

            match = PLCRegistryImportManager.PLC_NAME_PATTERN.match(
                plc_name
            )

            if not match:

                preview.append(
                    {
                        "plc_name": plc_name,
                        "ip_address": plc["ip_address"],
                        "machine_code": None,
                        "suffix": None,
                        "stage_type": None,
                        "machine_stage_id": None,
                        "status": "INVALID_PLC_NAME",
                        "message": "PLC name does not match expected pattern"
                    }
                )

                continue

            machine_code = match.group(1).upper()

            suffix = match.group(2).upper()

            stage_type = suffix_stage_map.get(
                suffix
            )

            if not stage_type:

                preview.append(
                    {
                        "plc_name": plc_name,
                        "ip_address": plc["ip_address"],
                        "machine_code": machine_code,
                        "suffix": suffix,
                        "stage_type": None,
                        "machine_stage_id": None,
                        "status": "UNMAPPED_SUFFIX",
                        "message": "No stage mapping selected for suffix"
                    }
                )

                continue

            machine = PLCRegistryImportManager._get_machine_by_code(
                machine_code
            )

            if not machine:

                status = "READY_CREATE_MACHINE"

                message = "Machine will be created before PLC import"

                if (
                    not create_missing_machines
                    or
                    not default_family_id
                ):

                    status = "MISSING_MACHINE"

                    message = "Machine does not exist"

                preview.append(
                    {
                        "plc_name": plc_name,
                        "ip_address": plc["ip_address"],
                        "machine_code": machine_code,
                        "suffix": suffix,
                        "stage_type": stage_type,
                        "machine_stage_id": None,
                        "status": status,
                        "message": message
                    }
                )

                continue

            stage = (
                PLCRegistryImportManager
                ._get_stage_by_machine_and_type(
                    machine["id"],
                    stage_type
                )
            )

            if not stage:

                status = "READY_CREATE_STAGE"

                message = "Machine stage will be created before PLC import"

                if not create_missing_stages:

                    status = "MISSING_STAGE"

                    message = "Machine stage does not exist"

                preview.append(
                    {
                        "plc_name": plc_name,
                        "ip_address": plc["ip_address"],
                        "machine_code": machine_code,
                        "suffix": suffix,
                        "stage_type": stage_type,
                        "machine_stage_id": None,
                        "status": status,
                        "message": message
                    }
                )

                continue

            if (
                PLCRegistryImportManager
                ._active_registry_plc_exists(
                    stage["id"]
                )
            ):

                preview.append(
                    {
                        "plc_name": plc_name,
                        "ip_address": plc["ip_address"],
                        "machine_code": machine_code,
                        "suffix": suffix,
                        "stage_type": stage_type,
                        "machine_stage_id": stage["id"],
                        "status": "ACTIVE_PLC_EXISTS",
                        "message": "Active PLC already exists for this stage"
                    }
                )

                continue

            preview.append(
                {
                    "plc_name": plc_name,
                    "ip_address": plc["ip_address"],
                    "machine_code": machine_code,
                    "suffix": suffix,
                    "stage_type": stage_type,
                    "machine_stage_id": stage["id"],
                    "status": "READY",
                    "message": "Ready to import"
                }
            )

        return preview

    @staticmethod
    def import_from_legacy(
        suffix_stage_map,
        username,
        reason,
        create_missing_machines=False,
        create_missing_stages=False,
        default_family_id=None
    ):

        preview = PLCRegistryImportManager.build_preview(
            suffix_stage_map=suffix_stage_map,
            create_missing_machines=create_missing_machines,
            create_missing_stages=create_missing_stages,
            default_family_id=default_family_id
        )

        imported = 0

        skipped = 0

        created_machines = 0

        created_stages = 0

        for item in preview:

            if item["status"] == "READY_CREATE_MACHINE":

                machine = (
                    PLCRegistryImportManager
                    ._get_machine_by_code(
                        item["machine_code"]
                    )
                )

                if not machine:

                    MachineManager.create_machine(

                        machine_code=item["machine_code"],

                        family_id=default_family_id,

                        description=(
                            f"PCR TBM {item['machine_code']}"
                        ),

                        created_by=username

                    )

                    AuditManager.log_event(

                        username=username,

                        role="ADMIN",

                        action="MACHINE_CREATED",

                        change_source="WEB",

                        record_id=item["machine_code"],

                        reason=reason

                    )

                    created_machines += 1

                    machine = (
                        PLCRegistryImportManager
                        ._get_machine_by_code(
                            item["machine_code"]
                        )
                    )

                stage = (
                    PLCRegistryImportManager
                    ._get_stage_by_machine_and_type(
                        machine["id"],
                        item["stage_type"]
                    )
                )

                item["machine_stage_id"] = stage["id"]

            if item["status"] == "READY_CREATE_STAGE":

                machine = (
                    PLCRegistryImportManager
                    ._get_machine_by_code(
                        item["machine_code"]
                    )
                )

                StageManager.create_stage(

                    machine_id=machine["id"],

                    stage_type=item["stage_type"],

                    description=item["stage_type"]

                )

                AuditManager.log_event(

                    username=username,

                    role="ADMIN",

                    action="STAGE_CREATED",

                    change_source="WEB",

                    record_id=(
                        f"{item['machine_code']} "
                        f"{item['stage_type']}"
                    ),

                    reason=reason

                )

                created_stages += 1

                stage = (
                    PLCRegistryImportManager
                    ._get_stage_by_machine_and_type(
                        machine["id"],
                        item["stage_type"]
                    )
                )

                item["machine_stage_id"] = stage["id"]

            if item["status"] not in [
                "READY",
                "READY_CREATE_MACHINE",
                "READY_CREATE_STAGE"
            ]:

                skipped += 1

                continue

            PLCRegistryManager.create_plc(

                machine_stage_id=item["machine_stage_id"],

                plc_name=item["plc_name"],

                ip_address=item["ip_address"],

                description=(
                    "Imported From Legacy PLC Master"
                ),

                username=username,

                reason=reason,

                change_source="WEB"

            )

            imported += 1

        return {
            "imported": imported,
            "skipped": skipped,
            "created_machines": created_machines,
            "created_stages": created_stages,
            "preview": preview
        }
