from database.recipe_manager import RecipeManager

new_version = RecipeManager.create_recipe_version(

    recipe_code="GT7107",

    source_version=1,

    created_by="admin"

)

print(
    f"New Version = {new_version}"
)
