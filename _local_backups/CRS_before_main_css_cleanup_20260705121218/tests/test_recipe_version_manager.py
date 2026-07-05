from database.recipe_version_manager import (
    RecipeVersionManager
)

version_id = (

    RecipeVersionManager
    .create_version(

        recipe_id=1,

        version_comment=
        "Initial Version",

        created_by=
        "admin"

    )

)

print(
    "VERSION ID =",
    version_id
)

versions = (

    RecipeVersionManager
    .get_versions(

        1

    )

)

print(
    "VERSIONS =",
    len(versions)
)

for row in versions:

    print(
        row
    )