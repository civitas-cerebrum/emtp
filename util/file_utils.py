import os
import json


def atomic_write_json(path: str, data, indent: int = 4):
    """Write JSON to a temp file then atomically rename.

    Prevents data corruption if the process crashes mid-write.
    """
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)
    os.replace(tmp_path, path)
