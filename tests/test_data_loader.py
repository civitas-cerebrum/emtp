import json
import os
import pytest

from dataset.acquisition.retrieve_url.data_loader import get_questions


class TestGetQuestionsNewFormat:
    """Tests for the new list-of-blocks format."""

    def test_string_questions_are_normalized(self, tmp_path):
        data = [{"category": "Science", "questions": ["What is gravity?", "What is light?"]}]
        path = tmp_path / "qa.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = get_questions(str(path))

        assert "Science" in result
        assert result["Science"] == [
            {"question": "What is gravity?", "dorks": None, "urls": None},
            {"question": "What is light?", "dorks": None, "urls": None},
        ]

    def test_dict_questions_preserve_fields(self, tmp_path):
        data = [
            {
                "category": "Tech",
                "questions": [
                    {"question": "How does DNS work?", "dorks": "site:edu", "urls": None},
                    {"question": "What is TCP?", "dorks": None, "urls": ["https://example.com"]},
                ],
            }
        ]
        path = tmp_path / "qa.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = get_questions(str(path))

        assert result["Tech"][0] == {"question": "How does DNS work?", "dorks": "site:edu", "urls": None}
        assert result["Tech"][1] == {
            "question": "What is TCP?",
            "dorks": None,
            "urls": ["https://example.com"],
        }

    def test_missing_dorks_and_urls_default_to_none(self, tmp_path):
        data = [{"category": "History", "questions": [{"question": "Ancient Rome"}]}]
        path = tmp_path / "qa.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = get_questions(str(path))

        assert result["History"][0] == {"question": "Ancient Rome", "dorks": None, "urls": None}

    def test_multiple_categories(self, tmp_path):
        data = [
            {"category": "A", "questions": ["q1"]},
            {"category": "B", "questions": ["q2"]},
        ]
        path = tmp_path / "qa.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = get_questions(str(path))

        assert set(result.keys()) == {"A", "B"}

    def test_missing_category_key_raises_value_error(self, tmp_path):
        data = [{"questions": ["q1"]}]
        path = tmp_path / "qa.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        with pytest.raises(ValueError, match="Missing 'category'"):
            get_questions(str(path))

    def test_invalid_question_item_raises_value_error(self, tmp_path):
        data = [{"category": "Bad", "questions": [42]}]
        path = tmp_path / "qa.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        with pytest.raises(ValueError):
            get_questions(str(path))

    def test_dict_question_uses_q_alias(self, tmp_path):
        data = [{"category": "Alias", "questions": [{"q": "What is entropy?"}]}]
        path = tmp_path / "qa.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = get_questions(str(path))

        assert result["Alias"][0]["question"] == "What is entropy?"

    def test_empty_questions_list(self, tmp_path):
        data = [{"category": "Empty", "questions": []}]
        path = tmp_path / "qa.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = get_questions(str(path))

        assert result["Empty"] == []


class TestGetQuestionsLegacyFormat:
    """Tests for the legacy dict-of-lists format."""

    def test_string_questions_normalized(self, tmp_path):
        data = {"Science": ["What is gravity?", "What is light?"]}
        path = tmp_path / "qa.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = get_questions(str(path))

        assert result["Science"] == [
            {"question": "What is gravity?", "dorks": None, "urls": None},
            {"question": "What is light?", "dorks": None, "urls": None},
        ]

    def test_dict_questions_preserved(self, tmp_path):
        data = {"Tech": [{"question": "How does DNS work?", "dorks": "site:edu", "urls": None}]}
        path = tmp_path / "qa.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = get_questions(str(path))

        assert result["Tech"][0] == {"question": "How does DNS work?", "dorks": "site:edu", "urls": None}

    def test_mixed_string_and_dict_questions(self, tmp_path):
        data = {"Mixed": ["plain string", {"question": "dict question"}]}
        path = tmp_path / "qa.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = get_questions(str(path))

        assert result["Mixed"][0] == {"question": "plain string", "dorks": None, "urls": None}
        assert result["Mixed"][1] == {"question": "dict question", "dorks": None, "urls": None}

    def test_dict_question_uses_q_alias(self, tmp_path):
        data = {"Alias": [{"q": "What is entropy?"}]}
        path = tmp_path / "qa.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = get_questions(str(path))

        assert result["Alias"][0]["question"] == "What is entropy?"

    def test_invalid_question_item_raises_value_error(self, tmp_path):
        data = {"Bad": [99]}
        path = tmp_path / "qa.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        with pytest.raises(ValueError):
            get_questions(str(path))


class TestGetQuestionsInvalidStructure:
    def test_top_level_string_raises_value_error(self, tmp_path):
        path = tmp_path / "qa.json"
        path.write_text(json.dumps("just a string"), encoding="utf-8")

        with pytest.raises(ValueError, match="Unsupported JSON structure"):
            get_questions(str(path))

    def test_top_level_number_raises_value_error(self, tmp_path):
        path = tmp_path / "qa.json"
        path.write_text("42", encoding="utf-8")

        with pytest.raises(ValueError, match="Unsupported JSON structure"):
            get_questions(str(path))


class TestGetQuestionsPathResolution:
    def test_absolute_path_is_used_directly(self, tmp_path):
        data = [{"category": "Test", "questions": ["q1"]}]
        path = tmp_path / "absolute.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = get_questions(str(path))

        assert "Test" in result

    def test_relative_path_resolved_to_script_dir(self, tmp_path, monkeypatch):
        """Relative paths should be resolved relative to data_loader.py's directory."""
        import dataset.acquisition.retrieve_url.data_loader as dl

        data = [{"category": "Relative", "questions": ["q1"]}]
        script_dir = os.path.dirname(dl.__file__)
        target = os.path.join(script_dir, "test_relative_temp.json")

        try:
            with open(target, "w", encoding="utf-8") as f:
                json.dump(data, f)
            result = get_questions("test_relative_temp.json")
            assert "Relative" in result
        finally:
            if os.path.exists(target):
                os.remove(target)
