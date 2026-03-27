import json
import pytest

from dataset.acquisition.save_datasource.json_parser import (
    extract_urls_from_json_file,
    parse_json_file,
    is_valid_url,
    extract_urls_from_data,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# is_valid_url
# ---------------------------------------------------------------------------

class TestIsValidUrl:
    def test_valid_http_url(self):
        assert is_valid_url("http://example.com") is True

    def test_valid_https_url(self):
        assert is_valid_url("https://example.com/path?q=1") is True

    def test_missing_scheme_is_invalid(self):
        assert is_valid_url("example.com") is False

    def test_missing_netloc_is_invalid(self):
        assert is_valid_url("https://") is False

    def test_empty_string_is_invalid(self):
        assert is_valid_url("") is False

    def test_plain_word_is_invalid(self):
        assert is_valid_url("notaurl") is False


# ---------------------------------------------------------------------------
# parse_json_file
# ---------------------------------------------------------------------------

class TestParseJsonFile:
    def test_parses_valid_json_file(self, tmp_path):
        f = tmp_path / "data.json"
        write_json(f, {"key": "value"})

        result = parse_json_file(str(f))

        assert result == {"key": "value"}

    def test_raises_file_not_found(self, tmp_path):
        missing = str(tmp_path / "missing.json")

        with pytest.raises(FileNotFoundError):
            parse_json_file(missing)

    def test_raises_value_error_for_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{ not valid json }", encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_json_file(str(f))

    def test_raises_value_error_for_directory(self, tmp_path):
        with pytest.raises(ValueError, match="not a file"):
            parse_json_file(str(tmp_path))


# ---------------------------------------------------------------------------
# extract_urls_from_data
# ---------------------------------------------------------------------------

class TestExtractUrlsFromData:
    def test_extracts_url_from_flat_dict(self):
        data = {"url": "https://example.com", "title": "Example"}
        result = extract_urls_from_data(data)
        assert "https://example.com" in result

    def test_extracts_urls_from_list(self):
        data = ["https://a.com", "https://b.com", "not_a_url"]
        result = extract_urls_from_data(data)
        assert result == ["https://a.com", "https://b.com"]

    def test_extracts_urls_recursively(self):
        data = {"nested": {"deep": "https://deep.example.com"}}
        result = extract_urls_from_data(data)
        assert "https://deep.example.com" in result

    def test_returns_empty_for_non_url_strings(self):
        result = extract_urls_from_data("just a plain string")
        assert result == []

    def test_returns_empty_for_empty_dict(self):
        assert extract_urls_from_data({}) == []


# ---------------------------------------------------------------------------
# extract_urls_from_json_file  — new list format (pipeline output)
# ---------------------------------------------------------------------------

class TestExtractUrlsFromJsonFileNewFormat:
    def test_extracts_urls_with_metadata(self, tmp_path):
        data = [
            {
                "category": "Science",
                "question": "What is gravity?",
                "urls": ["https://physics.org/gravity", "https://nasa.gov/gravity"],
            }
        ]
        f = tmp_path / "urls.json"
        write_json(f, data)

        result = extract_urls_from_json_file(str(f))

        assert len(result) == 2
        urls = {r["url"] for r in result}
        assert "https://physics.org/gravity" in urls
        assert "https://nasa.gov/gravity" in urls

    def test_metadata_fields_populated_correctly(self, tmp_path):
        data = [
            {
                "category": "Tech",
                "question": "How does DNS work?",
                "urls": ["https://cloudflare.com/dns"],
            }
        ]
        f = tmp_path / "urls.json"
        write_json(f, data)

        result = extract_urls_from_json_file(str(f))

        assert len(result) == 1
        entry = result[0]
        assert entry["url"] == "https://cloudflare.com/dns"
        assert entry["categoryName"] == "Tech"
        assert entry["question"] == "How does DNS work?"
        assert entry["is_pdf"] is False

    def test_empty_urls_list_produces_no_entries(self, tmp_path):
        data = [{"category": "Empty", "question": "No results", "urls": []}]
        f = tmp_path / "urls.json"
        write_json(f, data)

        result = extract_urls_from_json_file(str(f))

        assert result == []

    def test_invalid_urls_are_excluded(self, tmp_path):
        data = [
            {
                "category": "Bad",
                "question": "q",
                "urls": ["not_a_url", "also bad", "https://valid.com"],
            }
        ]
        f = tmp_path / "urls.json"
        write_json(f, data)

        result = extract_urls_from_json_file(str(f))

        assert len(result) == 1
        assert result[0]["url"] == "https://valid.com"

    def test_duplicate_urls_are_deduplicated(self, tmp_path):
        data = [
            {
                "category": "Dup",
                "question": "q1",
                "urls": ["https://example.com/page"],
            },
            {
                "category": "Dup",
                "question": "q2",
                "urls": ["https://example.com/page"],
            },
        ]
        f = tmp_path / "urls.json"
        write_json(f, data)

        result = extract_urls_from_json_file(str(f))

        assert len(result) == 1

    def test_missing_category_defaults_to_uncategorized(self, tmp_path):
        data = [{"question": "q", "urls": ["https://example.com"]}]
        f = tmp_path / "urls.json"
        write_json(f, data)

        result = extract_urls_from_json_file(str(f))

        assert result[0]["categoryName"] == "Uncategorized"

    def test_multiple_categories(self, tmp_path):
        data = [
            {"category": "A", "question": "q1", "urls": ["https://a.com"]},
            {"category": "B", "question": "q2", "urls": ["https://b.com"]},
        ]
        f = tmp_path / "urls.json"
        write_json(f, data)

        result = extract_urls_from_json_file(str(f))

        assert len(result) == 2
        category_names = {r["categoryName"] for r in result}
        assert category_names == {"A", "B"}


# ---------------------------------------------------------------------------
# extract_urls_from_json_file  — legacy dict format
# ---------------------------------------------------------------------------

class TestExtractUrlsFromJsonFileLegacyFormat:
    def test_extracts_urls_from_legacy_format(self, tmp_path):
        data = {
            "Science": [
                {"url": "https://physics.org", "question": "What is gravity?", "is_pdf": False}
            ]
        }
        f = tmp_path / "legacy.json"
        write_json(f, data)

        result = extract_urls_from_json_file(str(f))

        assert len(result) == 1
        assert result[0]["url"] == "https://physics.org"
        assert result[0]["categoryName"] == "Science"
        assert result[0]["is_pdf"] is False

    def test_pdf_flag_preserved_in_legacy_format(self, tmp_path):
        data = {
            "Docs": [
                {"url": "https://example.com/doc.pdf", "question": "q", "is_pdf": True}
            ]
        }
        f = tmp_path / "legacy.json"
        write_json(f, data)

        result = extract_urls_from_json_file(str(f))

        assert result[0]["is_pdf"] is True

    def test_invalid_url_excluded_in_legacy_format(self, tmp_path):
        data = {
            "Bad": [
                {"url": "not_valid", "question": "q", "is_pdf": False}
            ]
        }
        f = tmp_path / "legacy.json"
        write_json(f, data)

        result = extract_urls_from_json_file(str(f))

        assert result == []
