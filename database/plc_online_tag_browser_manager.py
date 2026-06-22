from pycomm3 import (
    LogixDriver
)

from database.database import (
    get_connection
)


class PLCOnlineTagBrowserManager:

    @staticmethod
    def get_active_plc(

        machine_id,

        stage_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                p.*,

                m.machine_code,

                s.stage_type

            FROM plc_registry p

            INNER JOIN machine_stages s

                ON s.id = p.machine_stage_id

            INNER JOIN tbm_machines m

                ON m.id = s.machine_id

            WHERE

                s.id = ?

                AND s.machine_id = ?

                AND p.active = 1

            ORDER BY
                p.plc_name
            """,
            (
                stage_id,
                machine_id
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None

    @staticmethod
    def search_online_tags(

        machine_id,

        stage_id,

        search_text="",

        bool_only=False,

        limit=100

    ):

        result = {

            "searched": True,

            "connected": False,

            "plc": None,

            "search_text": search_text,

            "bool_only": bool_only,

            "total_controller_tags": 0,

            "matched_count": 0,

            "returned_count": 0,

            "limit": limit,

            "tags": [],

            "errors": [],

            "warnings": []

        }

        plc = (
            PLCOnlineTagBrowserManager
            .get_active_plc(

                machine_id=machine_id,

                stage_id=stage_id

            )
        )

        result["plc"] = plc

        if not plc:

            result["errors"].append(
                "No active PLC is registered for this machine and stage."
            )

            return result

        try:

            with LogixDriver(
                plc["ip_address"],
                init_tags=False,
                init_program_tags=False,
                timeout=5
            ) as plc_conn:

                raw_tags = plc_conn.get_tag_list(
                    cache=False
                )

            result["connected"] = True

            result["total_controller_tags"] = len(
                raw_tags
            )

            normalized_tags = [

                PLCOnlineTagBrowserManager
                .normalize_tag(
                    raw_tag
                )

                for raw_tag in raw_tags

            ]

            matched_tags = [

                tag

                for tag in normalized_tags

                if PLCOnlineTagBrowserManager.matches_search(

                    tag=tag,

                    search_text=search_text,

                    bool_only=bool_only

                )

            ]

            matched_tags = sorted(
                matched_tags,
                key=lambda item: item["tag_name"].upper()
            )

            result["matched_count"] = len(
                matched_tags
            )

            result["tags"] = matched_tags[
                :limit
            ]

            result["returned_count"] = len(
                result["tags"]
            )

            if result["matched_count"] > result["returned_count"]:

                result["warnings"].append(
                    f"Showing first {result['returned_count']} of "
                    f"{result['matched_count']} matching PLC tags. "
                    "Narrow the search text if needed."
                )

        except Exception as ex:

            result["errors"].append(
                f"PLC online tag search failed: {ex}"
            )

        return result

    @staticmethod
    def normalize_tag(

        raw_tag

    ):

        tag_name = (
            raw_tag.get(
                "tag_name"
            )
            or
            raw_tag.get(
                "name"
            )
            or
            raw_tag.get(
                "tag"
            )
            or
            ""
        )

        data_type = (
            raw_tag.get(
                "data_type_name"
            )
            or
            raw_tag.get(
                "data_type"
            )
            or
            raw_tag.get(
                "tag_type"
            )
            or
            ""
        )

        if isinstance(
            data_type,
            dict
        ):

            data_type = (
                data_type.get(
                    "name"
                )
                or
                data_type.get(
                    "data_type_name"
                )
                or
                str(
                    data_type
                )
            )

        data_type = str(
            data_type
        )

        dimensions = (
            raw_tag.get(
                "dimensions"
            )
            or
            raw_tag.get(
                "dim"
            )
            or
            []
        )

        if dimensions is None:

            dimensions = []

        if isinstance(
            dimensions,
            int
        ):

            dimensions = [
                dimensions
            ]

        dimensions = [

            int(dimension)

            for dimension in dimensions

            if dimension

        ]

        is_array = 1 if dimensions else 0

        array_size = 1

        for dimension in dimensions:

            array_size *= dimension

        if not dimensions:

            array_size = None

        return {

            "tag_name": tag_name,

            "tag_type": data_type.upper(),

            "is_array": is_array,

            "array_size": array_size,

            "array_start_index": 0
            if is_array
            else
            None,

            "array_end_index": array_size - 1
            if array_size
            else
            None,

            "dimensions": " x ".join(
                [
                    str(dimension)
                    for dimension in dimensions
                ]
            )
            if dimensions
            else
            "-",

            "raw": raw_tag

        }

    @staticmethod
    def matches_search(

        tag,

        search_text,

        bool_only

    ):

        if bool_only and tag["tag_type"].upper() != "BOOL":

            return False

        search_text = (
            search_text
            or
            ""
        ).strip().upper()

        if not search_text:

            return True

        return (
            search_text in tag["tag_name"].upper()
            or
            search_text in tag["tag_type"].upper()
        )
