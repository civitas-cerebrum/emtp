import json
import pytest
from unittest.mock import patch, MagicMock

from dataset.enrichment.conversation_conversion import convert_to_conversations, main
from util.llm_providers.base import LLMError


class TestConvertToConversations:
    def test_basic_conversion(self):
        qna_pairs = [
            {"q": "What is QA?", "a": "QA is quality assurance.", "category": "Basics"},
            {"q": "Why QA?", "a": "QA ensures quality.", "category": "Basics"},
        ]
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            "conversations": [
                {"role": "user", "content": "Can you explain QA?"},
                {"role": "assistant", "content": "QA stands for quality assurance..."},
                {"role": "user", "content": "Why is it important?"},
                {"role": "assistant", "content": "It ensures product quality..."},
            ]
        }

        result = convert_to_conversations(
            client=mock_client, qna_pairs=qna_pairs,
            prompt="Convert to conversation", model_name="gemma3:4b",
        )

        assert len(result) == 1
        assert "messages" in result[0]
        assert len(result[0]["messages"]) == 4

    def test_groups_by_category(self):
        qna_pairs = [
            {"q": "Q1?", "a": "A1", "category": "Alpha"},
            {"q": "Q2?", "a": "A2", "category": "Beta"},
        ]
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            "conversations": [{"role": "user", "content": "Q"}, {"role": "assistant", "content": "A"}]
        }

        result = convert_to_conversations(
            client=mock_client, qna_pairs=qna_pairs,
            prompt="Convert", model_name="gemma3:4b",
        )

        assert len(result) == 2
        assert mock_client.generate.call_count == 2

    def test_batch_splitting(self):
        qna_pairs = [{"q": f"Q{i}?", "a": f"A{i}", "category": "Big"} for i in range(12)]
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            "conversations": [{"role": "user", "content": "Q"}, {"role": "assistant", "content": "A"}]
        }

        result = convert_to_conversations(
            client=mock_client, qna_pairs=qna_pairs,
            prompt="Convert", model_name="gemma3:4b", batch_size=5,
        )

        assert mock_client.generate.call_count == 3
        assert len(result) == 3

    def test_filters_system_role(self):
        qna_pairs = [{"q": "Q?", "a": "A", "category": "Test"}]
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            "conversations": [
                {"role": "system", "content": "You are an expert"},
                {"role": "user", "content": "Q?"},
                {"role": "assistant", "content": "A"},
            ]
        }

        result = convert_to_conversations(
            client=mock_client, qna_pairs=qna_pairs,
            prompt="Convert", model_name="gemma3:4b",
        )

        roles = [m["role"] for m in result[0]["messages"]]
        assert "system" not in roles

    def test_handles_empty_conversation_response(self):
        qna_pairs = [{"q": "Q?", "a": "A", "category": "Test"}]
        mock_client = MagicMock()
        mock_client.generate.return_value = {"conversations": []}

        result = convert_to_conversations(
            client=mock_client, qna_pairs=qna_pairs,
            prompt="Convert", model_name="gemma3:4b",
        )

        assert result == []

    def test_handles_llm_error(self):
        qna_pairs = [
            {"q": "Q1?", "a": "A1", "category": "Alpha"},
            {"q": "Q2?", "a": "A2", "category": "Beta"},
        ]
        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            LLMError("fail"),
            {"conversations": [{"role": "user", "content": "Q"}, {"role": "assistant", "content": "A"}]},
        ]

        result = convert_to_conversations(
            client=mock_client, qna_pairs=qna_pairs,
            prompt="Convert", model_name="gemma3:4b",
        )

        assert len(result) == 1

    def test_default_category_when_missing(self):
        qna_pairs = [{"q": "Q?", "a": "A"}]
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            "conversations": [{"role": "user", "content": "Q"}, {"role": "assistant", "content": "A"}]
        }

        result = convert_to_conversations(
            client=mock_client, qna_pairs=qna_pairs,
            prompt="Convert", model_name="gemma3:4b",
        )

        assert len(result) == 1


class TestMain:
    def test_saves_conversations_to_file(self, tmp_path):
        qna_data = [{"q": "Q?", "a": "A", "category": "Test"}]
        qna_file = tmp_path / "qna_dataset.json"
        qna_file.write_text(json.dumps(qna_data))

        mock_client = MagicMock()
        mock_client.generate.return_value = {
            "conversations": [{"role": "user", "content": "Q?"}, {"role": "assistant", "content": "A"}]
        }

        with patch("dataset.enrichment.conversation_conversion.create_llm_client") as mock_factory, \
             patch("dataset.enrichment.conversation_conversion.get_emtp_directory") as mock_dir:
            mock_factory.return_value = mock_client
            mock_dir.return_value = str(tmp_path)

            result_path = main(
                qna_dataset_file="qna_dataset.json",
                output_file="conversation_dataset.json",
            )

        assert result_path.endswith("conversation_dataset.json")
        with open(result_path) as f:
            data = json.load(f)
        assert len(data) == 1
