import hashlib
import importlib
import json
import os
import runpy
import shutil
import sqlite3
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from config.settings import (
    DATABASE_PATH,
    DATABASE_URL,
    PROJECT_ROOT,
    RECIPE_EXPORT_FOLDER,
    RECIPE_IMPORT_FOLDER,
)
from database.database import get_connection


@dataclass(frozen=True)
class BootstrapStep:
    group: str
    name: str
    action: object
    required: bool = True
    detail: str = ""


class CRSSystemBootstrapManager:
    """Recovery-safe CRS setup runner.

    This class is intentionally conservative:
    - no DROP TABLE setup steps
    - no blind import of every create_*.py script
    - every step is grouped and timed
    - every run writes a JSON report for troubleshooting
    """

    SQLITE_PREFIX = "sqlite"

    REQUIRED_TABLES = [
        "schema_version",
        "users",
        "user_sessions",
        "user_login_attempt_alerts",
        "audit_log",
        "audit_log_archive",
        "audit_archive_exports",
        "system_settings",
        "engineering_units",
        "tbm_families",
        "tbm_machines",
        "machine_stages",
        "plc_master",
        "plc_registry",
        "plc_program_history",
        "plc_tags",
        "plc_parameter_mapping",
        "plc_operation_jobs",
        "template_master",
        "template_parameters",
        "parameter_definitions",
        "stage_plc_tag_requirements",
        "phase_control_group_master",
        "phase_control_master",
        "phase_control_options",
        "phase_control_mapping",
        "recipe_master",
        "recipes",
        "recipe_versions",
        "recipe_version_values",
        "recipe_parameters",
        "recipe_parameter_values",
        "recipe_parameter_audit",
        "recipe_phase_control",
        "recipe_plc_mapping",
        "recipe_resource_locks",
        "recipe_upload_history",
        "recipe_download_history",
        "recipe_status_history",
        "system_bootstrap_history",
    ]

    def __init__(self, seed_users=None, verbose=True):
        self.verbose = verbose
        self.seed_users = self._resolve_seed_users(seed_users)
        self.run_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        self.started_at_utc = datetime.utcnow()
        self.started_at = time.monotonic()
        self.results = []
        self.report_dir = PROJECT_ROOT / "reports" / "bootstrap"
        self.backup_dir = PROJECT_ROOT / "_local_backups" / "bootstrap"
        self.database_url = str(DATABASE_URL)
        self.database_kind = self._database_kind()

    @staticmethod
    def _resolve_seed_users(seed_users):
        if seed_users is not None:
            return bool(seed_users)

        raw = os.getenv("CRS_BOOTSTRAP_SEED_DEFAULT_USERS", "1")
        return raw.strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def _database_kind(self):
        parsed = urlparse(self.database_url)
        return (parsed.scheme or "sqlite").split("+", 1)[0].lower()

    def _redacted_database_url(self):
        if "://" not in self.database_url:
            return self.database_url

        parsed = urlparse(self.database_url)
        if parsed.password:
            return self.database_url.replace(
                f":{parsed.password}@",
                ":***@",
            )
        return self.database_url

    def _status_line(self, current, total, group, name, status, step_seconds):
        elapsed = time.monotonic() - self.started_at
        average = elapsed / max(current, 1)
        remaining = average * max(total - current, 0)

        return (
            f"[{current:02d}/{total:02d}] "
            f"{group} / {name} ... {status} "
            f"({step_seconds:.2f}s, elapsed {self._fmt_time(elapsed)}, "
            f"remaining {self._fmt_time(remaining)})"
        )

    @staticmethod
    def _fmt_time(seconds):
        seconds = int(max(seconds, 0))
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{sec:02d}"
        return f"{minutes:02d}:{sec:02d}"

    def _print(self, message):
        if self.verbose:
            print(message, flush=True)

    def _call(self, module_name, function_name):
        module = importlib.import_module(module_name)
        func = getattr(module, function_name)
        return func()

    def _run_module(self, module_name):
        return runpy.run_module(
            module_name,
            run_name="__main__",
        )

    def _ensure_directories(self):
        for folder in [
            DATABASE_PATH.parent,
            RECIPE_EXPORT_FOLDER,
            RECIPE_IMPORT_FOLDER,
            self.report_dir,
            self.backup_dir,
            PROJECT_ROOT / "logs",
        ]:
            Path(folder).mkdir(
                parents=True,
                exist_ok=True,
            )

    def _validate_database_target(self):
        if self.database_kind != self.SQLITE_PREFIX:
            # The current CRS runtime still has sqlite3 managers in active use.
            # Do not pretend full MySQL bootstrap is ready until those managers
            # are migrated to SQLAlchemy/Alembic.
            from database.sqlalchemy_db import check_connection

            check_connection()
            raise RuntimeError(
                "Non-SQLite database connection is reachable, but full CRS "
                "table bootstrap is not enabled for this backend yet. "
                "Complete SQLAlchemy/Alembic migration before plant MySQL setup."
            )

        DATABASE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        conn = sqlite3.connect(DATABASE_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()

    def _backup_existing_sqlite_database(self):
        if self.database_kind != self.SQLITE_PREFIX:
            return "not_sqlite"

        if not DATABASE_PATH.exists() or DATABASE_PATH.stat().st_size == 0:
            return "new_database"

        backup_name = (
            f"recipe_pre_bootstrap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )
        backup_path = self.backup_dir / backup_name
        shutil.copy2(
            DATABASE_PATH,
            backup_path,
        )
        return str(backup_path)

    def _create_parameter_definitions_table_safe(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS parameter_definitions
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                stage_id INTEGER NOT NULL,
                tag_index INTEGER NOT NULL,
                plc_array_index INTEGER,
                parameter_name TEXT NOT NULL,
                parameter_class TEXT,
                unit TEXT,
                min_value REAL,
                max_value REAL,
                default_value REAL,
                datatype TEXT DEFAULT 'REAL',
                english_memo TEXT,
                used INTEGER DEFAULT 1,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_parameter_definition_tag_index
            ON parameter_definitions(machine_id, stage_id, tag_index)
            """
        )
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_parameter_definition_name
            ON parameter_definitions(machine_id, stage_id, parameter_name)
            """
        )
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_parameter_definition_plc_array
            ON parameter_definitions(machine_id, stage_id, plc_array_index)
            """
        )
        conn.commit()
        conn.close()

    def _create_phase_control_group_master_table(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS phase_control_group_master
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_stage_id INTEGER NOT NULL,
                phase_group_code TEXT NOT NULL,
                phase_group_name TEXT NOT NULL,
                display_order INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(machine_stage_id, phase_group_code)
            )
            """
        )
        conn.commit()
        conn.close()

    def _create_bootstrap_history_table(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS system_bootstrap_history
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                status TEXT NOT NULL,
                database_kind TEXT,
                database_url_hash TEXT,
                started_at TEXT,
                completed_at TEXT,
                elapsed_seconds REAL,
                total_steps INTEGER,
                successful_steps INTEGER,
                failed_steps INTEGER,
                report_path TEXT,
                message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        conn.close()

    def _record_schema_version(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO schema_version
            (
                version,
                description,
                applied_at
            )
            SELECT
                ?,
                ?,
                CURRENT_TIMESTAMP
            WHERE NOT EXISTS
            (
                SELECT 1
                FROM schema_version
                WHERE version = ?
            )
            """,
            (
                "CRS_BOOTSTRAP_V1",
                "Grouped CRS workstation recovery/bootstrap initializer",
                "CRS_BOOTSTRAP_V1",
            ),
        )
        conn.commit()
        conn.close()

    def _create_sqlalchemy_managed_tables(self):
        # Import all ORM classes before create_all so SQLAlchemy metadata is
        # populated. This currently covers newer job/audit manager tables.
        import database.orm_models  # noqa: F401
        from database.sqlalchemy_db import Base, engine

        Base.metadata.create_all(bind=engine)

    def _create_stage_plc_tag_requirements(self):
        from database.stage_plc_tag_requirement_manager import (
            StagePLCTagRequirementManager,
        )

        StagePLCTagRequirementManager.ensure_table()

    def _create_recipe_resource_locks(self):
        from database.recipe_resource_lock_manager import (
            RecipeResourceLockManager,
        )

        RecipeResourceLockManager.ensure_table()

    def _create_recipe_parameter_audit(self):
        from database.recipe_parameter_audit_manager import (
            RecipeParameterAuditManager,
        )

        RecipeParameterAuditManager.ensure_table()

    def _create_upload_history(self):
        from database.upload_history_manager import UploadHistoryManager

        UploadHistoryManager.ensure_table()

    def _seed_required_users(self):
        if not self.seed_users:
            return "skipped"

        from database.upgrade_user_management_priority11 import (
            ensure_priority11_default_users,
        )

        ensure_priority11_default_users()
        return "seeded"

    def _verify_required_tables(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        )
        existing = {
            row[0]
            for row in cursor.fetchall()
        }
        conn.close()

        missing = [
            table
            for table in self.REQUIRED_TABLES
            if table not in existing
        ]

        if missing:
            raise RuntimeError(
                "Missing required table(s): " + ", ".join(missing)
            )

        return {
            "table_count": len(existing),
            "verified_tables": len(self.REQUIRED_TABLES),
        }

    def _steps(self):
        return [
            BootstrapStep("01 Configuration", "Project folders", self._ensure_directories),
            BootstrapStep("01 Configuration", "Database target", self._validate_database_target),
            BootstrapStep("01 Configuration", "SQLite safety backup", self._backup_existing_sqlite_database),
            BootstrapStep("02 Core", "Schema version table", lambda: self._call("database.create_schema_version_table", "create_schema_version_table")),
            BootstrapStep("02 Core", "Legacy PLC master", lambda: self._call("database.models", "create_plc_master")),
            BootstrapStep("02 Core", "Users table", lambda: self._call("database.models", "create_users")),
            BootstrapStep("02 Core", "User sessions table", lambda: self._call("database.models", "create_user_sessions")),
            BootstrapStep("02 Core", "Audit log table", lambda: self._call("database.models", "create_audit_log")),
            BootstrapStep("02 Core", "System settings table", lambda: self._call("database.create_system_settings_table", "create_system_settings_table")),
            BootstrapStep("02 Core", "Engineering units table", lambda: self._call("database.create_engineering_units_table", "create_engineering_units_table")),
            BootstrapStep("03 Machine Setup", "TBM families", lambda: self._call("database.create_tbm_family_table", "create_tbm_family_table")),
            BootstrapStep("03 Machine Setup", "TBM machines", lambda: self._call("database.create_tbm_machine_table", "create_tbm_machine_table")),
            BootstrapStep("03 Machine Setup", "Machine stages", lambda: self._call("database.create_machine_stage_table", "create_machine_stage_table")),
            BootstrapStep("03 Machine Setup", "PLC registry", lambda: self._call("database.create_plc_registry_table", "create_plc_registry_table")),
            BootstrapStep("03 Machine Setup", "PLC program history", lambda: self._call("database.create_plc_program_history_table", "create_plc_program_history_table")),
            BootstrapStep("03 Machine Setup", "PLC tags", lambda: self._call("database.create_plc_tags_table", "create_plc_tags_table")),
            BootstrapStep("04 Templates", "Template master", lambda: self._call("database.create_template_master_table", "create_template_master_table")),
            BootstrapStep("04 Templates", "Template parameters", lambda: self._call("database.create_template_parameter_table", "create_template_parameter_table")),
            BootstrapStep("04 Templates", "Parameter definitions safe create", self._create_parameter_definitions_table_safe),
            BootstrapStep("04 Templates", "Stage PLC tag requirements", self._create_stage_plc_tag_requirements),
            BootstrapStep("05 Phase Controls", "Phase group master", self._create_phase_control_group_master_table),
            BootstrapStep("05 Phase Controls", "Phase master", lambda: self._call("database.create_phase_control_master_table", "create_phase_control_master_table")),
            BootstrapStep("05 Phase Controls", "Phase options", lambda: self._call("database.create_phase_control_option_table", "create_phase_control_option_table")),
            BootstrapStep("05 Phase Controls", "Phase PLC mapping", lambda: self._call("database.create_phase_control_mapping_table", "create_phase_control_mapping_table")),
            BootstrapStep("05 Phase Controls", "Recipe phase control", lambda: self._call("database.create_recipe_phase_control_table", "create_recipe_phase_control_table")),
            BootstrapStep("06 Recipes", "Legacy recipe master", lambda: self._call("database.models", "create_recipe_master")),
            BootstrapStep("06 Recipes", "Legacy recipe parameters", lambda: self._call("database.models", "create_recipe_parameters")),
            BootstrapStep("06 Recipes", "Legacy recipe phase control", lambda: self._call("database.models", "create_recipe_phase_control")),
            BootstrapStep("06 Recipes", "Recipes table", lambda: self._run_module("database.create_recipes_table")),
            BootstrapStep("06 Recipes", "Recipe versions", lambda: self._call("database.create_recipe_versions_table", "create_recipe_versions_table")),
            BootstrapStep("06 Recipes", "Recipe version values", lambda: self._run_module("database.create_recipe_version_values_table")),
            BootstrapStep("06 Recipes", "Recipe parameter values", lambda: self._run_module("database.create_recipe_parameter_values_table")),
            BootstrapStep("06 Recipes", "Recipe status history", lambda: self._call("database.create_recipe_status_history_table", "create_recipe_status_history_table")),
            BootstrapStep("06 Recipes", "Recipe upload history", self._create_upload_history),
            BootstrapStep("06 Recipes", "Recipe download history", lambda: self._call("database.create_recipe_download_history_table", "create_recipe_download_history_table")),
            BootstrapStep("06 Recipes", "Recipe PLC mapping", lambda: self._call("database.models", "create_recipe_plc_mapping")),
            BootstrapStep("06 Recipes", "Legacy recipe indexes", lambda: self._call("database.models", "create_recipe_parameters_index")),
            BootstrapStep("06 Recipes", "Legacy phase indexes", lambda: self._call("database.models", "create_phase_control_index")),
            BootstrapStep("07 PLC Mapping", "PLC parameter mapping", lambda: self._call("database.models", "create_plc_parameter_mapping")),
            BootstrapStep("07 PLC Mapping", "SQLAlchemy managed tables", self._create_sqlalchemy_managed_tables),
            BootstrapStep("08 Audit/Security", "Recipe parameter audit", self._create_recipe_parameter_audit),
            BootstrapStep("08 Audit/Security", "Recipe resource locks", self._create_recipe_resource_locks),
            BootstrapStep("08 Audit/Security", "User/session/archive schema", lambda: self._call("database.upgrade_user_management_priority11", "upgrade_user_management_schema")),
            BootstrapStep("09 Upgrades", "PLC tags upgrade", lambda: self._call("database.upgrade_plc_tags_table", "upgrade_plc_tags_table")),
            BootstrapStep("09 Upgrades", "Recipe status history upgrade", lambda: self._call("database.upgrade_recipe_status_history_table", "upgrade_recipe_status_history_table")),
            BootstrapStep("09 Upgrades", "Recipe phase control upgrade", lambda: self._call("database.upgrade_recipe_phase_control_table", "upgrade_recipe_phase_control_table")),
            BootstrapStep("09 Upgrades", "Recipe phase recipe-id upgrade", lambda: self._call("database.upgrade_recipe_phase_control_recipe_id", "upgrade_recipe_phase_control_table")),
            BootstrapStep("09 Upgrades", "Recipe download history upgrade", lambda: self._call("database.upgrade_recipe_download_history_table", "upgrade_recipe_download_history_table")),
            BootstrapStep("09 Upgrades", "Recipe test-only flag upgrade", lambda: self._call("database.upgrade_recipes_test_only", "upgrade_recipes_test_only")),
            BootstrapStep("09 Upgrades", "P15 phase scope/schema upgrade", lambda: self._run_module("database.upgrade_p15_second_stage_phase_master"), required=False),
            BootstrapStep("10 Defaults", "Schema version bootstrap record", self._record_schema_version),
            BootstrapStep("10 Defaults", "Default recovery users", self._seed_required_users),
            BootstrapStep("11 Verification", "Bootstrap history table", self._create_bootstrap_history_table),
            BootstrapStep("11 Verification", "Required table verification", self._verify_required_tables),
        ]

    def run(self):
        self._print("")
        self._print("CRS System Bootstrap / Workstation Recovery")
        self._print("=" * 48)
        self._print(f"Run ID       : {self.run_id}")
        self._print(f"Project Root : {PROJECT_ROOT}")
        self._print(f"Database     : {self._redacted_database_url()}")
        self._print(f"Seed Users   : {'YES' if self.seed_users else 'NO'}")
        self._print("")

        steps = self._steps()
        failures = []

        for index, step in enumerate(steps, start=1):
            step_started = time.monotonic()
            result = {
                "group": step.group,
                "name": step.name,
                "required": step.required,
                "status": "PENDING",
                "detail": step.detail,
                "seconds": 0.0,
            }

            try:
                detail = step.action()
                result["status"] = "OK"
                if detail is not None:
                    result["detail"] = str(detail)
                step_seconds = time.monotonic() - step_started
                result["seconds"] = step_seconds
                self._print(
                    self._status_line(
                        index,
                        len(steps),
                        step.group,
                        step.name,
                        "OK",
                        step_seconds,
                    )
                )
            except Exception as exc:
                step_seconds = time.monotonic() - step_started
                result["status"] = "FAILED"
                result["seconds"] = step_seconds
                result["error"] = str(exc)
                result["traceback"] = traceback.format_exc()
                failures.append(result)
                self._print(
                    self._status_line(
                        index,
                        len(steps),
                        step.group,
                        step.name,
                        "FAILED",
                        step_seconds,
                    )
                )
                self._print(f"    Error: {exc}")

                self.results.append(result)

                if step.required:
                    break

            else:
                self.results.append(result)

        completed_at = datetime.utcnow().isoformat(timespec="seconds")
        elapsed = time.monotonic() - self.started_at
        status = "SUCCESS" if not failures else "FAILED"
        report_path = self._write_report(
            status=status,
            completed_at=completed_at,
            elapsed=elapsed,
        )
        self._write_bootstrap_history(
            status=status,
            completed_at=completed_at,
            elapsed=elapsed,
            report_path=report_path,
            message=failures[0]["error"] if failures else "Bootstrap completed",
        )

        self._print("")
        self._print(f"Bootstrap Status : {status}")
        self._print(f"Elapsed          : {self._fmt_time(elapsed)}")
        self._print(f"Report           : {report_path}")
        self._print("")

        return {
            "status": status,
            "report_path": str(report_path),
            "failures": failures,
            "elapsed_seconds": elapsed,
        }

    def _write_report(self, status, completed_at, elapsed):
        self.report_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        report_path = self.report_dir / f"bootstrap_{self.run_id}.json"
        payload = {
            "run_id": self.run_id,
            "status": status,
            "project_root": str(PROJECT_ROOT),
            "database_kind": self.database_kind,
            "database_url_redacted": self._redacted_database_url(),
            "started_at_utc": self.started_at_utc.isoformat(timespec="seconds"),
            "completed_at_utc": completed_at,
            "elapsed_seconds": round(elapsed, 3),
            "steps": self.results,
        }
        report_path.write_text(
            json.dumps(
                payload,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        return report_path

    def _write_bootstrap_history(self, status, completed_at, elapsed, report_path, message):
        if self.database_kind != self.SQLITE_PREFIX:
            return

        try:
            self._create_bootstrap_history_table()
            conn = get_connection()
            cursor = conn.cursor()
            database_hash = hashlib.sha256(
                self.database_url.encode("utf-8")
            ).hexdigest()
            successful_steps = len(
                [
                    row
                    for row in self.results
                    if row.get("status") == "OK"
                ]
            )
            failed_steps = len(
                [
                    row
                    for row in self.results
                    if row.get("status") == "FAILED"
                ]
            )
            cursor.execute(
                """
                INSERT INTO system_bootstrap_history
                (
                    run_id,
                    status,
                    database_kind,
                    database_url_hash,
                    started_at,
                    completed_at,
                    elapsed_seconds,
                    total_steps,
                    successful_steps,
                    failed_steps,
                    report_path,
                    message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.run_id,
                    status,
                    self.database_kind,
                    database_hash,
                    self.started_at_utc.isoformat(timespec="seconds"),
                    completed_at,
                    round(elapsed, 3),
                    len(self._steps()),
                    successful_steps,
                    failed_steps,
                    str(report_path),
                    message,
                ),
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            self._print(f"Bootstrap history write skipped: {exc}")


def run_bootstrap(seed_users=None, verbose=True):
    manager = CRSSystemBootstrapManager(
        seed_users=seed_users,
        verbose=verbose,
    )
    return manager.run()


def main():
    seed_users = None
    if "--no-seed-users" in os.sys.argv:
        seed_users = False
    elif "--seed-users" in os.sys.argv:
        seed_users = True

    result = run_bootstrap(
        seed_users=seed_users,
        verbose=True,
    )
    return 0 if result["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
