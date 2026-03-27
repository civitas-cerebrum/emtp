import os
import json
import shutil
from datetime import datetime

from util.file_utils import atomic_write_json
from util.utilities import get_config, get_logger

log = get_logger(__name__)


def save_dataset_version(
    dataset_files: dict[str, str],
    versions_dir: str = "datasets",
    metadata: dict = None,
) -> str:
    """
    Save a versioned snapshot of dataset files.

    Args:
        dataset_files: {"name.json": "/path/to/file.json", ...}
        versions_dir: Base directory for versioned snapshots
        metadata: Additional metadata to save

    Returns:
        Path to the version directory
    """
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    version_dir = os.path.join(versions_dir, f"v_{timestamp}")
    os.makedirs(version_dir, exist_ok=True)

    for name, path in dataset_files.items():
        if os.path.exists(path):
            shutil.copy2(path, os.path.join(version_dir, name))
        else:
            log.warning(f"Dataset file not found, skipping: {path}")

    config = get_config()
    version_metadata = {
        "timestamp": datetime.now().isoformat(),
        "model_name": config.get("DEFAULT", "model_name", fallback="unknown"),
        "model_expertise": config.get("DEFAULT", "model_expertise", fallback="unknown"),
        "files": list(dataset_files.keys()),
    }
    if metadata:
        version_metadata.update(metadata)

    atomic_write_json(os.path.join(version_dir, "metadata.json"), version_metadata)
    log.info(f"Dataset version saved to {version_dir}")
    return version_dir


def list_versions(versions_dir: str = "datasets") -> list[dict]:
    """List all saved dataset versions with metadata."""
    versions = []
    if not os.path.exists(versions_dir):
        return versions

    for entry in sorted(os.listdir(versions_dir)):
        version_dir = os.path.join(versions_dir, entry)
        metadata_path = os.path.join(version_dir, "metadata.json")
        if os.path.isdir(version_dir) and os.path.exists(metadata_path):
            with open(metadata_path) as f:
                metadata = json.load(f)
            metadata["version_dir"] = version_dir
            versions.append(metadata)

    return versions
