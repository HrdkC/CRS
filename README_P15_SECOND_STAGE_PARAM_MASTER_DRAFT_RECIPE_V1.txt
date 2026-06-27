CRS P15 Second Stage Parameter Master + Draft Recipe V1
======================================================

Where to copy
-------------
Extract this ZIP into:
C:\Users\Administrator\Desktop\Centralized_Recipe_System

File added
----------
database\build_p15_second_stage_parameter_master_draft_recipe_v1.py
project_docs\48_P15_Second_Stage_Parameter_Master_Draft_Recipe_V1.txt

Before running
--------------
Fill and save the Excel input file here:
data_imports\P15_Second_Stage_Foundation_Input_Template_V3_PhaseOnly.xlsx

The Parameters sheet must contain actual P15 SECOND_STAGE parameters from local SCADA/PLC.
Do not use guessed production values.

Recommended dry run
-------------------
python database\build_p15_second_stage_parameter_master_draft_recipe_v1.py --dry-run

Create DRAFT recipe
-------------------
python database\build_p15_second_stage_parameter_master_draft_recipe_v1.py

Override recipe code/name if needed
-----------------------------------
python database\build_p15_second_stage_parameter_master_draft_recipe_v1.py --recipe-code GT_P15_SS_TEST_002 --recipe-name "P15 Second Stage Test 002" --version 1

Verify after run
----------------
python -c "import sqlite3; conn=sqlite3.connect('database\\recipe.db'); conn.row_factory=sqlite3.Row; cur=conn.cursor(); rows=cur.execute('SELECT id, recipe_code, recipe_name, version, status, machine_id, stage_id FROM recipes WHERE machine_id=5 AND stage_id=12 ORDER BY id DESC LIMIT 5').fetchall(); print([dict(r) for r in rows]); conn.close()"

python -c "import sqlite3; conn=sqlite3.connect('database\\recipe.db'); conn.row_factory=sqlite3.Row; cur=conn.cursor(); recipe_id=cur.execute('SELECT id FROM recipes WHERE machine_id=5 AND stage_id=12 ORDER BY id DESC LIMIT 1').fetchone()['id']; p=cur.execute('SELECT COUNT(*) c FROM recipe_parameter_values WHERE recipe_id=?',(recipe_id,)).fetchone()['c']; ph=cur.execute('SELECT phase_group_code, COUNT(*) c FROM recipe_phase_control WHERE recipe_id=? GROUP BY phase_group_code ORDER BY phase_group_code',(recipe_id,)).fetchall(); print({'recipe_id': recipe_id, 'parameters': p, 'phase_groups': [dict(r) for r in ph]}); conn.close()"

Commit after successful test
----------------------------
git status
git add database\build_p15_second_stage_parameter_master_draft_recipe_v1.py project_docs\48_P15_Second_Stage_Parameter_Master_Draft_Recipe_V1.txt README_P15_SECOND_STAGE_PARAM_MASTER_DRAFT_RECIPE_V1.txt
git commit -m "Add P15 second stage parameter master draft recipe builder"

Important
---------
This package creates database foundation only.
The next UI patch will show P15 SECOND_STAGE phase control as three groups:
- CAP_STRIP_SIDE
- BT_SIDE
- SHAPING_SIDE
