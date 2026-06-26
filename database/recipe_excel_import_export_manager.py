import os
import re
import uuid
from datetime import datetime
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from database.database import get_connection
from database.audit_manager import AuditManager
from database.recipe_status_history_manager import RecipeStatusHistoryManager


class RecipeExcelImportExportManager:
    """Current CRS recipe Excel import/export for recipes, parameters and phase control."""

    TEMPLATE_TYPE = "CRS_RECIPE_IMPORT_EXPORT_V1"
    PENDING_DIR = os.path.join("recipe_imports", "pending")

    RECIPE_INFO_SHEET = "Recipe_Info"
    PARAMETERS_SHEET = "Parameters"
    PHASE_SHEET = "Phase_Control"
    LISTS_SHEET = "Lists"
    README_SHEET = "README"

    PARAMETER_HEADERS = [
        "Tag Index",
        "PLC Array Index",
        "Parameter Name",
        "Parameter Class",
        "Unit",
        "Data Type",
        "Min Value",
        "Max Value",
        "Default Value",
        "Parameter Value",
        "Is Modified",
        "English Memo",
        "Used",
        "Parameter Definition ID",
    ]

    PHASE_HEADERS = [
        "Line No",
        "Phase Control Name",
        "Phase Control ID",
        "Stop Option",
        "Position Option",
        "Sequence No",
        "Description",
        "Stage Type",
    ]

    @staticmethod
    def _safe_file_part(value):
        value = str(value or "CRS").strip()
        value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
        return value[:80] or "CRS"

    @staticmethod
    def _now_stamp():
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def _get_request_context(request_obj=None):
        if not request_obj:
            return {}
        forwarded_for = request_obj.headers.get("X-Forwarded-For")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else request_obj.remote_addr
        return {
            "client_ip": client_ip,
            "workstation_name": (
                request_obj.headers.get("X-Workstation-Name")
                or request_obj.headers.get("X-Client-Workstation")
                or request_obj.headers.get("X-Forwarded-Host")
                or request_obj.host
            ),
            "user_agent": request_obj.headers.get("User-Agent", ""),
            "forwarded_for": forwarded_for,
            "request_host": request_obj.host,
        }

    @staticmethod
    def _apply_sheet_style(ws, freeze="A2"):
        header_fill = PatternFill("solid", fgColor="243247")
        header_font = Font(color="FFFFFF", bold=True)
        thin = Side(style="thin", color="E2E8F0")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        ws.freeze_panes = freeze
        ws.sheet_view.showGridLines = False

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = border

        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.border = border
                cell.alignment = Alignment(vertical="center", wrap_text=True)

        for column_cells in ws.columns:
            max_length = 8
            column_letter = get_column_letter(column_cells[0].column)
            for cell in column_cells[:80]:
                value = cell.value
                if value is not None:
                    max_length = max(max_length, min(len(str(value)), 45))
            ws.column_dimensions[column_letter].width = min(max_length + 2, 36)

    @staticmethod
    def _style_info_sheet(ws):
        ws.sheet_view.showGridLines = False
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 45
        title_fill = PatternFill("solid", fgColor="6F2DA8")
        sub_fill = PatternFill("solid", fgColor="F4EDFB")
        thin = Side(style="thin", color="E2E8F0")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=2):
            for cell in row:
                cell.border = border
                cell.alignment = Alignment(vertical="center", wrap_text=True)
        ws["A1"].fill = title_fill
        ws["A1"].font = Font(color="FFFFFF", bold=True)
        ws["B1"].fill = title_fill
        ws["B1"].font = Font(color="FFFFFF", bold=True)
        for row_idx in range(2, ws.max_row + 1):
            ws.cell(row_idx, 1).fill = sub_fill
            ws.cell(row_idx, 1).font = Font(bold=True)
        ws.freeze_panes = "A2"

    @staticmethod
    def _create_base_workbook():
        wb = Workbook()
        default = wb.active
        wb.remove(default)
        return wb

    @staticmethod
    def _write_readme(wb):
        ws = wb.create_sheet(RecipeExcelImportExportManager.README_SHEET)
        rows = [
            ["CRS Recipe Excel Template", "Purpose"],
            ["Template Type", RecipeExcelImportExportManager.TEMPLATE_TYPE],
            ["Editable fields", "Recipe_Info: Recipe Code / GT Code, Recipe Name, Version, Is Test Only. Parameters: Parameter Value only. Phase_Control: Phase Control Name/ID, Stop Option, Position Option, Sequence No."],
            ["Safety rule", "Imported recipes are saved as DRAFT. They must be reviewed/released before production use."],
            ["Do not change", "Machine ID, Stage ID, Tag Index, PLC Array Index, Parameter Definition ID, master min/max/unit/datatype columns unless Engineering is intentionally changing master data outside this import flow."],
            ["Validation", "All used parameters for selected machine/stage must be present. Values must be numeric and within min/max where limits are configured. Phase lines must be 1 to 12."],
        ]
        for row in rows:
            ws.append(row)
        RecipeExcelImportExportManager._style_info_sheet(ws)
        return ws

    @staticmethod
    def _write_recipe_info(wb, recipe=None, target=None, exported_by=None, blank=False):
        ws = wb.create_sheet(RecipeExcelImportExportManager.RECIPE_INFO_SHEET)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        source = recipe or target or {}
        rows = [
            ["Field", "Value"],
            ["Template Type", RecipeExcelImportExportManager.TEMPLATE_TYPE],
            ["Exported At", now],
            ["Exported By", exported_by or ""],
            ["Recipe ID", "" if blank else source.get("id", "")],
            ["Recipe Code / GT Code", source.get("recipe_code", "")],
            ["Recipe Name", source.get("recipe_name", "")],
            ["Version", source.get("version", 1)],
            ["Status", "DRAFT"],
            ["Machine ID", source.get("machine_id", "")],
            ["Machine Code", source.get("machine_code", "")],
            ["Stage ID", source.get("stage_id", "")],
            ["Stage Type", source.get("stage_type", "")],
            ["Is Test Only", source.get("is_test_only", 0)],
        ]
        for row in rows:
            ws.append(row)
        RecipeExcelImportExportManager._style_info_sheet(ws)
        return ws

    @staticmethod
    def _write_parameters(wb, parameter_rows):
        ws = wb.create_sheet(RecipeExcelImportExportManager.PARAMETERS_SHEET)
        ws.append(RecipeExcelImportExportManager.PARAMETER_HEADERS)
        for row in parameter_rows:
            ws.append([
                row.get("tag_index"),
                row.get("plc_array_index"),
                row.get("parameter_name"),
                row.get("parameter_class"),
                row.get("unit"),
                row.get("datatype"),
                row.get("min_value"),
                row.get("max_value"),
                row.get("default_value"),
                row.get("parameter_value"),
                row.get("is_modified", 0),
                row.get("english_memo"),
                row.get("used", 1),
                row.get("parameter_definition_id") or row.get("id"),
            ])
        RecipeExcelImportExportManager._apply_sheet_style(ws, freeze="A2")
        for col in ["A", "B", "G", "H", "I", "J", "K", "M", "N"]:
            for cell in ws[col][1:]:
                if cell.value is not None:
                    cell.number_format = "0.########"
        return ws

    @staticmethod
    def _write_phase_control(wb, phase_rows):
        ws = wb.create_sheet(RecipeExcelImportExportManager.PHASE_SHEET)
        ws.append(RecipeExcelImportExportManager.PHASE_HEADERS)
        for row in phase_rows:
            ws.append([
                row.get("line_no"),
                row.get("phase_control_name"),
                row.get("phase_control_id"),
                row.get("stop_option"),
                row.get("position_option"),
                row.get("sequence_no"),
                row.get("description"),
                row.get("stage_type"),
            ])
        RecipeExcelImportExportManager._apply_sheet_style(ws, freeze="A2")
        for col in ["A", "C", "F"]:
            for cell in ws[col][1:]:
                if cell.value is not None:
                    cell.number_format = "0"
        yn = DataValidation(type="list", formula1='"Yes,No"', allow_blank=False)
        ws.add_data_validation(yn)
        yn.add(f"D2:E{max(ws.max_row, 2)}")
        return ws

    @staticmethod
    def _write_lists(wb, stage_type):
        ws = wb.create_sheet(RecipeExcelImportExportManager.LISTS_SHEET)
        ws.append(["Phase Control ID", "Phase Control Name", "Stage Type", "Description"])
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, phase_control_name, stage_type, description
            FROM phase_control_master
            WHERE active = 1 AND stage_type = ?
            ORDER BY display_order, phase_control_name
            """,
            (stage_type,),
        )
        for row in cur.fetchall():
            ws.append([row["id"], row["phase_control_name"], row["stage_type"], row["description"]])
        conn.close()
        RecipeExcelImportExportManager._apply_sheet_style(ws, freeze="A2")
        ws.sheet_state = "hidden"
        return ws

    @staticmethod
    def get_template_targets():
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                m.id AS machine_id,
                m.machine_code,
                s.id AS stage_id,
                s.stage_type,
                COALESCE(m.description, '') AS machine_description,
                COALESCE(s.description, '') AS stage_description
            FROM tbm_machines m
            INNER JOIN machine_stages s ON s.machine_id = m.id
            WHERE COALESCE(m.active, 1) = 1 AND COALESCE(s.active, 1) = 1
            ORDER BY m.machine_code, s.stage_type
            """
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def _get_recipe_export_data(recipe_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT r.*, m.machine_code, s.stage_type
            FROM recipes r
            LEFT JOIN tbm_machines m ON m.id = r.machine_id
            LEFT JOIN machine_stages s ON s.id = r.stage_id
            WHERE r.id = ?
            """,
            (recipe_id,),
        )
        recipe = cur.fetchone()
        if not recipe:
            conn.close()
            raise ValueError("Recipe not found.")
        recipe = dict(recipe)

        cur.execute(
            """
            SELECT
                pd.id AS parameter_definition_id,
                pd.tag_index,
                pd.plc_array_index,
                pd.parameter_name,
                pd.parameter_class,
                pd.unit,
                pd.datatype,
                pd.min_value,
                pd.max_value,
                pd.default_value,
                rpv.parameter_value,
                rpv.is_modified,
                pd.english_memo,
                pd.used
            FROM recipe_parameter_values rpv
            INNER JOIN parameter_definitions pd ON pd.id = rpv.parameter_definition_id
            WHERE rpv.recipe_id = ?
            ORDER BY pd.tag_index
            """,
            (recipe_id,),
        )
        parameters = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT
                rpc.line_no,
                rpc.phase_control_id,
                pcm.phase_control_name,
                rpc.stop_option,
                rpc.position_option,
                rpc.sequence_no,
                pcm.description,
                pcm.stage_type
            FROM recipe_phase_control rpc
            LEFT JOIN phase_control_master pcm ON pcm.id = rpc.phase_control_id
            WHERE rpc.recipe_id = ?
            ORDER BY rpc.line_no
            """,
            (recipe_id,),
        )
        phase_rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return recipe, parameters, phase_rows

    @staticmethod
    def _get_target_template_data(machine_id, stage_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                m.id AS machine_id,
                m.machine_code,
                s.id AS stage_id,
                s.stage_type
            FROM tbm_machines m
            INNER JOIN machine_stages s ON s.machine_id = m.id
            WHERE m.id = ? AND s.id = ?
            """,
            (machine_id, stage_id),
        )
        target = cur.fetchone()
        if not target:
            conn.close()
            raise ValueError("Machine/stage target not found.")
        target = dict(target)

        cur.execute(
            """
            SELECT
                pd.id AS parameter_definition_id,
                pd.tag_index,
                pd.plc_array_index,
                pd.parameter_name,
                pd.parameter_class,
                pd.unit,
                pd.datatype,
                pd.min_value,
                pd.max_value,
                pd.default_value,
                pd.default_value AS parameter_value,
                0 AS is_modified,
                pd.english_memo,
                pd.used
            FROM parameter_definitions pd
            WHERE pd.machine_id = ? AND pd.stage_id = ? AND COALESCE(pd.used, 1) = 1
            ORDER BY pd.tag_index
            """,
            (machine_id, stage_id),
        )
        parameters = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT id, phase_control_name, description, stage_type
            FROM phase_control_master
            WHERE active = 1 AND stage_type = ? AND phase_control_name = 'Empty Phase'
            LIMIT 1
            """,
            (target["stage_type"],),
        )
        empty = cur.fetchone()
        empty_id = empty["id"] if empty else None
        empty_name = empty["phase_control_name"] if empty else "Empty Phase"
        empty_desc = empty["description"] if empty else ""
        phase_rows = []
        for line_no in range(1, 13):
            phase_rows.append({
                "line_no": line_no,
                "phase_control_id": empty_id,
                "phase_control_name": empty_name,
                "stop_option": "No",
                "position_option": "No",
                "sequence_no": line_no,
                "description": empty_desc,
                "stage_type": target["stage_type"],
            })
        conn.close()
        return target, parameters, phase_rows

    @staticmethod
    def build_export_workbook(recipe_id, exported_by=None):
        recipe, parameters, phase_rows = RecipeExcelImportExportManager._get_recipe_export_data(recipe_id)
        wb = RecipeExcelImportExportManager._create_base_workbook()
        RecipeExcelImportExportManager._write_readme(wb)
        RecipeExcelImportExportManager._write_recipe_info(wb, recipe=recipe, exported_by=exported_by)
        RecipeExcelImportExportManager._write_parameters(wb, parameters)
        RecipeExcelImportExportManager._write_phase_control(wb, phase_rows)
        RecipeExcelImportExportManager._write_lists(wb, recipe.get("stage_type"))
        return wb, recipe

    @staticmethod
    def build_blank_template_workbook(machine_id, stage_id, exported_by=None):
        target, parameters, phase_rows = RecipeExcelImportExportManager._get_target_template_data(machine_id, stage_id)
        target.update({
            "recipe_code": "",
            "recipe_name": "",
            "version": 1,
            "status": "DRAFT",
            "is_test_only": 0,
        })
        wb = RecipeExcelImportExportManager._create_base_workbook()
        RecipeExcelImportExportManager._write_readme(wb)
        RecipeExcelImportExportManager._write_recipe_info(wb, target=target, exported_by=exported_by, blank=True)
        RecipeExcelImportExportManager._write_parameters(wb, parameters)
        RecipeExcelImportExportManager._write_phase_control(wb, phase_rows)
        RecipeExcelImportExportManager._write_lists(wb, target.get("stage_type"))
        return wb, target

    @staticmethod
    def workbook_to_bytes(wb):
        stream = BytesIO()
        wb.save(stream)
        stream.seek(0)
        return stream

    @staticmethod
    def export_filename(recipe):
        return (
            f"CRS_RECIPE_{RecipeExcelImportExportManager._safe_file_part(recipe.get('recipe_code'))}"
            f"_V{recipe.get('version')}_{RecipeExcelImportExportManager._now_stamp()}.xlsx"
        )

    @staticmethod
    def template_filename(target):
        return (
            f"CRS_RECIPE_IMPORT_TEMPLATE_{RecipeExcelImportExportManager._safe_file_part(target.get('machine_code'))}"
            f"_{RecipeExcelImportExportManager._safe_file_part(target.get('stage_type'))}"
            f"_{RecipeExcelImportExportManager._now_stamp()}.xlsx"
        )

    @staticmethod
    def save_pending_upload(upload_file):
        if not upload_file or not upload_file.filename:
            raise ValueError("Select an Excel file to import.")
        if not upload_file.filename.lower().endswith(".xlsx"):
            raise ValueError("Only .xlsx files are supported.")
        os.makedirs(RecipeExcelImportExportManager.PENDING_DIR, exist_ok=True)
        token = uuid.uuid4().hex
        path = os.path.join(RecipeExcelImportExportManager.PENDING_DIR, f"{token}.xlsx")
        upload_file.save(path)
        return token, path

    @staticmethod
    def pending_path(token):
        token = re.sub(r"[^a-fA-F0-9]", "", str(token or ""))
        if not token:
            raise ValueError("Invalid import token.")
        path = os.path.join(RecipeExcelImportExportManager.PENDING_DIR, f"{token}.xlsx")
        if not os.path.exists(path):
            raise ValueError("Pending import file not found. Upload the template again.")
        return path

    @staticmethod
    def _read_info_sheet(wb):
        if RecipeExcelImportExportManager.RECIPE_INFO_SHEET not in wb.sheetnames:
            raise ValueError("Recipe_Info sheet missing.")
        ws = wb[RecipeExcelImportExportManager.RECIPE_INFO_SHEET]
        result = {}
        for row in ws.iter_rows(min_row=2, max_col=2, values_only=True):
            key, value = row
            if key is None:
                continue
            result[str(key).strip().lower()] = value
        return result

    @staticmethod
    def _info_value(info, *names, default=None):
        for name in names:
            key = str(name).strip().lower()
            if key in info and info[key] not in (None, ""):
                return info[key]
        return default

    @staticmethod
    def _sheet_rows(wb, sheet_name, expected_headers):
        if sheet_name not in wb.sheetnames:
            raise ValueError(f"{sheet_name} sheet missing.")
        ws = wb[sheet_name]
        headers = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
        missing = [h for h in expected_headers if h not in headers]
        if missing:
            raise ValueError(f"{sheet_name} missing column(s): {', '.join(missing)}")
        header_index = {h: headers.index(h) for h in headers if h}
        rows = []
        for excel_row_no, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if all(value is None for value in row):
                continue
            item = {h: row[header_index[h]] if header_index[h] < len(row) else None for h in expected_headers}
            item["__excel_row__"] = excel_row_no
            rows.append(item)
        return rows

    @staticmethod
    def _to_int(value, label, errors, row_no=None, required=True):
        if value in (None, ""):
            if required:
                errors.append(f"{label} is required" + (f" at row {row_no}" if row_no else ""))
            return None
        try:
            return int(float(value))
        except Exception:
            errors.append(f"{label} must be an integer" + (f" at row {row_no}" if row_no else ""))
            return None

    @staticmethod
    def _to_float(value, label, errors, row_no=None, required=True):
        if value in (None, ""):
            if required:
                errors.append(f"{label} is required" + (f" at row {row_no}" if row_no else ""))
            return None
        try:
            return float(value)
        except Exception:
            errors.append(f"{label} must be numeric" + (f" at row {row_no}" if row_no else ""))
            return None

    @staticmethod
    def preview_import(file_path):
        errors = []
        warnings = []
        try:
            wb = load_workbook(file_path, data_only=True)
        except Exception as exc:
            return {"ok": False, "errors": [f"Unable to read Excel workbook: {exc}"], "warnings": [], "summary": {}}

        try:
            info = RecipeExcelImportExportManager._read_info_sheet(wb)
            template_type = RecipeExcelImportExportManager._info_value(info, "Template Type")
            if template_type != RecipeExcelImportExportManager.TEMPLATE_TYPE:
                errors.append("Invalid template type. Download a fresh CRS recipe template/export workbook.")

            recipe_code = str(RecipeExcelImportExportManager._info_value(info, "Recipe Code / GT Code", "GT Code", default="") or "").strip().upper()
            recipe_name = str(RecipeExcelImportExportManager._info_value(info, "Recipe Name", default="") or "").strip()
            version = RecipeExcelImportExportManager._to_int(RecipeExcelImportExportManager._info_value(info, "Version", default=1), "Version", errors)
            machine_id = RecipeExcelImportExportManager._to_int(RecipeExcelImportExportManager._info_value(info, "Machine ID"), "Machine ID", errors)
            stage_id = RecipeExcelImportExportManager._to_int(RecipeExcelImportExportManager._info_value(info, "Stage ID"), "Stage ID", errors)
            is_test_only = RecipeExcelImportExportManager._to_int(RecipeExcelImportExportManager._info_value(info, "Is Test Only", default=0), "Is Test Only", errors, required=False) or 0

            if not recipe_code:
                errors.append("Recipe Code / GT Code is required in Recipe_Info sheet.")
            if not recipe_name:
                errors.append("Recipe Name is required in Recipe_Info sheet.")
            if version is not None and version < 1:
                errors.append("Version must be 1 or higher.")

            parameter_rows = RecipeExcelImportExportManager._sheet_rows(wb, RecipeExcelImportExportManager.PARAMETERS_SHEET, RecipeExcelImportExportManager.PARAMETER_HEADERS)
            phase_rows = RecipeExcelImportExportManager._sheet_rows(wb, RecipeExcelImportExportManager.PHASE_SHEET, RecipeExcelImportExportManager.PHASE_HEADERS)
        except Exception as exc:
            return {"ok": False, "errors": [str(exc)], "warnings": [], "summary": {}}

        if not errors:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT m.machine_code, s.stage_type
                FROM tbm_machines m
                INNER JOIN machine_stages s ON s.machine_id = m.id
                WHERE m.id = ? AND s.id = ?
                """,
                (machine_id, stage_id),
            )
            target = cur.fetchone()
            if not target:
                errors.append("Machine ID / Stage ID combination does not exist.")
                target = {"machine_code": "-", "stage_type": "-"}
            else:
                target = dict(target)

            cur.execute(
                """
                SELECT id FROM recipes
                WHERE machine_id = ? AND stage_id = ? AND UPPER(recipe_code) = UPPER(?) AND version = ?
                """,
                (machine_id, stage_id, recipe_code, version),
            )
            if cur.fetchone():
                errors.append(f"Recipe {recipe_code} V{version} already exists for selected machine/stage. Use a new GT code or version.")

            cur.execute(
                """
                SELECT * FROM parameter_definitions
                WHERE machine_id = ? AND stage_id = ? AND COALESCE(used, 1) = 1
                ORDER BY tag_index
                """,
                (machine_id, stage_id),
            )
            definitions = [dict(r) for r in cur.fetchall()]
            by_id = {int(r["id"]): r for r in definitions}
            by_tag = {int(r["tag_index"]): r for r in definitions}

            seen_defs = set()
            parsed_parameters = []
            for row in parameter_rows:
                row_no = row["__excel_row__"]
                def_id = RecipeExcelImportExportManager._to_int(row.get("Parameter Definition ID"), "Parameter Definition ID", errors, row_no, required=False)
                tag_index = RecipeExcelImportExportManager._to_int(row.get("Tag Index"), "Tag Index", errors, row_no)
                definition = by_id.get(def_id) if def_id else by_tag.get(tag_index)
                if not definition:
                    errors.append(f"Parameter definition not found for row {row_no}.")
                    continue
                if definition["id"] in seen_defs:
                    errors.append(f"Duplicate parameter definition {definition['id']} at row {row_no}.")
                    continue
                seen_defs.add(definition["id"])
                excel_name = str(row.get("Parameter Name") or "").strip()
                if excel_name and excel_name != definition["parameter_name"]:
                    warnings.append(f"Row {row_no}: parameter name differs from master. Master name will be used: {definition['parameter_name']}.")
                value = RecipeExcelImportExportManager._to_float(row.get("Parameter Value"), f"Parameter Value for {definition['parameter_name']}", errors, row_no)
                if value is not None:
                    min_v = definition.get("min_value")
                    max_v = definition.get("max_value")
                    if min_v is not None and value < float(min_v):
                        errors.append(f"Row {row_no}: {definition['parameter_name']} value {value} is below minimum {min_v}.")
                    if max_v is not None and value > float(max_v):
                        errors.append(f"Row {row_no}: {definition['parameter_name']} value {value} is above maximum {max_v}.")
                parsed_parameters.append({"definition": definition, "value": value})

            missing_defs = [r for r in definitions if r["id"] not in seen_defs]
            if missing_defs:
                errors.append(f"Missing {len(missing_defs)} required parameter row(s). Download a fresh template for this machine/stage.")

            cur.execute(
                """
                SELECT * FROM phase_control_master
                WHERE active = 1 AND stage_type = ?
                """,
                (target.get("stage_type"),),
            )
            phase_master = [dict(r) for r in cur.fetchall()]
            phase_by_id = {int(r["id"]): r for r in phase_master}
            phase_by_name = {str(r["phase_control_name"]).strip().upper(): r for r in phase_master}

            parsed_phase = []
            seen_lines = set()
            for row in phase_rows:
                row_no = row["__excel_row__"]
                line_no = RecipeExcelImportExportManager._to_int(row.get("Line No"), "Phase Line No", errors, row_no)
                if line_no is None:
                    continue
                if line_no < 1 or line_no > 12:
                    errors.append(f"Phase line number must be between 1 and 12 at row {row_no}.")
                    continue
                if line_no in seen_lines:
                    errors.append(f"Duplicate phase line number {line_no} at row {row_no}.")
                    continue
                seen_lines.add(line_no)
                phase_id = RecipeExcelImportExportManager._to_int(row.get("Phase Control ID"), "Phase Control ID", errors, row_no, required=False)
                phase_name = str(row.get("Phase Control Name") or "").strip()
                phase = phase_by_id.get(phase_id) if phase_id else phase_by_name.get(phase_name.upper())
                if not phase:
                    errors.append(f"Phase control not found for line {line_no} at row {row_no}.")
                    continue
                stop_option = str(row.get("Stop Option") or "No").strip().title()
                position_option = str(row.get("Position Option") or "No").strip().title()
                if stop_option not in {"Yes", "No"}:
                    errors.append(f"Stop Option must be Yes/No at row {row_no}.")
                if position_option not in {"Yes", "No"}:
                    errors.append(f"Position Option must be Yes/No at row {row_no}.")
                sequence_no = RecipeExcelImportExportManager._to_int(row.get("Sequence No"), "Sequence No", errors, row_no, required=False) or line_no
                parsed_phase.append({
                    "line_no": line_no,
                    "phase_control_id": int(phase["id"]),
                    "phase_control_name": phase["phase_control_name"],
                    "stop_option": stop_option,
                    "position_option": position_option,
                    "sequence_no": sequence_no,
                })
            if len(seen_lines) != 12:
                errors.append(f"Phase_Control must contain 12 unique line numbers. Found {len(seen_lines)}.")
            conn.close()
        else:
            target = {"machine_code": "-", "stage_type": "-"}
            parsed_parameters = []
            parsed_phase = []

        summary = {
            "recipe_code": recipe_code if 'recipe_code' in locals() else "",
            "recipe_name": recipe_name if 'recipe_name' in locals() else "",
            "version": version if 'version' in locals() else "",
            "machine_id": machine_id if 'machine_id' in locals() else "",
            "machine_code": target.get("machine_code", "-") if 'target' in locals() else "-",
            "stage_id": stage_id if 'stage_id' in locals() else "",
            "stage_type": target.get("stage_type", "-") if 'target' in locals() else "-",
            "is_test_only": is_test_only if 'is_test_only' in locals() else 0,
            "parameter_count": len(parsed_parameters) if 'parsed_parameters' in locals() else 0,
            "phase_count": len(parsed_phase) if 'parsed_phase' in locals() else 0,
        }
        return {
            "ok": not errors,
            "errors": errors,
            "warnings": warnings,
            "summary": summary,
            "parameters": parsed_parameters[:15] if 'parsed_parameters' in locals() else [],
            "phase_rows": parsed_phase[:12] if 'parsed_phase' in locals() else [],
            "_parsed_parameters": parsed_parameters if 'parsed_parameters' in locals() else [],
            "_parsed_phase": parsed_phase if 'parsed_phase' in locals() else [],
        }

    @staticmethod
    def import_pending_file(token, imported_by, user_role, reason=None, request_obj=None):
        file_path = RecipeExcelImportExportManager.pending_path(token)
        preview = RecipeExcelImportExportManager.preview_import(file_path)
        if not preview["ok"]:
            return False, None, preview

        summary = preview["summary"]
        parameters = preview["_parsed_parameters"]
        phase_rows = preview["_parsed_phase"]
        recipe_code = summary["recipe_code"]
        version = int(summary["version"])
        machine_id = int(summary["machine_id"])
        stage_id = int(summary["stage_id"])
        is_test_only = int(summary.get("is_test_only") or 0)

        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN")
            cur.execute(
                """
                INSERT INTO recipes
                (machine_id, stage_id, recipe_code, recipe_name, version, status, created_by, is_test_only)
                VALUES (?, ?, ?, ?, ?, 'DRAFT', ?, ?)
                """,
                (machine_id, stage_id, recipe_code, summary["recipe_name"], version, imported_by, is_test_only),
            )
            recipe_id = cur.lastrowid
            for item in parameters:
                definition = item["definition"]
                cur.execute(
                    """
                    INSERT INTO recipe_parameter_values
                    (recipe_id, parameter_definition_id, parameter_value, is_modified)
                    VALUES (?, ?, ?, 1)
                    """,
                    (recipe_id, definition["id"], item["value"]),
                )
            for row in phase_rows:
                cur.execute(
                    """
                    INSERT INTO recipe_phase_control
                    (recipe_id, line_no, phase_control_id, stop_option, position_option, sequence_no)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (recipe_id, row["line_no"], row["phase_control_id"], row["stop_option"], row["position_option"], row["sequence_no"]),
                )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            conn.close()
            preview["errors"] = [f"Database import failed: {exc}"]
            preview["ok"] = False
            return False, None, preview
        conn.close()

        RecipeStatusHistoryManager.add_history(
            recipe_id=recipe_id,
            recipe_code=recipe_code,
            old_status="IMPORT",
            new_status="DRAFT",
            changed_by=imported_by,
            remarks=reason or "Recipe imported from Excel template",
        )

        ctx = RecipeExcelImportExportManager._get_request_context(request_obj)
        AuditManager.log_event(
            username=imported_by,
            role=user_role,
            action="RECIPE_IMPORTED_EXCEL",
            change_source="WEB_RECIPE_IMPORT_EXPORT",
            recipe_code=recipe_code,
            recipe_version=version,
            record_id=recipe_id,
            old_value=os.path.basename(file_path),
            new_value=f"parameters={len(parameters)}; phase_rows={len(phase_rows)}; status=DRAFT",
            reason=reason or "Recipe imported from Excel template",
            **ctx,
        )

        try:
            os.remove(file_path)
        except OSError:
            pass

        return True, recipe_id, preview
