"""Secure local database profile and connectivity validation for CRS."""

from __future__ import annotations

import base64
import ctypes
import json
import os
import re
import time
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import URL, create_engine, text
from sqlalchemy.pool import NullPool

from config.settings import DATABASE_URL, PROJECT_ROOT


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


class DatabaseConfigurationManager:
    """Validate and store a MySQL profile without persisting plaintext secrets."""

    PROFILE_PATH = PROJECT_ROOT / "instance" / "database_profile.json"
    PROFILE_VERSION = 1
    DATABASE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")
    SSL_MODES = {"disabled", "required", "verify_identity"}

    @staticmethod
    def _windows_crypto_functions():
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        crypt32.CryptProtectData.argtypes = [
            ctypes.POINTER(_DataBlob),
            wintypes.LPCWSTR,
            ctypes.POINTER(_DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(_DataBlob),
        ]
        crypt32.CryptProtectData.restype = wintypes.BOOL
        crypt32.CryptUnprotectData.argtypes = [
            ctypes.POINTER(_DataBlob),
            ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(_DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(_DataBlob),
        ]
        crypt32.CryptUnprotectData.restype = wintypes.BOOL
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        return crypt32, kernel32

    @classmethod
    def _protect_secret(cls, value):
        if os.name != "nt":
            raise RuntimeError("Secure profile storage requires Windows DPAPI.")

        raw = str(value).encode("utf-8")
        buffer = ctypes.create_string_buffer(raw)
        input_blob = _DataBlob(
            len(raw),
            ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)),
        )
        output_blob = _DataBlob()

        crypt32, kernel32 = cls._windows_crypto_functions()
        if not crypt32.CryptProtectData(
            ctypes.byref(input_blob),
            "CRS MySQL password",
            None,
            None,
            None,
            0,
            ctypes.byref(output_blob),
        ):
            raise ctypes.WinError()

        try:
            protected = ctypes.string_at(output_blob.pbData, output_blob.cbData)
            return base64.b64encode(protected).decode("ascii")
        finally:
            kernel32.LocalFree(output_blob.pbData)

    @classmethod
    def _unprotect_secret(cls, value):
        if os.name != "nt":
            raise RuntimeError("Secure profile storage requires Windows DPAPI.")

        protected = base64.b64decode(str(value).encode("ascii"), validate=True)
        buffer = ctypes.create_string_buffer(protected)
        input_blob = _DataBlob(
            len(protected),
            ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)),
        )
        output_blob = _DataBlob()

        crypt32, kernel32 = cls._windows_crypto_functions()
        if not crypt32.CryptUnprotectData(
            ctypes.byref(input_blob),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(output_blob),
        ):
            raise ctypes.WinError()

        try:
            raw = ctypes.string_at(output_blob.pbData, output_blob.cbData)
            return raw.decode("utf-8")
        finally:
            kernel32.LocalFree(output_blob.pbData)

    @classmethod
    def validate_fields(cls, fields, password_required=True):
        cleaned = {
            "host": str(fields.get("host") or "").strip(),
            "port": str(fields.get("port") or "3306").strip(),
            "database": str(fields.get("database") or "").strip(),
            "username": str(fields.get("username") or "").strip(),
            "password": str(fields.get("password") or ""),
            "ssl_mode": str(fields.get("ssl_mode") or "required").strip().lower(),
            "ssl_ca_path": str(fields.get("ssl_ca_path") or "").strip(),
        }
        errors = []

        if not cleaned["host"] or len(cleaned["host"]) > 253:
            errors.append("Enter a valid MySQL server hostname or IP address.")
        elif any(character.isspace() for character in cleaned["host"]):
            errors.append("MySQL server hostname must not contain spaces.")

        try:
            port = int(cleaned["port"])
            if not 1 <= port <= 65535:
                raise ValueError
            cleaned["port"] = port
        except (TypeError, ValueError):
            errors.append("MySQL port must be between 1 and 65535.")

        if not cls.DATABASE_NAME_PATTERN.fullmatch(cleaned["database"]):
            errors.append(
                "Database name may contain only letters, numbers, and underscores."
            )

        if not cleaned["username"] or len(cleaned["username"]) > 128:
            errors.append("Enter a valid MySQL username.")

        if password_required and not cleaned["password"]:
            errors.append("Enter the MySQL password.")

        if cleaned["ssl_mode"] not in cls.SSL_MODES:
            errors.append("Select a supported TLS mode.")

        if cleaned["ssl_mode"] == "verify_identity":
            ca_path = Path(cleaned["ssl_ca_path"])
            if not cleaned["ssl_ca_path"] or not ca_path.is_file():
                errors.append(
                    "Verify Identity requires an existing CA certificate file."
                )

        return cleaned, errors

    @classmethod
    def _connection_url(cls, fields):
        return URL.create(
            drivername="mysql+pymysql",
            username=fields["username"],
            password=fields["password"],
            host=fields["host"],
            port=int(fields["port"]),
            database=fields["database"],
            query={"charset": "utf8mb4"},
        )

    @classmethod
    def _connect_args(cls, fields):
        args = {
            "connect_timeout": 5,
            "read_timeout": 5,
            "write_timeout": 5,
        }
        if fields["ssl_mode"] == "required":
            args["ssl"] = {"check_hostname": False}
        elif fields["ssl_mode"] == "verify_identity":
            args["ssl"] = {
                "ca": fields["ssl_ca_path"],
                "check_hostname": True,
            }
        return args

    @classmethod
    def test_connection(cls, fields):
        cleaned, errors = cls.validate_fields(fields)
        if errors:
            return {"ok": False, "errors": errors, "fields": cleaned}

        engine = None
        started = time.monotonic()
        try:
            engine = create_engine(
                cls._connection_url(cleaned),
                future=True,
                poolclass=NullPool,
                connect_args=cls._connect_args(cleaned),
            )
            with engine.connect() as connection:
                row = connection.execute(
                    text(
                        "SELECT VERSION() AS server_version, "
                        "DATABASE() AS database_name, "
                        "CURRENT_USER() AS authenticated_user"
                    )
                ).mappings().one()
            return {
                "ok": True,
                "message": "MySQL connection and database selection succeeded.",
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "server_version": str(row["server_version"]),
                "database_name": str(row["database_name"]),
                "authenticated_user": str(row["authenticated_user"]),
                "masked_url": cls._connection_url(cleaned).render_as_string(
                    hide_password=True
                ),
                "fields": cleaned,
            }
        except Exception as exc:
            detail = str(exc)
            if cleaned.get("password"):
                detail = detail.replace(cleaned["password"], "***")
            if len(detail) > 400:
                detail = detail[:397] + "..."
            return {
                "ok": False,
                "errors": [
                    "MySQL connection failed. Check server, database, credentials, "
                    "firewall, account grants, and TLS settings."
                ],
                "technical_detail": detail,
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "fields": cleaned,
            }
        finally:
            if engine is not None:
                engine.dispose()

    @classmethod
    def load_profile(cls, include_password=False):
        if not cls.PROFILE_PATH.is_file():
            return None

        try:
            profile = json.loads(cls.PROFILE_PATH.read_text(encoding="utf-8"))
            if include_password:
                profile["password"] = cls._unprotect_secret(
                    profile.pop("password_dpapi")
                )
            else:
                profile.pop("password_dpapi", None)
                profile["password_saved"] = True
            return profile
        except Exception as exc:
            return {
                "profile_error": (
                    "Saved database profile cannot be read by this Windows account: "
                    f"{type(exc).__name__}."
                )
            }

    @classmethod
    def save_profile(cls, fields, updated_by, test_result=None):
        cleaned, errors = cls.validate_fields(fields)
        if errors:
            raise ValueError(" ".join(errors))

        profile = {
            "profile_version": cls.PROFILE_VERSION,
            "engine": "mysql+pymysql",
            "host": cleaned["host"],
            "port": cleaned["port"],
            "database": cleaned["database"],
            "username": cleaned["username"],
            "ssl_mode": cleaned["ssl_mode"],
            "ssl_ca_path": cleaned["ssl_ca_path"],
            "password_dpapi": cls._protect_secret(cleaned["password"]),
            "updated_by": str(updated_by or "ADMIN"),
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "last_tested_at_utc": datetime.now(timezone.utc).isoformat(),
            "last_tested_server_version": str(
                (test_result or {}).get("server_version") or ""
            ),
            "runtime_activation": "blocked_pending_sqlalchemy_migration",
        }

        cls.PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = cls.PROFILE_PATH.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(profile, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary_path, cls.PROFILE_PATH)
        return cls.load_profile(include_password=False)

    @classmethod
    def test_saved_profile(cls):
        profile = cls.load_profile(include_password=True)
        if not profile or profile.get("profile_error"):
            return {
                "ok": False,
                "errors": ["No readable saved MySQL profile is available."],
            }
        return cls.test_connection(profile)

    @classmethod
    def runtime_status(cls):
        current_driver = str(DATABASE_URL).split(":", 1)[0]
        database_files = list((PROJECT_ROOT / "database").glob("*.py"))
        legacy_files = 0
        for path in database_files:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "get_connection" in content or "sqlite3" in content:
                legacy_files += 1

        return {
            "current_driver": current_driver,
            "current_database": (
                "SQLite development database"
                if current_driver == "sqlite"
                else "Configured external database"
            ),
            "mysql_driver_available": cls._mysql_driver_available(),
            "legacy_sqlite_files": legacy_files,
            "activation_supported": False,
            "activation_message": (
                "Connectivity and secure profile storage are ready. CRS runtime "
                "activation remains blocked until all SQLite managers and migrations "
                "are converted and validated against MySQL."
            ),
        }

    @staticmethod
    def _mysql_driver_available():
        try:
            import pymysql  # noqa: F401
        except ImportError:
            return False
        return True
