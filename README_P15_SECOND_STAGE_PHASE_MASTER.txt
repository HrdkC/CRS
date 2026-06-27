CRS P15 Second Stage Phase-Control Master Patch

Purpose:
Adds a safe, idempotent upgrade script for P15 SECOND_STAGE phase-control master data.

Files included:
- database/upgrade_p15_second_stage_phase_master.py
- project_docs/47_P15_Second_Stage_Phase_Control_Master.txt

Install:
1. Extract this ZIP into the CRS project root:
   C:\Users\Administrator\Desktop\Centralized_Recipe_System
2. Overwrite files if prompted.
3. Run:
   python database\upgrade_p15_second_stage_phase_master.py

This script:
- Creates phase_control_group_master table if missing.
- Adds group columns to phase_control_master.
- Adds group columns to recipe_phase_control.
- Backfills old rows as MAIN / Phase Control.
- Inserts P15 SECOND_STAGE groups:
  CAP_STRIP_SIDE, BT_SIDE, SHAPING_SIDE
- Inserts 11 second-stage phase-control master options.

It does not create a recipe and does not modify production recipe values.
