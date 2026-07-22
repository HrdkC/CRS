"""Read-only diagnosis for a CRS recipe restore buffer.

This utility never writes a PLC tag. It compares the selected recipe's database
payload with the configured RECIPE_DATA tag immediately and again after a delay
using a fresh LogixDriver connection.
"""

import argparse
import os
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pycomm3 import LogixDriver

from database.plc_buffer_operation_manager import PLCBufferOperationManager
from database.plc_download_preparation_manager import PLCDownloadPreparationManager
from database.recipe_manager import RecipeManager
from database.recipe_parameter_value_manager import RecipeParameterValueManager


def _read_array(plc, tag_name, size):
    result = plc.read(f"{tag_name}{{{size}}}")
    error = getattr(result, "error", None)
    value = getattr(result, "value", None)
    if result is None or error:
        raise RuntimeError(f"{tag_name} read failed: {error}")
    payload = PLCBufferOperationManager.normalize_payload(value, payload_size=size)
    if payload is None:
        raise RuntimeError(f"{tag_name} did not return {size} numeric values")
    return payload


def _print_preview(label, values, count=8):
    preview = values[: min(count, len(values))]
    print(f"{label}: {preview}")


def main():
    parser = argparse.ArgumentParser(
        description="Read-only CRS recipe buffer persistence diagnosis"
    )
    parser.add_argument("--recipe-id", type=int, required=True)
    parser.add_argument("--plc-id", type=int)
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()

    if os.getenv("CRS_ALLOW_PLC_COMMUNICATION", "").strip().upper() != "YES":
        raise SystemExit(
            "Set CRS_ALLOW_PLC_COMMUNICATION=YES in this PowerShell session. "
            "This command performs PLC reads only."
        )

    recipe = RecipeManager.get_recipe_by_id(args.recipe_id)
    if not recipe:
        raise SystemExit(f"Recipe {args.recipe_id} was not found")

    plc = PLCDownloadPreparationManager.get_plc_for_recipe(
        recipe=recipe,
        plc_id=args.plc_id,
    )
    if not plc:
        raise SystemExit("No active PLC is assigned to this recipe stage")

    payload_size = PLCDownloadPreparationManager.get_payload_size_for_recipe(recipe)
    if not payload_size:
        raise SystemExit("RECIPE_DATA array size is not configured")

    source_tag = PLCBufferOperationManager.require_array_tag(
        recipe,
        PLCBufferOperationManager.SOURCE_PURPOSE,
        "CRS recipe buffer",
    )
    values = RecipeParameterValueManager.get_recipe_values(recipe["id"])
    expected = PLCBufferOperationManager.build_database_payload(
        values,
        payload_size=payload_size,
    )

    print("CRS recipe restore buffer diagnosis")
    print(f"Recipe: {recipe['recipe_code']} (ID {recipe['id']})")
    print(f"PLC: {plc['plc_name']} @ {plc['ip_address']}")
    print(f"Configured tag: {source_tag['tag_name']} REAL[{payload_size}]")
    _print_preview("Database expected", expected)

    with LogixDriver(plc["ip_address"]) as connection:
        info = getattr(connection, "info", {}) or {}
        print(
            "Controller identity: "
            f"name={info.get('name')}, device={info.get('device_type')}, "
            f"revision={info.get('revision')}, serial={info.get('serial')}"
        )
        tag_definition = (getattr(connection, "tags", {}) or {}).get(
            source_tag["tag_name"]
        )
        if tag_definition:
            print(
                "Tag metadata: "
                f"type={tag_definition.get('data_type_name')}, "
                f"dimensions={tag_definition.get('dimensions')}, "
                f"external_access={tag_definition.get('external_access')}, "
                f"alias={tag_definition.get('alias')}"
            )
        first = _read_array(connection, source_tag["tag_name"], payload_size)

    _print_preview("PLC read now", first)
    first_compare = PLCBufferOperationManager.compare_payloads(expected, first)
    print(f"Immediate match: {first_compare['matched']}")
    if not first_compare["matched"]:
        print(f"First mismatch: {first_compare['mismatches'][0]}")

    delay = max(0.2, float(args.delay))
    print(f"Waiting {delay:.1f} second(s), then opening a fresh PLC connection...")
    time.sleep(delay)

    with LogixDriver(plc["ip_address"]) as connection:
        second = _read_array(connection, source_tag["tag_name"], payload_size)

    _print_preview("PLC read after delay", second)
    second_compare = PLCBufferOperationManager.compare_payloads(expected, second)
    print(f"Persistent match: {second_compare['matched']}")
    if not second_compare["matched"]:
        print(f"First mismatch: {second_compare['mismatches'][0]}")
        print(
            "Conclusion: the configured CRS buffer does not contain or retain "
            "the database recipe. Check PLC logic/SCADA writes, controller/tag "
            "scope, and the exact PLC being monitored."
        )
        raise SystemExit(2)

    print("Conclusion: the configured CRS buffer matches the database recipe.")


if __name__ == "__main__":
    main()
