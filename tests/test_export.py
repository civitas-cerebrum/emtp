import csv
import json
import os
import pytest

from util.export import export_to_csv, export_dataset


class TestExportToCsv:
    def test_exports_flat_data(self, tmp_path):
        data = [
            {"q": "What is QA?", "a": "Quality assurance", "category": "Basics"},
            {"q": "What is TDD?", "a": "Test-driven dev", "category": "Testing"},
        ]
        output = str(tmp_path / "output.csv")
        export_to_csv(data, output)

        with open(output, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["q"] == "What is QA?"

    def test_flattens_nested_data(self, tmp_path):
        data = [{"q": "Q?", "a": "A", "messages": [{"role": "user", "content": "hi"}]}]
        output = str(tmp_path / "output.csv")
        export_to_csv(data, output)

        with open(output, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Nested list should be JSON-stringified
        assert '"role"' in rows[0]["messages"]

    def test_empty_data_no_file(self, tmp_path):
        output = str(tmp_path / "output.csv")
        export_to_csv([], output)
        assert not os.path.exists(output)


class TestExportDataset:
    def test_csv_format(self, tmp_path):
        input_path = str(tmp_path / "data.json")
        with open(input_path, "w") as f:
            json.dump([{"q": "Q?", "a": "A"}], f)

        output_path = str(tmp_path / "data.csv")
        export_dataset(input_path, output_path, "csv")
        assert os.path.exists(output_path)

    def test_invalid_format_raises(self, tmp_path):
        input_path = str(tmp_path / "data.json")
        with open(input_path, "w") as f:
            json.dump([], f)

        with pytest.raises(ValueError, match="Unsupported"):
            export_dataset(input_path, str(tmp_path / "data.xml"), "xml")
