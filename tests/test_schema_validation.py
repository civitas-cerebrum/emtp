import json
import pytest

from util.schema_validation import (
    validate_questions_file,
    validate_qna_dataset,
    validate_conversation_dataset,
    ValidationError,
)


class TestValidateQuestionsFile:
    def test_valid_new_format(self, tmp_path):
        path = str(tmp_path / "questions.json")
        data = [{"category": "Test", "questions": ["Q1?", "Q2?"]}]
        with open(path, "w") as f:
            json.dump(data, f)

        validate_questions_file(path)  # should not raise

    def test_valid_legacy_format(self, tmp_path):
        path = str(tmp_path / "questions.json")
        data = {"Testing": ["Q1?", "Q2?"]}
        with open(path, "w") as f:
            json.dump(data, f)

        validate_questions_file(path)  # should not raise

    def test_invalid_missing_category(self, tmp_path):
        path = str(tmp_path / "questions.json")
        data = [{"questions": ["Q1?"]}]  # missing category
        with open(path, "w") as f:
            json.dump(data, f)

        with pytest.raises(ValidationError, match="missing 'category'"):
            validate_questions_file(path)

    def test_invalid_not_list_or_dict(self, tmp_path):
        path = str(tmp_path / "questions.json")
        with open(path, "w") as f:
            json.dump("just a string", f)

        with pytest.raises(ValidationError, match="must be a list or dict"):
            validate_questions_file(path)


class TestValidateQnaDataset:
    def test_valid_dataset(self, tmp_path):
        path = str(tmp_path / "qna.json")
        data = [{"q": "Q?", "a": "A", "category": "Test"}]
        with open(path, "w") as f:
            json.dump(data, f)

        validate_qna_dataset(path)  # should not raise

    def test_missing_q_key(self, tmp_path):
        path = str(tmp_path / "qna.json")
        data = [{"a": "A"}]
        with open(path, "w") as f:
            json.dump(data, f)

        with pytest.raises(ValidationError, match="missing 'q' or 'a'"):
            validate_qna_dataset(path)

    def test_not_a_list(self, tmp_path):
        path = str(tmp_path / "qna.json")
        with open(path, "w") as f:
            json.dump({"q": "Q?", "a": "A"}, f)

        with pytest.raises(ValidationError, match="must be a list"):
            validate_qna_dataset(path)


class TestValidateConversationDataset:
    def test_valid_dataset(self, tmp_path):
        path = str(tmp_path / "conv.json")
        data = [{"messages": [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}]}]
        with open(path, "w") as f:
            json.dump(data, f)

        validate_conversation_dataset(path)  # should not raise

    def test_missing_messages(self, tmp_path):
        path = str(tmp_path / "conv.json")
        data = [{"other": "data"}]
        with open(path, "w") as f:
            json.dump(data, f)

        with pytest.raises(ValidationError, match="missing 'messages'"):
            validate_conversation_dataset(path)

    def test_empty_messages(self, tmp_path):
        path = str(tmp_path / "conv.json")
        data = [{"messages": []}]
        with open(path, "w") as f:
            json.dump(data, f)

        with pytest.raises(ValidationError, match="empty or invalid"):
            validate_conversation_dataset(path)
