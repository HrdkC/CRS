"""
P15 Second Stage Phase-Control Master Upgrade

Purpose:
- Create proper group-wise phase-control master for P15 SECOND_STAGE.
- Add 2 configurable second-stage phase groups:
    1. CAP_STRIP_SIDE
    2. BT_SIDE
- Add second-stage phase-control master options under each group.
- Add group columns to recipe_phase_control for future recipe selections.
- Keep old FIRST_STAGE recipe phase-control working with group MAIN.

Safe behavior:
- Idempotent: can be run multiple times.
- Does not delete existing data.
- Does not create any production/released recipe.
- Does not change existing first-stage phase-control selections except adding default group info.
"""

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "recipe.db"


P15_MACHINE_CODE = "P15"
SECOND_STAGE_TYPE = "SECOND_STAGE"


GROUPS = [
    {
        "phase_group_code": "CAP_STRIP_SIDE",
        "phase_group_name": "Cap Strip Side",
        "description": "P15 Second Stage Cap Strip Side phase-control group",
        "display_order": 1,
    },
    {
        "phase_group_code": "BT_SIDE",
        "phase_group_name": "B&T Side",
        "description": "P15 Second Stage Belt and Tread side phase-control group",
        "display_order": 2,
    },
]


PHASE_MASTERS = [
    # CAP STRIP SIDE
    {
        "phase_group_code": "CAP_STRIP_SIDE",
        "phase_group_name": "Cap Strip Side",
        "phase_control_name": "Apply CapStrip",
        "description": "Apply CapStrip",
        "display_order": 1,
    },
    {
        "phase_group_code": "CAP_STRIP_SIDE",
        "phase_group_name": "Cap Strip Side",
        "phase_control_name": "Apply Tread",
        "description": "Apply Tread",
        "display_order": 2,
    },

    # B&T SIDE
    {
        "phase_group_code": "BT_SIDE",
        "phase_group_name": "B&T Side",
        "phase_control_name": "Apply Belt 1",
        "description": "Apply Belt 1",
        "display_order": 1,
    },
    {
        "phase_group_code": "BT_SIDE",
        "phase_group_name": "B&T Side",
        "phase_control_name": "Apply Belt 2",
        "description": "Apply Belt 2",
        "display_order": 2,
    },
    {
        "phase_group_code": "BT_SIDE",
        "phase_group_name": "B&T Side",
        "phase_control_name": "Turn Table",
        "description": "Turn Table",
        "display_order": 3,
    },
    {
        "phase_group_code": "BT_SIDE",
        "phase_group_name": "B&T Side",
        "phase_control_name": "Apply Tread",
        "description": "Apply Tread",
        "display_order": 4,
    },
    {
        "phase_group_code": "BT_SIDE",
        "phase_group_name": "B&T Side",
        "phase_control_name": "Remove Belt Package",
        "description": "Remove Belt Package",
        "display_order": 5,
    },

]


