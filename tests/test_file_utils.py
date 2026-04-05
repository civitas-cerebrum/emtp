import json
import os
import pytest

from util.file_utils import atomic_write_json


class TestAtomicWriteJson:
    def test_writes_valid_json(self, tmp_path):
        path = str(tmp_path / "output.json")
        data = {"key": "value", "list": [1, 2, 3]}

        atomic_write_json(path, data)

        with open(path) as f:
            result = json.load(f)
        assert result == data

    def test_file_exists_after_write(self, tmp_path):
        path = str(tmp_path / "output.json")
        atomic_write_json(path, {"test": True})
        assert os.path.exists(path)

    def test_no_temp_file_remains(self, tmp_path):
        path = str(tmp_path / "output.json")
        atomic_write_json(path, {"test": True})
        assert not os.path.exists(path + ".tmp")

    def test_overwrites_existing_file(self, tmp_path):
        path = str(tmp_path / "output.json")
        atomic_write_json(path, {"version": 1})
        atomic_write_json(path, {"version": 2})

        with open(path) as f:
            result = json.load(f)
        assert result == {"version": 2}

    def test_creates_parent_dirs(self, tmp_path):
        path = str(tmp_path / "sub" / "dir" / "output.json")
        atomic_write_json(path, {"nested": True})

        with open(path) as f:
            result = json.load(f)
        assert result == {"nested": True}
