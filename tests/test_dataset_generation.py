import json
import os
import pytest
from unittest.mock import patch, MagicMock

from dataset.enrichment.dataset_generation import generate_qna_dataset
from util.llm_providers.base import LLMError


class TestGenerateQnaDataset:
    def test_single_dir_string_backward_compat(self, tmp_path):
        md_dir = tmp_path / "datasources" / "testing"
        md_dir.mkdir(parents=True)
        (md_dir / "doc.md").write_text("Testing content")

        mock_client = MagicMock()
        mock_client.generate.return_value = {"qnaList": [{"q": "What is testing?", "a": "Testing is..."}]}

        result = generate_qna_dataset(
            client=mock_client,
            prompt="Generate QA about {domain_of_expertise}",
            model_expertise="QA",
            scraped_content_dirs=str(tmp_path / "datasources"),
            model_name="gemma3:4b",
            min_content_length=0,
        )

        assert len(result) == 1
        assert result[0]["q"] == "What is testing?"

    def test_multiple_dirs(self, tmp_path):
        dir1 = tmp_path / "datasources" / "cat1"
        dir1.mkdir(parents=True)
        (dir1 / "doc1.md").write_text("Content 1")
        dir2 = tmp_path / "datasources_deep" / "cat2"
        dir2.mkdir(parents=True)
        (dir2 / "doc2.md").write_text("Content 2")

        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            {"qnaList": [{"q": "Q1?", "a": "A1"}]},
            {"qnaList": [{"q": "Q2?", "a": "A2"}]},
        ]

        result = generate_qna_dataset(
            client=mock_client,
            prompt="Generate QA about {domain_of_expertise}",
            model_expertise="QA",
            scraped_content_dirs=[str(tmp_path / "datasources"), str(tmp_path / "datasources_deep")],
            model_name="gemma3:4b",
            min_content_length=0,
        )

        assert len(result) == 2

    def test_category_from_parent_dir(self, tmp_path):
        md_dir = tmp_path / "datasources" / "test_automation"
        md_dir.mkdir(parents=True)
        (md_dir / "doc.md").write_text("Content")

        mock_client = MagicMock()
        mock_client.generate.return_value = {"qnaList": [{"q": "Q?", "a": "A"}]}

        result = generate_qna_dataset(
            client=mock_client,
            prompt="Generate QA about {domain_of_expertise}",
            model_expertise="QA",
            scraped_content_dirs=str(tmp_path / "datasources"),
            model_name="gemma3:4b",
            min_content_length=0,
        )

        assert result[0]["category"] == "Test Automation"

    def test_source_label_round1(self, tmp_path):
        md_dir = tmp_path / "datasources" / "cat"
        md_dir.mkdir(parents=True)
        (md_dir / "doc.md").write_text("Content")

        mock_client = MagicMock()
        mock_client.generate.return_value = {"qnaList": [{"q": "Q?", "a": "A"}]}

        result = generate_qna_dataset(
            client=mock_client,
            prompt="Generate QA about {domain_of_expertise}",
            model_expertise="QA",
            scraped_content_dirs=str(tmp_path / "datasources"),
            model_name="gemma3:4b",
            min_content_length=0,
        )

        assert result[0]["source"] == "round1"

    def test_source_label_round2_for_deep_dirs(self, tmp_path):
        md_dir = tmp_path / "datasources_deep" / "cat"
        md_dir.mkdir(parents=True)
        (md_dir / "doc.md").write_text("Content")

        mock_client = MagicMock()
        mock_client.generate.return_value = {"qnaList": [{"q": "Q?", "a": "A"}]}

        result = generate_qna_dataset(
            client=mock_client,
            prompt="Generate QA about {domain_of_expertise}",
            model_expertise="QA",
            scraped_content_dirs=str(tmp_path / "datasources_deep"),
            model_name="gemma3:4b",
            min_content_length=0,
        )

        assert result[0]["source"] == "round2"

    def test_empty_dirs_returns_empty(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        mock_client = MagicMock()
        result = generate_qna_dataset(
            client=mock_client,
            prompt="test {domain_of_expertise}",
            model_expertise="QA",
            scraped_content_dirs=str(empty_dir),
            model_name="gemma3:4b",
        )

        assert result == []

    def test_handles_llm_error_continues(self, tmp_path):
        md_dir = tmp_path / "datasources" / "cat"
        md_dir.mkdir(parents=True)
        (md_dir / "bad.md").write_text("Bad content")
        (md_dir / "good.md").write_text("Good content")

        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            LLMError("fail"),
            {"qnaList": [{"q": "Q?", "a": "A"}]},
        ]

        result = generate_qna_dataset(
            client=mock_client,
            prompt="test {domain_of_expertise}",
            model_expertise="QA",
            scraped_content_dirs=str(tmp_path / "datasources"),
            model_name="gemma3:4b",
            min_content_length=0,
        )

        assert len(result) == 1

    def test_source_file_tracking(self, tmp_path):
        """Each Q&A pair includes the source markdown file path."""
        md_dir = tmp_path / "datasources" / "testing"
        md_dir.mkdir(parents=True)
        (md_dir / "doc.md").write_text("A" * 300)  # above min_content_length

        mock_client = MagicMock()
        mock_client.generate.return_value = {"qnaList": [{"q": "Q?", "a": "A"}]}

        result = generate_qna_dataset(
            client=mock_client,
            prompt="Generate QA about {domain_of_expertise}",
            model_expertise="QA",
            scraped_content_dirs=str(tmp_path / "datasources"),
            model_name="gemma3:4b",
            min_content_length=0,
        )

        assert "source_file" in result[0]
        assert "doc.md" in result[0]["source_file"]
