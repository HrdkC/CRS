# CRS V11.11-RC1 — Recipe Restore Persistence Verification

## Confirmed finding

The uploaded database shows recipe 13 contains `11.0` at PLC array index `0` and the latest Restore job reported an immediate write/readback match for `CRS_Recipe_Data{350}`. The operator reports that Studio 5000 does not retain `CRS_Recipe_Data[0] = 11`.

The pycomm3 array expression `CRS_Recipe_Data{350}` is valid and starts at index zero. The release therefore must not repeatedly rewrite the PLC or assume the syntax is the fault.

## Problem in current behavior

Restore declared `SUCCESS` after an immediate readback on the same connection. A controller routine, SCADA, HMI, or another client can overwrite the buffer immediately afterward, leaving the operator with an unchanged tag even though the application recorded success.

## Change

- Keep the existing immediate full-array readback.
- Wait one second by default.
- Open a new PLC connection.
- Read the entire configured `RECIPE_DATA` array again.
- Compare every element to the database payload.
- Report Restore `SUCCESS` only when the values persist.
- If index 0 returns to zero, report the exact expected/actual mismatch and identify likely external overwrite or wrong monitored controller/tag.
- Record expected, immediate, and persistent first-eight-value previews in the job result.
- Add a read-only diagnostic CLI for controller identity, tag metadata, and two-point readback.

## Configuration

Optional environment setting:

```powershell
$env:CRS_PLC_RESTORE_VERIFY_DELAY_SECONDS = "1.0"
```

## Read-only diagnosis

```powershell
$env:CRS_ALLOW_PLC_COMMUNICATION = "YES"
python scripts\diagnose_recipe_restore_buffer.py --recipe-id 13 --delay 2
```

This command performs PLC reads only.
