CRS Recipe Import / Export V1
=============================

Apply the package to your CRS root folder and overwrite files.

Run:
  python app.py

Test:
  1. Open /recipes/import-export
  2. Download template for P15 / FIRST_STAGE
  3. Fill Recipe Code / GT Code and Recipe Name in Recipe_Info
  4. Upload the template for preview
  5. Confirm import with reason
  6. Confirm recipe opens as DRAFT in Recipe Editor
  7. Export an existing recipe using /recipes/<recipe_id>/export-excel

Expected:
  - Export workbook has README, Recipe_Info, Parameters, Phase_Control and hidden Lists sheets
  - Preview blocks duplicate GT code/version and out-of-range values
  - Import creates recipe as DRAFT only
  - Audit History records export/template/import events
