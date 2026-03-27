import pytest
from unittest.mock import MagicMock, patch


def _make_search_engine():
    """Import search_engine with all module-level utilities patched."""
    with patch("util.utilities.get_config", return_value=MagicMock()), \
         patch("util.utilities.get_logger", return_value=MagicMock()), \
         patch("util.utilities.is_verbose", return_value=True):
        import importlib
        import dataset.acquisition.retrieve_url.search_engine as se
        importlib.reload(se)
        return se


# Import once for the whole module; reload handles the patched side-effects
import sys
# Ensure a clean slate when this test module is collected
with patch("util.utilities.get_config", return_value=MagicMock()), \
     patch("util.utilities.get_logger", return_value=MagicMock()), \
     patch("util.utilities.is_verbose", return_value=True):
    import dataset.acquisition.retrieve_url.search_engine as _se


def _make_ddgs_mock(results):
    """Returns (ddgs_class_mock, ddgs_instance_mock)."""
    ddgs_instance = MagicMock()
    ddgs_instance.text.return_value = results
    ddgs_instance.__enter__ = MagicMock(return_value=ddgs_instance)
    ddgs_instance.__exit__ = MagicMock(return_value=False)
    ddgs_class = MagicMock(return_value=ddgs_instance)
    return ddgs_class, ddgs_instance


