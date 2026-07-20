# Supervised PLC-live tools

These files are intentionally outside pytest discovery. They may read or write a
real controller and must never be run by CI, IDE test discovery, or an ordinary
`pytest` command.

Required controls before execution:

1. Approved maintenance/test window.
2. Confirmed machine and stage identity.
3. PLC manual/test interlocks verified.
4. Explicit `CRS_ALLOW_LIVE_PLC_TESTS=YES` environment variable.
5. Review the file and target tags before running.
6. Record the operator, controller, program revision, purpose, and result.

Dry-run or read-only behavior should be the default whenever supported.
