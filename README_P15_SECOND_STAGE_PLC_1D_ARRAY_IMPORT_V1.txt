P15 Second Stage PLC 1D Array Import V1
=======================================

Extract into project root:
C:\Users\Administrator\Desktop\Centralized_Recipe_System

Files included:
- app.py
- database/plc_1d_array_recipe_builder.py
- database/recipe_phase_control_manager.py
- flask_app/routes/plc_array_import_routes.py
- flask_app/templates/plc_array_import/import_1d_array.html
- project_docs/50_P15_Second_Stage_PLC_1D_Array_Import_V1.txt

Run:
python app.py

Open:
http://127.0.0.1:5000/plc-array-import/5/12

Workflow:
1. Click Browse PLC Tags, find/copy the exact 1D recipe array tag name.
2. Enter tag name, start index, end index.
3. Click Preview PLC Array.
4. If values are correct, enter reason.
5. Click Build Parameter Master + Draft Recipe.

Expected result:
- P15 SECOND_STAGE parameter_definitions created.
- One DRAFT recipe created.
- recipe_parameter_values created from PLC array values.
- recipe_phase_control created from 3 second-stage phase-control groups.
- Redirects to Recipe Editor for new draft recipe.

DB checks:
python -c "import sqlite3; conn=sqlite3.connect('database\\recipe.db'); conn.row_factory=sqlite3.Row; cur=conn.cursor(); rows=cur.execute('SELECT machine_id, stage_id, COUNT(*) c FROM parameter_definitions WHERE machine_id=5 AND stage_id=12 GROUP BY machine_id, stage_id').fetchall(); print([dict(r) for r in rows]); conn.close()"

python -c "import sqlite3; conn=sqlite3.connect('database\\recipe.db'); conn.row_factory=sqlite3.Row; cur=conn.cursor(); rows=cur.execute('SELECT id, recipe_code, recipe_name, version, status, machine_id, stage_id FROM recipes WHERE machine_id=5 AND stage_id=12 ORDER BY id DESC LIMIT 5').fetchall(); print([dict(r) for r in rows]); conn.close()"

Important:
- Created parameter names are placeholders such as P15 SS Param 030.
- Rename parameters and set correct units/min/max before release.
- Do not use for production download until validation and sync/authority control are complete.
