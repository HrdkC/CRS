# CRS Test Matrix

| Area | Automated now | Required next |
|---|---|---|
| Bootstrap CLI | Help, generic scope, warning status | New workstation recovery drill |
| Security | CSRF, unauth redirect, headers, PLC IP validation | Full role matrix, login lockout concurrency |
| Health | Liveness/readiness | Service monitor integration |
| Python/templates/CSS | Compile and syntax checks | Browser visual regression |
| SQLite | Integrity and foreign-key check | Backup restore and migration rollback |
| Routes | Unauthenticated safe GET smoke | Authenticated functional route matrix |
| Recipes | Existing manual/script tests | Isolated lifecycle and audit pytest suite |
| PLC | No call in safe suite | Mocked pycomm3 tests and explicit live acceptance |
| Import/export | Existing functional implementation | Corrupt/large/duplicate workbook regression |
| Concurrency | Resource locks exist | Two-user edit/download race tests |

## Safe Commands

```powershell
venv\Scripts\python.exe -m pytest tests\safe -q
venv\Scripts\python.exe scripts\audit_crs_repository.py
venv\Scripts\python.exe scripts\validate_crs_release.py
venv\Scripts\python.exe scripts\run_crs.py --check
```

Do not run all legacy `tests/` scripts on a connected plant workstation. Several are script-style and may access the configured database or PLC logic.