def table_exists(cur, table_name: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def get_columns(cur, table_name: str) -> set[str]:
    rows = cur.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def add_column_if_missing(cur, table_name: str, column_name: str, column_sql: str) -> None:
    columns = get_columns(cur, table_name)
    if column_name not in columns:
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")
        print(f"Added column: {table_name}.{column_name}")
    else:
        print(f"Column already exists: {table_name}.{column_name}")


def resolve_p15_second_stage(cur) -> tuple[int, int]:
    machine = cur.execute(
        """
        SELECT id, machine_code
        FROM tbm_machines
        WHERE machine_code = ?
        """,
        (P15_MACHINE_CODE,),
    ).fetchone()

    if not machine:
        raise RuntimeError("P15 machine not found in tbm_machines.")

    stage = cur.execute(
        """
        SELECT id, machine_id, stage_type
        FROM machine_stages
        WHERE machine_id = ? AND stage_type = ?
        """,
        (machine["id"], SECOND_STAGE_TYPE),
    ).fetchone()

    if not stage:
        raise RuntimeError("P15 SECOND_STAGE not found in machine_stages.")

    return machine["id"], stage["id"]


def create_group_master_table(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS phase_control_group_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_stage_id INTEGER NOT NULL,
            stage_type TEXT NOT NULL,
            phase_group_code TEXT NOT NULL,
            phase_group_name TEXT NOT NULL,
            description TEXT,
            display_order INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(machine_stage_id, phase_group_code)
        )
        """
    )
    print("Checked/created table: phase_control_group_master")


def upgrade_phase_control_master_columns(cur) -> None:
    add_column_if_missing(
        cur,
        "phase_control_master",
        "machine_stage_id",
        "machine_stage_id INTEGER",
    )
    add_column_if_missing(
        cur,
        "phase_control_master",
        "phase_group_code",
        "phase_group_code TEXT DEFAULT 'MAIN'",
    )
    add_column_if_missing(
        cur,
        "phase_control_master",
        "phase_group_name",
        "phase_group_name TEXT DEFAULT 'Phase Control'",
    )

    cur.execute(
        """
        UPDATE phase_control_master
        SET phase_group_code = 'MAIN'
        WHERE phase_group_code IS NULL OR TRIM(phase_group_code) = ''
        """
    )
    cur.execute(
        """
        UPDATE phase_control_master
        SET phase_group_name = 'Phase Control'
        WHERE phase_group_name IS NULL OR TRIM(phase_group_name) = ''
        """
    )
    print("Backfilled existing phase_control_master rows as MAIN where required.")


def upgrade_recipe_phase_control_columns(cur) -> None:
    add_column_if_missing(
        cur,
        "recipe_phase_control",
        "phase_group_code",
        "phase_group_code TEXT DEFAULT 'MAIN'",
    )
    add_column_if_missing(
        cur,
        "recipe_phase_control",
        "phase_group_name",
        "phase_group_name TEXT DEFAULT 'Phase Control'",
    )
    add_column_if_missing(
        cur,
        "recipe_phase_control",
        "used",
        "used INTEGER DEFAULT 1",
    )

    cur.execute(
        """
        UPDATE recipe_phase_control
        SET phase_group_code = 'MAIN'
        WHERE phase_group_code IS NULL OR TRIM(phase_group_code) = ''
        """
    )
    cur.execute(
        """
        UPDATE recipe_phase_control
        SET phase_group_name = 'Phase Control'
        WHERE phase_group_name IS NULL OR TRIM(phase_group_name) = ''
        """
    )
    cur.execute(
        """
        UPDATE recipe_phase_control
        SET used = 1
        WHERE used IS NULL
        """
    )
    print("Backfilled existing recipe_phase_control rows as MAIN where required.")


def insert_group_masters(cur, machine_stage_id: int) -> None:
    for group in GROUPS:
        existing = cur.execute(
            """
            SELECT id
            FROM phase_control_group_master
            WHERE machine_stage_id = ? AND phase_group_code = ?
            """,
            (machine_stage_id, group["phase_group_code"]),
        ).fetchone()

        if existing:
            cur.execute(
                """
                UPDATE phase_control_group_master
                SET
                    stage_type = ?,
                    phase_group_name = ?,
                    description = ?,
                    display_order = ?,
                    active = 1
                WHERE id = ?
                """,
                (
                    SECOND_STAGE_TYPE,
                    group["phase_group_name"],
                    group["description"],
                    group["display_order"],
                    existing["id"],
                ),
            )
            print(f"Updated group master: {group['phase_group_code']}")
        else:
            cur.execute(
                """
                INSERT INTO phase_control_group_master (
                    machine_stage_id,
                    stage_type,
                    phase_group_code,
                    phase_group_name,
                    description,
                    display_order,
                    active
                )
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    machine_stage_id,
                    SECOND_STAGE_TYPE,
                    group["phase_group_code"],
                    group["phase_group_name"],
                    group["description"],
                    group["display_order"],
                ),
            )
            print(f"Inserted group master: {group['phase_group_code']}")


