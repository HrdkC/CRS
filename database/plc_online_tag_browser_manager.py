from pycomm3 import LogixDriver

from database.database import get_connection
from database.plc_connection_errors import (
    format_plc_connection_failure,
    is_plc_connection_error,
)


class PLCOnlineTagBrowserManager:
    """Online PLC tag browser with diagnostics.

    Important notes:
    - Some ControlLogix projects expose recipe tags as controller tags.
    - Some expose them under program scope, for example Program:<program>.TagName.
    - Older CRS versions could return 0 tags when the pycomm3 driver was opened
      without initializing the tag database. This version tries multiple safe browse
      methods and reports diagnostics on the browser page.
    """

    @staticmethod
    def get_active_plc(machine_id, stage_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                p.*,
                m.machine_code,
                s.stage_type
            FROM plc_registry p
            INNER JOIN machine_stages s ON s.id = p.machine_stage_id
            INNER JOIN tbm_machines m ON m.id = s.machine_id
            WHERE
                s.id = ?
                AND s.machine_id = ?
                AND p.active = 1
            ORDER BY p.plc_name
            """,
            (stage_id, machine_id),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def search_online_tags(
        machine_id,
        stage_id,
        search_text="",
        bool_only=False,
        array_only=False,
        limit=300,
    ):
        result = {
            "searched": True,
            "connected": False,
            "plc": None,
            "search_text": search_text,
            "bool_only": bool_only,
            "array_only": array_only,
            "total_controller_tags": 0,
            "matched_count": 0,
            "returned_count": 0,
            "limit": limit,
            "tags": [],
            "errors": [],
            "warnings": [],
            "diagnostics": [],
            "browse_source": "",
        }

        plc = PLCOnlineTagBrowserManager.get_active_plc(
            machine_id=machine_id,
            stage_id=stage_id,
        )
        result["plc"] = plc

        if not plc:
            result["errors"].append(
                "No active PLC is registered for this machine and stage."
            )
            return result

        try:
            raw_tags = []
            browse_source = []

            with LogixDriver(
                plc["ip_address"],
                init_tags=True,
                init_program_tags=True,
                timeout=10,
            ) as plc_conn:
                tags_attr = getattr(plc_conn, "tags", None)

                if isinstance(tags_attr, dict) and tags_attr:
                    raw_tags = PLCOnlineTagBrowserManager._tags_dict_to_rows(tags_attr)
                    browse_source.append(f"driver.tags={len(raw_tags)}")

                if not raw_tags:
                    try:
                        listed = plc_conn.get_tag_list(cache=False)
                        if listed:
                            raw_tags = list(listed)
                            browse_source.append(f"get_tag_list={len(raw_tags)}")
                    except TypeError as ex:
                        result["diagnostics"].append(
                            f"get_tag_list(cache=False) not supported by this pycomm3 version: {ex}"
                        )
                    except Exception as ex:
                        result["diagnostics"].append(
                            f"get_tag_list(cache=False) failed: {ex}"
                        )

                # Program scoped retry. This is harmless if the pycomm3 version
                # does not support the program argument.
                program_name = (
                    plc.get("actual_program_name")
                    or plc.get("program_revision")
                    or ""
                ).strip()
                if program_name:
                    try:
                        program_listed = plc_conn.get_tag_list(
                            program=program_name,
                            cache=False,
                        )
                        program_rows = list(program_listed or [])
                        if program_rows:
                            for row in program_rows:
                                if isinstance(row, dict) and not (
                                    row.get("tag_name") or row.get("name")
                                ):
                                    row["_program_name"] = program_name
                            raw_tags.extend(program_rows)
                            browse_source.append(
                                f"program:{program_name}={len(program_rows)}"
                            )
                    except TypeError:
                        result["diagnostics"].append(
                            "Program-scoped tag browse is not supported by this pycomm3 version."
                        )
                    except Exception as ex:
                        result["diagnostics"].append(
                            f"Program-scoped tag browse failed for {program_name}: {ex}"
                        )

            result["connected"] = True
            result["browse_source"] = ", ".join(browse_source) or "no-tag-source"

            normalized_tags = []
            seen_names = set()
            for raw_tag in raw_tags:
                tag = PLCOnlineTagBrowserManager.normalize_tag(raw_tag)
                tag_name_key = tag["tag_name"].upper()
                if not tag_name_key:
                    continue
                if tag_name_key in seen_names:
                    continue
                seen_names.add(tag_name_key)
                normalized_tags.append(tag)

            result["total_controller_tags"] = len(normalized_tags)

            matched_tags = [
                tag
                for tag in normalized_tags
                if PLCOnlineTagBrowserManager.matches_search(
                    tag=tag,
                    search_text=search_text,
                    bool_only=bool_only,
                    array_only=array_only,
                )
            ]

            matched_tags = sorted(
                matched_tags,
                key=lambda item: item["tag_name"].upper(),
            )

            result["matched_count"] = len(matched_tags)
            result["tags"] = matched_tags[:limit]
            result["returned_count"] = len(result["tags"])

            if not normalized_tags:
                result["warnings"].append(
                    "PLC connection succeeded, but the online tag database returned 0 tags. "
                    "This can happen if controller tag upload/browse is restricted, "
                    "if tags are program-scoped and the driver cannot enumerate them, "
                    "or if this pycomm3 version cannot browse this controller tag database. "
                    "Use Manual Add Fallback if you know the recipe array tag name."
                )

            if normalized_tags and not matched_tags:
                hint = ""
                sample = normalized_tags[:10]
                if sample:
                    hint = " Sample tags: " + ", ".join(
                        [item["tag_name"] for item in sample]
                    )
                result["warnings"].append(
                    "PLC tags were browsed, but no tags matched the current filter. "
                    "Clear search text and uncheck BOOL Only/Array Only to see more."
                    + hint
                )

            if result["matched_count"] > result["returned_count"]:
                result["warnings"].append(
                    f"Showing first {result['returned_count']} of "
                    f"{result['matched_count']} matching PLC tags. Narrow the search text if needed."
                )

        except Exception as ex:
            if is_plc_connection_error(str(ex)):
                result["errors"].append(
                    format_plc_connection_failure(
                        plc=plc,
                        detail=ex,
                        action="PLC online tag search",
                    )
                )
            else:
                result["errors"].append(f"PLC online tag search failed: {ex}")

        return result

    @staticmethod
    def _tags_dict_to_rows(tags_dict):
        rows = []
        for key, value in tags_dict.items():
            if isinstance(value, dict):
                row = dict(value)
                row.setdefault("_key_name", key)
                rows.append(row)
            else:
                rows.append({"_key_name": key, "raw_object": value})
        return rows

    @staticmethod
    def _get(raw_tag, *names, default=""):
        if isinstance(raw_tag, dict):
            for name in names:
                if name in raw_tag and raw_tag.get(name) not in (None, ""):
                    return raw_tag.get(name)
        for name in names:
            if hasattr(raw_tag, name):
                value = getattr(raw_tag, name)
                if value not in (None, ""):
                    return value
        return default

    @staticmethod
    def normalize_tag(raw_tag):
        tag_name = (
            PLCOnlineTagBrowserManager._get(
                raw_tag,
                "tag_name",
                "name",
                "tag",
                "_key_name",
                default="",
            )
            or ""
        )

        program_name = PLCOnlineTagBrowserManager._get(
            raw_tag,
            "program_name",
            "_program_name",
            default="",
        )
        if program_name and tag_name and not str(tag_name).startswith("Program:"):
            tag_name = f"Program:{program_name}.{tag_name}"

        data_type = PLCOnlineTagBrowserManager._get(
            raw_tag,
            "data_type_name",
            "data_type",
            "tag_type",
            "type",
            default="",
        )

        if isinstance(data_type, dict):
            data_type = (
                data_type.get("name")
                or data_type.get("data_type_name")
                or data_type.get("type")
                or str(data_type)
            )

        data_type = str(data_type or "").upper()

        dimensions = PLCOnlineTagBrowserManager._get(
            raw_tag,
            "dimensions",
            "dim",
            "array_dims",
            default=[],
        )

        if dimensions is None:
            dimensions = []
        if isinstance(dimensions, int):
            dimensions = [dimensions]
        if isinstance(dimensions, str):
            dimensions = [part.strip() for part in dimensions.replace("x", ",").split(",")]

        clean_dimensions = []
        for dimension in dimensions:
            try:
                dim_value = int(dimension)
            except Exception:
                continue
            if dim_value:
                clean_dimensions.append(dim_value)

        is_array = 1 if clean_dimensions else 0
        array_size = None
        if clean_dimensions:
            array_size = 1
            for dimension in clean_dimensions:
                array_size *= dimension

        return {
            "tag_name": str(tag_name or ""),
            "tag_type": data_type,
            "is_array": is_array,
            "array_size": array_size,
            "array_start_index": 0 if is_array else None,
            "array_end_index": array_size - 1 if array_size else None,
            "dimensions": " x ".join(str(d) for d in clean_dimensions) if clean_dimensions else "-",
            "raw": raw_tag,
        }

    @staticmethod
    def matches_search(tag, search_text, bool_only, array_only=False):
        if bool_only and tag["tag_type"].upper() != "BOOL":
            return False

        if array_only and int(tag.get("is_array") or 0) != 1:
            return False

        search_text = (search_text or "").strip().upper()
        if not search_text:
            return True

        return (
            search_text in tag["tag_name"].upper()
            or search_text in tag["tag_type"].upper()
            or search_text in str(tag.get("dimensions") or "").upper()
        )
