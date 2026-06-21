from flask import (

    render_template,

    redirect,

    session

)

from database.database import (
    get_connection
)


def register_dashboard_routes(

    app

):

    @app.route("/")
    def dashboard():

        if not session.get(

            "logged_in"

        ):

            return redirect(
                "/login"
            )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM tbm_families
            """
        )

        family_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM recipes
            """
        )

        recipe_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM plc_master
            """
        )

        plc_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM plc_registry
            """
        )

        configured_plc_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM tbm_machines
            """
        )

        machine_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM machine_stages
            """
        )

        stage_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM users
            """
        )

        user_count = cursor.fetchone()[0]

        conn.close()

        return render_template(

            "dashboard/dashboard.html",

            family_count=family_count,

            recipe_count=recipe_count,

            plc_count=plc_count,

            configured_plc_count=configured_plc_count,

            machine_count=machine_count,

            stage_count=stage_count,

            user_count=user_count

        )