def insert_phase_masters(cur, machine_stage_id: int) -> None:
    for phase in PHASE_MASTERS:
        existing = cur.execute(
            """
            SELECT id
            FROM phase_control_master
            WHERE
                machine_stage_id = ?
                AND stage_type = ?
                AND phase_group_code = ?
                AND phase_control_name = ?
            """,
            (
                machine_stage_id,
                SECOND_STAGE_TYPE,
                phase["phase_group_code"],
                phase["phase_control_name"],
            ),
        ).fetchone()

        if existing:
            cur.execute(
                """
                UPDATE phase_control_master
                SET
                    phase_group_name = ?,
                    description = ?,
                    display_order = ?,
                    active = 1
                WHERE id = ?
                """,
                (
                    phase["phase_group_name"],
                    phase["description"],
                    phase["display_order"],
                    existing["id"],
                ),
            )
            print(
                f"Updated phase master: "
                f"{phase['phase_group_code']} -> {phase['phase_control_name']}"
            )
        else:
            cur.execute(
                """
                INSERT INTO phase_control_master (
                    machine_stage_id,
                    stage_type,
                    phase_group_code,
                    phase_group_name,
                    phase_control_name,
                    description,
                    display_order,
                    active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    machine_stage_id,
                    SECOND_STAGE_TYPE,
                    phase["phase_group_code"],
                    phase["phase_group_name"],
                    phase["phase_control_name"],
                    phase["description"],
                    phase["display_order"],
                ),
            )
            print(
                f"Inserted phase master: "
                f"{phase['phase_group_code']} -> {phase['phase_control_name']}"
            )


def verify(cur, machine_stage_id: int) -> None:
    group_rows = cur.execute(
        """
        SELECT
            machine_stage_id,
            stage_type,
            phase_group_code,
            phase_group_name,
            display_order,
            active
        FROM phase_control_group_master
        WHERE machine_stage_id = ?
        ORDER BY display_order
        """,
        (machine_stage_id,),
    ).fetchall()

    phase_rows = cur.execute(
        """
        SELECT
            machine_stage_id,
            stage_type,
            phase_group_code,
            phase_group_name,
            phase_control_name,
            display_order,
            active
        FROM phase_control_master
        WHERE
            machine_stage_id = ?
            AND stage_type = ?
            AND phase_group_code IN ('CAP_STRIP_SIDE', 'BT_SIDE')
        ORDER BY
            CASE phase_group_code
                WHEN 'CAP_STRIP_SIDE' THEN 1
                WHEN 'BT_SIDE' THEN 2
                ELSE 99
            END,
            display_order
        """,
        (machine_stage_id, SECOND_STAGE_TYPE),
    ).fetchall()

    print("\nVerification Summary")
    print("--------------------")
    print(f"P15 SECOND_STAGE machine_stage_id: {machine_stage_id}")
    print(f"Group master count: {len(group_rows)}")
    print(f"Phase master count: {len(phase_rows)}")

    print("\nGroups:")
    for row in group_rows:
        print(dict(row))

    print("\nPhase Masters:")
    for row in phase_rows:
        print(dict(row))

    if len(group_rows) != 3:
        raise RuntimeError("Verification failed: expected 3 phase groups.")

    if len(phase_rows) != 11:
        raise RuntimeError("Verification failed: expected 11 second-stage phase masters.")

    print("\nP15 Second Stage phase-control master upgrade completed successfully.")


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    print(f"Using database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.cursor()

        required_tables = [
            "tbm_machines",
            "machine_stages",
            "phase_control_master",
            "recipe_phase_control",
        ]
        for table in required_tables:
            if not table_exists(cur, table):
                raise RuntimeError(f"Required table missing: {table}")

        machine_id, machine_stage_id = resolve_p15_second_stage(cur)
        print(f"Resolved P15 machine_id      : {machine_id}")
        print(f"Resolved P15 SECOND_STAGE id : {machine_stage_id}")

        create_group_master_table(cur)
        upgrade_phase_control_master_columns(cur)
        upgrade_recipe_phase_control_columns(cur)
        insert_group_masters(cur, machine_stage_id)
        insert_phase_masters(cur, machine_stage_id)

        conn.commit()

        verify(cur, machine_stage_id)

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
