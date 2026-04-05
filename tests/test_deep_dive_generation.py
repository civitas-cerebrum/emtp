import json
import os
import pytest
from unittest.mock import patch, MagicMock

from dataset.enrichment.deep_dive_generation import generate_deep_dive_questions, main
from util.llm_providers.base import LLMError


class TestGenerateDeepDiveQuestions:
    def test_generates_questions_from_markdown(self, tmp_path):
        md_dir = tmp_path / "datasources" / "test_category"
        md_dir.mkdir(parents=True)
        (md_dir / "doc1.md").write_text("# Test Document\nSome content about testing.")

        mock_client = MagicMock()
        mock_client.generate.return_value = [
            {"question": "What are the best testing practices?", "category": "Testing"},
            {"question": "How does TDD work?", "category": "Testing"},
        ]

        result = generate_deep_dive_questions(
            client=mock_client,
            scraped_content_dir=str(tmp_path / "datasources"),
            prompt="Generate questions about QA",
            model_name="gemma3:4b",
            min_content_length=0,
        )

        assert len(result) == 1
        assert result[0]["category"] == "Testing"
        assert len(result[0]["questions"]) == 2
        mock_client.generate.assert_called_once()

    def test_empty_directory_returns_empty(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        mock_client = MagicMock()

        result = generate_deep_dive_questions(
            client=mock_client,
            scraped_content_dir=str(empty_dir),
            prompt="test",
            model_name="gemma3:4b",
        )

        assert result == []
        mock_client.generate.assert_not_called()

    def test_skips_empty_markdown_files(self, tmp_path):
        md_dir = tmp_path / "datasources" / "cat"
        md_dir.mkdir(parents=True)
        (md_dir / "empty.md").write_text("")
        (md_dir / "whitespace.md").write_text("   \n  \n  ")

        mock_client = MagicMock()
        result = generate_deep_dive_questions(
            client=mock_client,
            scraped_content_dir=str(tmp_path / "datasources"),
            prompt="test",
            model_name="gemma3:4b",
        )

        assert result == []
        mock_client.generate.assert_not_called()

    def test_handles_llm_error(self, tmp_path):
        md_dir = tmp_path / "datasources" / "cat"
        md_dir.mkdir(parents=True)
        (md_dir / "doc.md").write_text("Some content")

        mock_client = MagicMock()
        mock_client.generate.side_effect = LLMError("API failed")

        result = generate_deep_dive_questions(
            client=mock_client,
            scraped_content_dir=str(tmp_path / "datasources"),
            prompt="test",
            model_name="gemma3:4b",
            min_content_length=0,
        )

        assert result == []

    def test_groups_questions_by_category(self, tmp_path):
        md_dir = tmp_path / "datasources" / "cat"
        md_dir.mkdir(parents=True)
        (md_dir / "doc1.md").write_text("Content 1")
        (md_dir / "doc2.md").write_text("Content 2")

        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            [{"question": "Q1", "category": "Alpha"}, {"question": "Q2", "category": "Beta"}],
            [{"question": "Q3", "category": "Alpha"}],
        ]

        result = generate_deep_dive_questions(
            client=mock_client,
            scraped_content_dir=str(tmp_path / "datasources"),
            prompt="test",
            model_name="gemma3:4b",
            min_content_length=0,
        )

        categories = {r["category"]: r["questions"] for r in result}
        assert len(categories["Alpha"]) == 2
        assert len(categories["Beta"]) == 1


class TestMain:
    def test_saves_questions_to_file(self, tmp_path):
        md_dir = tmp_path / "datasources" / "cat"
        md_dir.mkdir(parents=True)
        (md_dir / "doc.md").write_text("Content about QA")

        mock_client = MagicMock()
        mock_client.generate.return_value = [{"question": "Q1?", "category": "QA"}]

        with patch("dataset.enrichment.deep_dive_generation.create_llm_client") as mock_factory, \
             patch("dataset.enrichment.deep_dive_generation.get_emtp_directory") as mock_dir:
            mock_factory.return_value = mock_client
            mock_dir.return_value = str(tmp_path)

            result_path = main(
                scraped_content_dir="datasources",
                output_file="output.json",
                min_content_length=0,
            )

        assert os.path.exists(result_path)
        with open(result_path) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["category"] == "QA"
