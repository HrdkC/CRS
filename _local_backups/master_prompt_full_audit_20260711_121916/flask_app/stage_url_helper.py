"""
CRS machine/stage URL and display helper.

User-facing standard:
    URL:     /<page>/P15/FS and /<page>/P15/SS
    Display: P15 - FS First Stage and P15 - SS Second Stage

Internal database IDs remain unchanged:
    tbm_machines.id, machine_stages.id
"""

from urllib.parse import urlencode

from database.database import get_connection


STAGE_TYPE_TO_CODE = {
    "FIRST_STAGE": "FS",
    "SECOND_STAGE": "SS",
}

STAGE_TYPE_TO_DISPLAY = {
    "FIRST_STAGE": "First Stage",
    "SECOND_STAGE": "Second Stage",
}

STAGE_CODE_TO_TYPE = {
    "FS": "FIRST_STAGE",
    "F_S": "FIRST_STAGE",
    "FIRST": "FIRST_STAGE",
    "FIRSTSTAGE": "FIRST_STAGE",
    "FIRST_STAGE": "FIRST_STAGE",
    "FIRST-STAGE": "FIRST_STAGE",
    "FIRST STAGE": "FIRST_STAGE",
    "SS": "SECOND_STAGE",
    "S_S": "SECOND_STAGE",
    "SECOND": "SECOND_STAGE",
    "SECONDSTAGE": "SECOND_STAGE",
    "SECOND_STAGE": "SECOND_STAGE",
    "SECOND-STAGE": "SECOND_STAGE",
    "SECOND STAGE": "SECOND_STAGE",
}


def _value(row, key, default=None):
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        value = row[key]
        return default if value is None else value
    except Exception:
        return getattr(row, key, default)


def _compact(value):
    return str(value or "").strip().upper().replace("-", "_").replace(" ", "_")


def normalize_stage_type(stage_value):
    """Accept FS/SS and old First_Stage/Second_Stage style values."""
    raw = str(stage_value or "").strip()
    if not raw:
        return ""

    direct = STAGE_CODE_TO_TYPE.get(raw.upper())
    if direct:
        return direct

    normalized = _compact(raw)
    direct = STAGE_CODE_TO_TYPE.get(normalized)
    if direct:
        return direct

    no_sep = normalized.replace("_", "")
    direct = STAGE_CODE_TO_TYPE.get(no_sep)
    if direct:
        return direct

    return normalized


def stage_url_code(stage_type):
    normalized = normalize_stage_type(stage_type)
    return STAGE_TYPE_TO_CODE.get(normalized, normalized)


def stage_display_name(stage_type):
    normalized = normalize_stage_type(stage_type)
    if normalized in STAGE_TYPE_TO_DISPLAY:
        return STAGE_TYPE_TO_DISPLAY[normalized]
    return normalized.replace("_", " ").title()


def machine_stage_display(machine_code=None, stage_type=None, context=None):
    if context is not None:
        machine_code = machine_code or _value(context, "machine_code")
        stage_type = stage_type or _value(context, "stage_type")

    machine_code = str(machine_code or "").strip()
    code = stage_url_code(stage_type)
    display = stage_display_name(stage_type)

    if machine_code and code and display:
        return f"{machine_code} - {code} {display}"
    if machine_code and display:
        return f"{machine_code} - {display}"
    return display or machine_code


def get_machine_stage_context_by_id(machine_id, stage_id, include_inactive=False):
    conn = get_connection()
    cur = conn.cursor()

    active_clause = ""
    if not include_inactive:
        active_clause = "AND COALESCE(m.active, 1) = 1 AND COALESCE(s.active, 1) = 1"

    row = cur.execute(
        f"""
        SELECT
            m.id AS machine_id,
            m.machine_code,
            m.description AS machine_description,
            s.id AS stage_id,
            s.stage_type,
            s.description AS stage_description
        FROM tbm_machines m
        INNER JOIN machine_stages s ON s.machine_id = m.id
        WHERE m.id = ? AND s.id = ? {active_clause}
        """,
        (machine_id, stage_id),
    ).fetchone()

    conn.close()
    if not row:
        return None

    ctx = dict(row)
    add_machine_stage_url_fields(ctx)
    return ctx


def get_machine_stage_context_by_code(machine_code, stage_code, include_inactive=False):
    stage_type = normalize_stage_type(stage_code)
    conn = get_connection()
    cur = conn.cursor()

    active_clause = ""
    if not include_inactive:
        active_clause = "AND COALESCE(m.active, 1) = 1 AND COALESCE(s.active, 1) = 1"

    row = cur.execute(
        f"""
        SELECT
            m.id AS machine_id,
            m.machine_code,
            m.description AS machine_description,
            s.id AS stage_id,
            s.stage_type,
            s.description AS stage_description
        FROM tbm_machines m
        INNER JOIN machine_stages s ON s.machine_id = m.id
        WHERE UPPER(m.machine_code) = UPPER(?)
          AND UPPER(s.stage_type) = UPPER(?)
          {active_clause}
        """,
        (machine_code, stage_type),
    ).fetchone()

    conn.close()
    if not row:
        return None

    ctx = dict(row)
    add_machine_stage_url_fields(ctx)
    return ctx


def add_machine_stage_url_fields(context):
    if not context:
        return context
    context["stage_url_code"] = stage_url_code(context.get("stage_type"))
    context["stage_display_name"] = stage_display_name(context.get("stage_type"))
    context["machine_stage_display"] = machine_stage_display(context=context)
    return context


def machine_stage_path(machine_code=None, stage_type=None, context=None):
    if context is not None:
        machine_code = machine_code or _value(context, "machine_code")
        stage_type = stage_type or _value(context, "stage_type")
    return f"{str(machine_code or '').strip()}/{stage_url_code(stage_type)}"


def machine_stage_url(prefix, context=None, machine_id=None, stage_id=None, machine_code=None, stage_type=None, query=None):
    """
    Build friendly machine/stage URL.

    Examples:
        machine_stage_url('/plc-tags', context=ctx)
        machine_stage_url('/recipes', machine_id=5, stage_id=12)
    """
    if context is None and (machine_code is None or stage_type is None) and machine_id and stage_id:
        context = get_machine_stage_context_by_id(machine_id, stage_id, include_inactive=True)

    if context is not None:
        machine_code = machine_code or _value(context, "machine_code")
        stage_type = stage_type or _value(context, "stage_type")

    if not machine_code or not stage_type:
        # Fallback only for non-stage-specific legacy data.
        if machine_id and stage_id:
            base = f"{prefix.rstrip('/')}/{machine_id}/{stage_id}"
        else:
            base = prefix.rstrip("/")
    else:
        base = f"{prefix.rstrip('/')}/{str(machine_code).strip()}/{stage_url_code(stage_type)}"

    if query:
        cleaned = {k: v for k, v in dict(query).items() if v is not None}
        if cleaned:
            return base + "?" + urlencode(cleaned)
    return base
