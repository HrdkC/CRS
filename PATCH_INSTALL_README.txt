CRS V6.3 Friendly Routes - PATCH ONLY - Project Root ZIP
============================================================

Apply location:
  Extract this ZIP INSIDE your existing Centralized_Recipe_System folder.

Approved standard:
  URL:     P15/FS and P15/SS
  Display: P15 - FS First Stage and P15 - SS Second Stage
  DB:      machine_id and stage_id remain numeric internally.

Recommended PowerShell steps:
  cd C:\Users\Administrator\Desktop\Centralized_Recipe_System
  Expand-Archive -Path .\CRS_V6.3_FriendlyRoutes_PATCH_ONLY_ProjectRoot_270626.zip -DestinationPath . -Force

Then restart Flask:
  python app.py

This patch includes only changed source/templates/docs. It does not include database, venv, .git, or cache files.

Changed files:
  flask_app/__init__.py
  flask_app/stage_url_helper.py
  flask_app/routes/dashboard_routes.py
  flask_app/routes/parameter_routes.py
  flask_app/routes/plc_array_import_routes.py
  flask_app/routes/plc_tag_routes.py
  flask_app/routes/recipe_routes.py
  flask_app/templates/parameters/parameters.html
  flask_app/templates/plc_array_import/import_1d_array.html
  flask_app/templates/plc_tags/browser.html
  flask_app/templates/recipes/copy_recipe.html
  flask_app/templates/recipes/create_recipe.html
  flask_app/templates/recipes/download_preparation.html
  flask_app/templates/recipes/editor.html
  flask_app/templates/recipes/recipes.html
  flask_app/templates/stages/stages.html
  README_V6_3_FRIENDLY_ROUTES.txt
