import json
import os
import pytest
from unittest.mock import patch, MagicMock


class TestRunDeepDive:
    def test_full_deep_dive_flow(self, tmp_path):
        """Runs all 3 stages: generate questions, URL retrieval, datasource capture."""
        datasources_dir = str(tmp_path / "datasources")
        urls_deep_dir = str(tmp_path / "urls_deep")
        datasources_deep_dir = str(tmp_path / "datasources_deep")

        questions_file = str(tmp_path / "deep_dive_questions.json")
        questions_data = [
            {"category": "Testing", "questions": ["Q1?", "Q2?"]}
        ]

        with patch("main.generate_deep_dive_questions") as mock_gen, \
             patch("main.run_url_retrieval") as mock_url, \
             patch("main.run_datasource_capture") as mock_ds:

            # generate_deep_dive_questions returns path to questions file
            mock_gen.return_value = questions_file
            # Write the questions file so run_deep_dive can read it
            os.makedirs(os.path.dirname(questions_file), exist_ok=True)
            with open(questions_file, "w") as f:
                json.dump(questions_data, f)

            mock_ds.return_value = []

            from main import run_deep_dive
            result = run_deep_dive(
                datasources_dir=datasources_dir,
                urls_deep_dir=urls_deep_dir,
                datasources_deep_dir=datasources_deep_dir,
            )

        assert result == datasources_deep_dir
        mock_gen.assert_called_once_with(scraped_content_dir=datasources_dir)
        mock_url.assert_called_once()
        mock_ds.assert_called_once()

    def test_skips_round2_when_no_questions(self, tmp_path):
        """Returns None and skips scraping when no questions generated."""
        questions_file = str(tmp_path / "empty_questions.json")

        with patch("main.generate_deep_dive_questions") as mock_gen, \
             patch("main.run_url_retrieval") as mock_url, \
             patch("main.run_datasource_capture") as mock_ds:

            mock_gen.return_value = questions_file
            os.makedirs(os.path.dirname(questions_file), exist_ok=True)
            with open(questions_file, "w") as f:
                json.dump([], f)  # empty questions

            from main import run_deep_dive
            result = run_deep_dive(
                datasources_dir=str(tmp_path / "datasources"),
                urls_deep_dir=str(tmp_path / "urls_deep"),
                datasources_deep_dir=str(tmp_path / "datasources_deep"),
            )

        assert result is None
        mock_url.assert_not_called()
        mock_ds.assert_not_called()

    def test_clears_previous_outputs(self, tmp_path):
        """Clears urls_deep and datasources_deep dirs before running."""
        urls_deep = tmp_path / "urls_deep"
        datasources_deep = tmp_path / "datasources_deep"
        urls_deep.mkdir()
        datasources_deep.mkdir()
        (urls_deep / "old_file.json").write_text("{}")
        (datasources_deep / "old_file.md").write_text("old")

        questions_file = str(tmp_path / "questions.json")

        with patch("main.generate_deep_dive_questions") as mock_gen, \
             patch("main.run_url_retrieval") as mock_url, \
             patch("main.run_datasource_capture") as mock_ds:

            mock_gen.return_value = questions_file
            with open(questions_file, "w") as f:
                json.dump([{"category": "Test", "questions": ["Q?"]}], f)
            mock_ds.return_value = []

            from main import run_deep_dive
            run_deep_dive(
                datasources_dir=str(tmp_path / "datasources"),
                urls_deep_dir=str(urls_deep),
                datasources_deep_dir=str(datasources_deep),
            )

        # Old files should be gone (dirs were cleared)
        # Dirs get recreated by ensure_dir inside the function
        assert not (urls_deep / "old_file.json").exists()
        assert not (datasources_deep / "old_file.md").exists()

    def test_returns_none_on_file_read_error(self, tmp_path):
        """Returns None when questions file can't be read."""
        with patch("main.generate_deep_dive_questions") as mock_gen, \
             patch("main.run_url_retrieval") as mock_url:

            mock_gen.return_value = str(tmp_path / "nonexistent.json")

            from main import run_deep_dive
            result = run_deep_dive(
                datasources_dir=str(tmp_path / "datasources"),
                urls_deep_dir=str(tmp_path / "urls_deep"),
                datasources_deep_dir=str(tmp_path / "datasources_deep"),
            )

        assert result is None
        mock_url.assert_not_called()


class TestRunConversationConversion:
    def test_calls_convert_module(self):
        """Delegates to convert_to_conversations module."""
        with patch("main.convert_to_conversations") as mock_convert:
            mock_convert.return_value = "/fake/path/conversation_dataset.json"

            from main import run_conversation_conversion
            result = run_conversation_conversion(
                qna_dataset_file="qna_dataset.json",
                output_file="conversation_dataset.json",
            )

        mock_convert.assert_called_once_with(
            qna_dataset_file="qna_dataset.json",
            output_file="conversation_dataset.json",
        )
        assert result == "/fake/path/conversation_dataset.json"