class TestSearchQuestion:

    def test_string_question_searches_ddg(self):
        fake_results = [{"href": "https://example.com/1"}, {"href": "https://example.com/2"}]
        ddgs_class, ddgs_instance = _make_ddgs_mock(fake_results)

        with patch("dataset.acquisition.retrieve_url.search_engine.DDGS", ddgs_class), \
             patch("dataset.acquisition.retrieve_url.search_engine.is_verbose", return_value=True):
            result = _se.search_question("Science", "What is gravity?")

        ddgs_instance.text.assert_called_once_with("What is gravity?", max_results=10)
        assert result["category"] == "Science"
        assert result["question"] == "What is gravity?"
        assert result["urls"] == ["https://example.com/1", "https://example.com/2"]

    def test_string_question_with_global_dorks(self):
        fake_results = [{"href": "https://example.com/a"}]
        ddgs_class, ddgs_instance = _make_ddgs_mock(fake_results)

        with patch("dataset.acquisition.retrieve_url.search_engine.DDGS", ddgs_class), \
             patch("dataset.acquisition.retrieve_url.search_engine.is_verbose", return_value=True):
            result = _se.search_question("Science", "What is gravity?", dorks="site:edu")

        ddgs_instance.text.assert_called_once_with("What is gravity? site:edu", max_results=10)
        assert result["dorks"] == "site:edu"

    def test_dict_question_extracts_question_key(self):
        fake_results = [{"href": "https://example.com/x"}]
        ddgs_class, ddgs_instance = _make_ddgs_mock(fake_results)

        with patch("dataset.acquisition.retrieve_url.search_engine.DDGS", ddgs_class), \
             patch("dataset.acquisition.retrieve_url.search_engine.is_verbose", return_value=True):
            result = _se.search_question(
                "Tech", {"question": "How does DNS work?", "dorks": None, "urls": None}
            )

        ddgs_instance.text.assert_called_once_with("How does DNS work?", max_results=10)
        assert result["question"] == "How does DNS work?"

    def test_dict_question_uses_per_question_dorks_over_global(self):
        fake_results = [{"href": "https://example.com/q"}]
        ddgs_class, ddgs_instance = _make_ddgs_mock(fake_results)

        with patch("dataset.acquisition.retrieve_url.search_engine.DDGS", ddgs_class), \
             patch("dataset.acquisition.retrieve_url.search_engine.is_verbose", return_value=True):
            result = _se.search_question(
                "Tech",
                {"question": "How does DNS work?", "dorks": "site:wikipedia.org", "urls": None},
                dorks="site:edu",
            )

        # Per-question dorks should override global dorks
        ddgs_instance.text.assert_called_once_with(
            "How does DNS work? site:wikipedia.org", max_results=10
        )
        assert result["dorks"] == "site:wikipedia.org"

    def test_dict_question_with_global_dorks_fallback(self):
        """When dict has no per-question dorks, global dorks are used."""
        fake_results = []
        ddgs_class, ddgs_instance = _make_ddgs_mock(fake_results)

        with patch("dataset.acquisition.retrieve_url.search_engine.DDGS", ddgs_class), \
             patch("dataset.acquisition.retrieve_url.search_engine.is_verbose", return_value=True):
            _se.search_question(
                "Tech",
                {"question": "What is TCP?", "dorks": None, "urls": None},
                dorks="site:edu",
            )

        ddgs_instance.text.assert_called_once_with("What is TCP? site:edu", max_results=10)

    def test_dict_question_with_provided_urls_skips_search(self):
        ddgs_class = MagicMock()

        with patch("dataset.acquisition.retrieve_url.search_engine.DDGS", ddgs_class), \
             patch("dataset.acquisition.retrieve_url.search_engine.is_verbose", return_value=True):
            result = _se.search_question(
                "History",
                {
                    "question": "Ancient Rome",
                    "dorks": None,
                    "urls": ["https://history.com/rome", "https://britannica.com/rome"],
                },
            )

        # DDGS should never be instantiated
        ddgs_class.assert_not_called()
        assert result["urls"] == ["https://history.com/rome", "https://britannica.com/rome"]
        assert result["category"] == "History"
        assert result["question"] == "Ancient Rome"

    def test_results_without_href_are_excluded(self):
        fake_results = [
            {"href": "https://good.com"},
            {"title": "no href here"},
            {"href": "https://also-good.com"},
        ]
        ddgs_class, ddgs_instance = _make_ddgs_mock(fake_results)

        with patch("dataset.acquisition.retrieve_url.search_engine.DDGS", ddgs_class), \
             patch("dataset.acquisition.retrieve_url.search_engine.is_verbose", return_value=True):
            result = _se.search_question("Test", "some question")

        assert result["urls"] == ["https://good.com", "https://also-good.com"]

    def test_custom_search_result_count(self):
        ddgs_class, ddgs_instance = _make_ddgs_mock([])

        with patch("dataset.acquisition.retrieve_url.search_engine.DDGS", ddgs_class), \
             patch("dataset.acquisition.retrieve_url.search_engine.is_verbose", return_value=True):
            _se.search_question("Test", "query", search_result_count=5)

        ddgs_instance.text.assert_called_once_with("query", max_results=5)

    def test_ddgs_exception_returns_empty_urls_with_error_key(self):
        ddgs_instance = MagicMock()
        ddgs_instance.text.side_effect = Exception("Network error")
        ddgs_instance.__enter__ = MagicMock(return_value=ddgs_instance)
        ddgs_instance.__exit__ = MagicMock(return_value=False)
        ddgs_class = MagicMock(return_value=ddgs_instance)

        with patch("dataset.acquisition.retrieve_url.search_engine.DDGS", ddgs_class), \
             patch("dataset.acquisition.retrieve_url.search_engine.is_verbose", return_value=True):
            result = _se.search_question("Science", "What is light?")

        assert result["urls"] == []
        assert "error" in result
        assert "Network error" in result["error"]

    def test_invalid_question_type_raises_value_error(self):
        with pytest.raises(ValueError):
            _se.search_question("Test", 12345)

    def test_return_structure_contains_required_keys(self):
        fake_results = [{"href": "https://example.com"}]
        ddgs_class, ddgs_instance = _make_ddgs_mock(fake_results)

        with patch("dataset.acquisition.retrieve_url.search_engine.DDGS", ddgs_class), \
             patch("dataset.acquisition.retrieve_url.search_engine.is_verbose", return_value=True):
            result = _se.search_question("Cat", "question text")

        assert "category" in result
        assert "question" in result
        assert "dorks" in result
        assert "urls" in result
