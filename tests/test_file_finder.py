import os
import pytest

from dataset.acquisition.save_datasource.file_finder import find_json_files, validate_directory


class TestFindJsonFiles:
    def test_finds_json_files_in_flat_directory(self, tmp_path):
        (tmp_path / "a.json").write_text("{}")
        (tmp_path / "b.json").write_text("{}")

        result = find_json_files(str(tmp_path))

        assert len(result) == 2
        assert all(f.endswith(".json") for f in result)

    def test_finds_json_files_recursively(self, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        (tmp_path / "root.json").write_text("{}")
        (sub / "nested.json").write_text("{}")

        result = find_json_files(str(tmp_path))

        assert len(result) == 2
        assert any("root.json" in f for f in result)
        assert any("nested.json" in f for f in result)

    def test_returns_empty_list_for_empty_directory(self, tmp_path):
        result = find_json_files(str(tmp_path))
        assert result == []

    def test_ignores_non_json_files(self, tmp_path):
        (tmp_path / "data.json").write_text("{}")
        (tmp_path / "readme.txt").write_text("hello")
        (tmp_path / "script.py").write_text("print('hi')")

        result = find_json_files(str(tmp_path))

        assert len(result) == 1
        assert result[0].endswith("data.json")

    def test_returns_sorted_list(self, tmp_path):
        (tmp_path / "c.json").write_text("{}")
        (tmp_path / "a.json").write_text("{}")
        (tmp_path / "b.json").write_text("{}")

        result = find_json_files(str(tmp_path))

        assert result == sorted(result)

    def test_raises_for_nonexistent_directory(self, tmp_path):
        nonexistent = str(tmp_path / "does_not_exist")

        with pytest.raises(ValueError, match="does not exist"):
            find_json_files(nonexistent)

    def test_raises_for_file_path(self, tmp_path):
        f = tmp_path / "file.json"
        f.write_text("{}")

        with pytest.raises(ValueError, match="not a directory"):
            find_json_files(str(f))

    def test_deeply_nested_json_files(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "deep.json").write_text("{}")

        result = find_json_files(str(tmp_path))

        assert len(result) == 1
        assert "deep.json" in result[0]


class TestValidateDirectory:
    def test_returns_true_for_existing_directory(self, tmp_path):
        assert validate_directory(str(tmp_path)) is True

    def test_returns_false_for_nonexistent_path(self, tmp_path):
        nonexistent = str(tmp_path / "no_such_dir")
        assert validate_directory(nonexistent) is False

    def test_returns_false_for_file_path(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("content")
        assert validate_directory(str(f)) is False

    def test_returns_true_for_nested_existing_directory(self, tmp_path):
        nested = tmp_path / "level1" / "level2"
        nested.mkdir(parents=True)
        assert validate_directory(str(nested)) is True
