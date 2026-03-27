import os
import json
import csv

from util.utilities import get_logger

log = get_logger(__name__)


def export_to_csv(data: list[dict], output_path: str):
    """Export list of dicts to CSV."""
    if not data:
        log.warning("No data to export")
        return

    fieldnames = list(data[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            flat_row = {
                k: json.dumps(v) if isinstance(v, (dict, list)) else v
                for k, v in row.items()
            }
            writer.writerow(flat_row)

    log.info(f"Exported {len(data)} entries to CSV: {output_path}")


def export_to_parquet(data: list[dict], output_path: str):
    """Export list of dicts to Parquet. Requires pyarrow."""
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        log.error("pyarrow not installed. Install with: pip install pyarrow")
        raise

    flat_data = []
    for row in data:
        flat_row = {
            k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) if v is not None else ""
            for k, v in row.items()
        }
        flat_data.append(flat_row)

    if not flat_data:
        log.warning("No data to export")
        return

    table = pa.table({k: [row.get(k, "") for row in flat_data] for k in flat_data[0].keys()})
    pq.write_table(table, output_path)
    log.info(f"Exported {len(data)} entries to Parquet: {output_path}")


def export_dataset(input_path: str, output_path: str, fmt: str):
    """
    Export a JSON dataset to the specified format.

    Args:
        input_path: Path to source JSON file
        output_path: Path for output file
        fmt: "csv" or "parquet"
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if fmt == "csv":
        export_to_csv(data, output_path)
    elif fmt == "parquet":
        export_to_parquet(data, output_path)
    else:
        raise ValueError(f"Unsupported export format: {fmt}. Use 'csv' or 'parquet'.")
