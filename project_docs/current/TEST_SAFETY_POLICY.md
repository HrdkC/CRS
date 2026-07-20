# CRS test safety policy

Default test command:

```text
python -m pytest
```

It collects only `tests/safe`, blocks external socket connections and replaces `pycomm3.LogixDriver` with a fail-closed test stub.

Markers:

- safe
- integration
- plc_live
- destructive
- legacy

Live PLC work is not an automated test. It requires an approved target, an interactive terminal, `CRS_ALLOW_LIVE_PLC_TESTS=YES`, exact typed confirmation and supervised commissioning evidence.
