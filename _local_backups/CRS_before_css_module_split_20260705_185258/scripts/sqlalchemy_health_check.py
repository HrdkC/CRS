import sys

from pathlib import (
    Path
)

from sqlalchemy import (
    func,
    select
)

ROOT_DIR = Path(__file__).resolve().parent.parent

if str(ROOT_DIR) not in sys.path:

    sys.path.insert(
        0,
        str(ROOT_DIR)
    )

from config.settings import (
    DATABASE_URL
)

from database.sqlalchemy_db import (
    check_connection,
    session_scope
)

from database.orm_models import (
    AuditLog,
    ParameterDefinition,
    PLCOperationJob,
    PLCTag,
    Recipe,
    RecipeParameterValue,
    User
)


def count_rows(

    session,

    model

):

    return session.execute(
        select(
            func.count()
        ).select_from(
            model
        )
    ).scalar_one()


def main():

    print(
        "SQLAlchemy CRS Health Check"
    )

    print(
        f"DATABASE_URL = {DATABASE_URL}"
    )

    check_connection()

    print(
        "Connection OK"
    )

    with session_scope() as session:

        counts = {
            "recipes": count_rows(
                session,
                Recipe
            ),
            "recipe_parameter_values": count_rows(
                session,
                RecipeParameterValue
            ),
            "parameter_definitions": count_rows(
                session,
                ParameterDefinition
            ),
            "plc_tags": count_rows(
                session,
                PLCTag
            ),
            "plc_operation_jobs": count_rows(
                session,
                PLCOperationJob
            ),
            "audit_log": count_rows(
                session,
                AuditLog
            ),
            "users": count_rows(
                session,
                User
            )
        }

        for table_name, row_count in counts.items():

            print(
                f"{table_name}: {row_count}"
            )

        current_recipe = session.execute(
            select(
                Recipe.id,
                Recipe.recipe_code,
                Recipe.version,
                Recipe.status
            )
            .where(
                Recipe.recipe_code == "GT_Copy_Test"
            )
            .order_by(
                Recipe.version.desc()
            )
            .limit(
                1
            )
        ).first()

        if current_recipe:

            print(
                "Latest GT_Copy_Test:",
                dict(
                    current_recipe._mapping
                )
            )

    print(
        "SQLAlchemy foundation OK"
    )


if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        print(
            f"SQLAlchemy health check failed: {exc}"
        )

        raise
