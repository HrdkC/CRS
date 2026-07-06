from database.database import get_connection


class TemplateParameterManager:

    @staticmethod
    def add_parameter(

        template_id,

        parameter_name,

        parameter_description,

        plc_tag,

        array_index,

        data_type,

        engineering_unit_id,

        minimum_value,

        maximum_value,

        default_value="0",

        display_order=0

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO template_parameters
            (

                template_id,

                parameter_name,

                parameter_description,

                plc_tag,

                array_index,

                data_type,

                engineering_unit_id,

                minimum_value,

                maximum_value,

                default_value,

                display_order

            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (

                template_id,

                parameter_name,

                parameter_description,

                plc_tag,

                array_index,

                data_type,

                engineering_unit_id,

                minimum_value,

                maximum_value,

                default_value,

                display_order

            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_template_parameters(

        template_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM template_parameters

            WHERE template_id = ?

            AND active = 1

            ORDER BY display_order
            """,
            (
                template_id,
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]