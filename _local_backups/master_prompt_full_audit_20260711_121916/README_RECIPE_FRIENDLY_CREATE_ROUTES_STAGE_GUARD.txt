CRS Recipe Friendly Create Routes + Stage Guard

Install:
1. Extract this ZIP into your CRS project root.
2. Overwrite files.
3. Restart Flask with python app.py.

New URLs:
- /recipes/P15/Second_Stage
- /recipes/create/P15/Second_Stage

Old numeric URLs still work:
- /recipes/5/12 redirects to /recipes/P15/Second_Stage
- /recipes/create/5/12 redirects to /recipes/create/P15/Second_Stage on GET

For P15 Second Stage:
- If parameter master is missing, recipe create page will not create an empty recipe.
- It will show buttons for PLC Tag Browser and 1D Array Import.

Test:
python app.py
Open /recipes/create/P15/Second_Stage
Expected: friendly page, no 500 error.
If parameter master count is 0, page shows blocked message and import buttons.
