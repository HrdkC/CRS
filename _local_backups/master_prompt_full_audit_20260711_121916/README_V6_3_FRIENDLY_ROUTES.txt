CRS V6.3 Friendly Machine/Stage Routes
======================================

Approved routing/display standard:

URL:
- /plc-tags/P15/FS
- /plc-tags/P15/SS
- /recipes/P15/FS
- /recipes/P15/SS
- /plc-array-import/P15/FS
- /plc-array-import/P15/SS
- /parameters/P15/FS
- /parameters/P15/SS

Display:
- P15 - FS First Stage
- P15 - SS Second Stage

Internal database IDs remain unchanged:
- machine_id = 5
- stage_id = 11 / 12

Compatibility:
- Old numeric GET routes redirect to friendly routes.
- Old First_Stage / Second_Stage style URLs are accepted and redirected to FS / SS on GET.

Main changed files:
- flask_app/stage_url_helper.py
- flask_app/__init__.py
- flask_app/routes/plc_tag_routes.py
- flask_app/routes/plc_array_import_routes.py
- flask_app/routes/parameter_routes.py
- flask_app/routes/recipe_routes.py
- flask_app/routes/dashboard_routes.py
- flask_app/templates/plc_tags/browser.html
- flask_app/templates/plc_array_import/import_1d_array.html
- flask_app/templates/parameters/parameters.html
- flask_app/templates/recipes/*.html affected back links
- flask_app/templates/stages/stages.html
