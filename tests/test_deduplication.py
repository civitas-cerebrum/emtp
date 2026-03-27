import pytest
from util.deduplication import deduplicate_qna, normalize_text


class TestNormalizeText:
    def test_lowercases(self):
        assert normalize_text("HELLO World") == "hello world"

    def test_strips_punctuation(self):
        assert normalize_text("What is QA?") == "what is qa"

    def test_collapses_whitespace(self):
        assert normalize_text("  too   many   spaces  ") == "too many spaces"

    def test_handles_empty(self):
        assert normalize_text("") == ""


class TestDeduplicateQna:
    def test_removes_exact_duplicates(self):
        dataset = [
            {"q": "What is QA?", "a": "Quality assurance"},
            {"q": "What is QA?", "a": "Quality assurance"},
            {"q": "What is testing?", "a": "Testing is..."},
        ]
        result, removed = deduplicate_qna(dataset)
        assert len(result) == 2
        assert removed == 1

    def test_removes_near_duplicates(self):
        dataset = [
            {"q": "What is QA?", "a": "Answer 1"},
            {"q": "what is qa", "a": "Answer 2"},
            {"q": "What is QA", "a": "Answer 3"},
        ]
        result, removed = deduplicate_qna(dataset)
        assert len(result) == 1
        assert removed == 2
        assert result[0]["a"] == "Answer 1"  # first occurrence wins

    def test_preserves_unique_questions(self):
        dataset = [
            {"q": "What is QA?", "a": "A1"},
            {"q": "What is testing?", "a": "A2"},
            {"q": "How does TDD work?", "a": "A3"},
        ]
        result, removed = deduplicate_qna(dataset)
        assert len(result) == 3
        assert removed == 0

    def test_empty_dataset(self):
        result, removed = deduplicate_qna([])
        assert result == []
        assert removed == 0

    def test_preserves_metadata(self):
        dataset = [
            {"q": "Q?", "a": "A", "category": "Test", "source": "round1", "source_file": "test.md"},
        ]
        result, removed = deduplicate_qna(dataset)
        assert result[0]["category"] == "Test"
        assert result[0]["source_file"] == "test.md"
