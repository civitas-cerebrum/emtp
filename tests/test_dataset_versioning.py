import json
import os
import pytest
from unittest.mock import patch

from util.dataset_versioning import save_dataset_version, list_versions


class TestSaveDatasetVersion:
    def test_creates_version_directory(self, tmp_path):
        qna_file = tmp_path / "qna.json"
        qna_file.write_text(json.dumps([{"q": "Q?", "a": "A"}]))

        with patch("util.dataset_versioning.get_config") as mock_config:
            mock_config.return_value.get = lambda s, k, fallback=None: fallback

            version_dir = save_dataset_version(
                {"qna_dataset.json": str(qna_file)},
                versions_dir=str(tmp_path / "datasets"),
            )

        assert os.path.isdir(version_dir)
        assert os.path.exists(os.path.join(version_dir, "qna_dataset.json"))
        assert os.path.exists(os.path.join(version_dir, "metadata.json"))

    def test_metadata_includes_timestamp(self, tmp_path):
        qna_file = tmp_path / "qna.json"
        qna_file.write_text("[]")

        with patch("util.dataset_versioning.get_config") as mock_config:
            mock_config.return_value.get = lambda s, k, fallback=None: fallback

            version_dir = save_dataset_version(
                {"qna.json": str(qna_file)},
                versions_dir=str(tmp_path / "datasets"),
            )

        with open(os.path.join(version_dir, "metadata.json")) as f:
            meta = json.load(f)
        assert "timestamp" in meta
        assert "files" in meta

    def test_custom_metadata(self, tmp_path):
        qna_file = tmp_path / "qna.json"
        qna_file.write_text("[]")

        with patch("util.dataset_versioning.get_config") as mock_config:
            mock_config.return_value.get = lambda s, k, fallback=None: fallback

            version_dir = save_dataset_version(
                {"qna.json": str(qna_file)},
                versions_dir=str(tmp_path / "datasets"),
                metadata={"qna_count": 42},
            )

        with open(os.path.join(version_dir, "metadata.json")) as f:
            meta = json.load(f)
        assert meta["qna_count"] == 42

    def test_skips_missing_files(self, tmp_path):
        with patch("util.dataset_versioning.get_config") as mock_config:
            mock_config.return_value.get = lambda s, k, fallback=None: fallback

            version_dir = save_dataset_version(
                {"missing.json": str(tmp_path / "nonexistent.json")},
                versions_dir=str(tmp_path / "datasets"),
            )

        assert not os.path.exists(os.path.join(version_dir, "missing.json"))


class TestListVersions:
    def test_lists_versions(self, tmp_path):
        # Create two versions
        for i in range(2):
            v_dir = tmp_path / "datasets" / f"v_{i}"
            v_dir.mkdir(parents=True)
            with open(v_dir / "metadata.json", "w") as f:
                json.dump({"timestamp": f"2026-03-26T{i}", "files": []}, f)

        versions = list_versions(str(tmp_path / "datasets"))
        assert len(versions) == 2

    def test_empty_dir(self, tmp_path):
        versions = list_versions(str(tmp_path / "nonexistent"))
        assert versions == []
