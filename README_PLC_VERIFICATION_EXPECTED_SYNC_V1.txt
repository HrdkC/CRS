CRS PLC Verification Expected Details Sync V1
=============================================

Purpose
-------
Adds a controlled button on the PLC Verification screen:

    Sync Expected Details From Online PLC

This allows ADMIN/ENGINEERING to update CRS expected PLC identity using the latest online actual PLC details captured by Verify.

Updated expected fields
-----------------------
- processor_name        <- actual_processor_name
- firmware_revision    <- actual_firmware_revision
- program_revision     <- actual_program_name

Serial number is recorded in the audit as an online reference, but this patch does not add a new expected serial-number field.

Safety
------
- Only ADMIN and ENGINEERING can sync expected details.
- Reason is mandatory.
- Audit action: PLC_EXPECTED_IDENTITY_UPDATED_FROM_ONLINE
- Verification must be run first so actual online details are available.
- Use only after confirming the connected PLC is the correct physical machine PLC.

Install
-------
Extract this ZIP into the CRS project root and overwrite files.

Run
---
python app.py

Test
----
1. Open /plcs/verify/<plc_id>
2. Confirm actual details are displayed.
3. Enter reason and click Sync Expected Details From Online PLC.
4. Re-verify.
5. Check audit history for PLC_EXPECTED_IDENTITY_UPDATED_FROM_ONLINE.

Files
-----
- database/plc_verification_manager.py
- flask_app/routes/plc_routes.py
- flask_app/templates/plcs/verify_plc.html
- project_docs/49_PLC_Verification_Expected_Details_Sync_V1.txt
