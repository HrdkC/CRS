# Current CRS agreement decision register

- Keep Flask/Python browser intranet architecture.
- SQLite is development/current RC storage; MySQL production activation requires proven parity; MSSQL is future work.
- Use `pycomm3` for ControlLogix communication.
- Current RELEASED values may be edited by authorized roles with mandatory atomic audit.
- Historical RELEASED versions are immutable.
- Unchanged values create no audit.
- Roles: ADMIN, ENGINEERING, TECHNOLOGY, PRODUCTION, OPERATOR, VIEWER.
- VIEWER is read-only.
- Existing live session has priority; one normalized username has one active session.
- P15 FS recipe arrays are REAL[500].
- P15 SS recipe arrays are REAL[150].
- P15 SS recipe phase groups are CAP_STRIP_SIDE and BT_SIDE only.
- SHAPING_SIDE is fixed PLC logic and never recipe data.
- P15 SS stop and position are not recipe data.
- Restore, Save, Download and Upload require server-side conflict protection.
- RECIPE_DATA is the CRS source buffer; TEST_RECIPE_DATA is the configured testing destination/running buffer.
- No partial recipe download.
- AI/ML remains advisory and has no recipe approval, release, interlock or PLC-write authority.
