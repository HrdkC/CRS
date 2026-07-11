from database.database import get_connection


class TBMFamilyManager:

    @staticmethod
    def _clean_name(family_name):
        return (family_name or "").strip()

    @staticmethod
    def _clean_description(description):
        return (description or "").strip()

    @staticmethod
    def family_name_exists(family_name, exclude_family_id=None):
        family_name = TBMFamilyManager._clean_name(family_name)

        if not family_name:
            return False

        conn = get_connection()
        cursor = conn.cursor()

        if exclude_family_id:
            cursor.execute(
                """
                SELECT id
                FROM tbm_families
                WHERE LOWER(family_name) = LOWER(?)
                AND id <> ?
                """,
                (
                    family_name,
                    exclude_family_id
                )
            )
        else:
            cursor.execute(
                """
                SELECT id
                FROM tbm_families
                WHERE LOWER(family_name) = LOWER(?)
                """,
                (
                    family_name,
                )
            )

        row = cursor.fetchone()
        conn.close()

        return row is not None

    @staticmethod
    def create_family(

        family_name,

        description="",

        created_by=None

    ):

        family_name = TBMFamilyManager._clean_name(family_name)
        description = TBMFamilyManager._clean_description(description)

        if not family_name:
            raise ValueError("Family name is required.")

        if TBMFamilyManager.family_name_exists(family_name):
            raise ValueError(f"Family {family_name} already exists.")

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO tbm_families
            (

                family_name,

                description,

                created_by

            )
            VALUES
            (?, ?, ?)
            """,
            (

                family_name,

                description,

                created_by

            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_all_families():

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                f.*,
                COALESCE(machine_counts.machine_count, 0) AS machine_count

            FROM tbm_families f

            LEFT JOIN (
                SELECT
                    family_id,
                    COUNT(*) AS machine_count
                FROM tbm_machines
                GROUP BY family_id
            ) machine_counts

            ON machine_counts.family_id = f.id

            ORDER BY f.family_name
            """
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    @staticmethod
    def get_active_families():

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                f.*,
                COALESCE(machine_counts.machine_count, 0) AS machine_count

            FROM tbm_families f

            LEFT JOIN (
                SELECT
                    family_id,
                    COUNT(*) AS machine_count
                FROM tbm_machines
                GROUP BY family_id
            ) machine_counts

            ON machine_counts.family_id = f.id

            WHERE f.active = 1

            ORDER BY f.family_name
            """
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    @staticmethod
    def get_family_by_id(

        family_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM tbm_families

            WHERE id = ?
            """,
            (
                family_id,
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None

    @staticmethod
    def update_family(

        family_id,

        family_name,

        description

    ):

        family_name = TBMFamilyManager._clean_name(family_name)
        description = TBMFamilyManager._clean_description(description)

        if not family_name:
            raise ValueError("Family name is required.")

        current = TBMFamilyManager.get_family_by_id(family_id)

        if not current:
            raise ValueError("Family record was not found.")

        if TBMFamilyManager.family_name_exists(
            family_name,
            exclude_family_id=family_id
        ):
            raise ValueError(f"Family {family_name} already exists.")

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE tbm_families

            SET

                family_name = ?,

                description = ?

            WHERE id = ?
            """,
            (

                family_name,

                description,

                family_id

            )
        )

        conn.commit()

        conn.close()

        updated = TBMFamilyManager.get_family_by_id(family_id)

        return {
            "old": current,
            "new": updated
        }

    @staticmethod
    def get_linked_machine_count(family_id):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) AS machine_count
            FROM tbm_machines
            WHERE family_id = ?
            """,
            (
                family_id,
            )
        )

        row = cursor.fetchone()

        conn.close()

        return int(row["machine_count"] or 0)

    @staticmethod
    def get_linked_machines(family_id):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                machine_code,
                description,
                active
            FROM tbm_machines
            WHERE family_id = ?
            ORDER BY machine_code
            """,
            (
                family_id,
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    @staticmethod
    def delete_family(family_id):

        current = TBMFamilyManager.get_family_by_id(family_id)

        if not current:
            raise ValueError("Family record was not found.")

        linked_count = TBMFamilyManager.get_linked_machine_count(family_id)

        if linked_count:
            raise ValueError(
                "Family cannot be deleted while "
                f"{linked_count} machine(s) are linked."
            )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM tbm_families
            WHERE id = ?
            """,
            (
                family_id,
            )
        )

        conn.commit()

        conn.close()

        return current

    @staticmethod
    def disable_family(

        family_id

    ):

        current = TBMFamilyManager.get_family_by_id(family_id)

        if not current:
            raise ValueError("Family record was not found.")

        linked_count = TBMFamilyManager.get_linked_machine_count(family_id)

        if linked_count:
            raise ValueError(
                "Family cannot be disabled while "
                f"{linked_count} machine(s) are linked. "
                "Reassign linked machines first."
            )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE tbm_families

            SET active = 0

            WHERE id = ?
            """,
            (
                family_id,
            )
        )

        conn.commit()

        conn.close()

        return current

    @staticmethod
    def enable_family(

        family_id

    ):

        current = TBMFamilyManager.get_family_by_id(family_id)

        if not current:
            raise ValueError("Family record was not found.")

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE tbm_families

            SET active = 1

            WHERE id = ?
            """,
            (
                family_id,
            )
        )

        conn.commit()

        conn.close()

        return current
