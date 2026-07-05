import sys
import os

ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from recipe.recipe_import_export import RecipeImportExport

RecipeImportExport.import_recipe_from_excel(

    recipe_code="GT7107",

    version=1,

    file_path="recipe_imports/GT7107_V1.xlsx"

)