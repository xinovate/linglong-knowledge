"""Tests for EmbeddingGenerator."""

from unittest.mock import MagicMock, patch

import pytest

from linglong.core.config import LinglongConfig, set_config
from linglong.knowledge.embeddings import EmbeddingGenerator


@pytest.fixture(autouse=True)
def _set_config(tmp_path):
    """Set test config with embedding settings."""
    config = LinglongConfig(
        knowledge=LinglongConfig().knowledge.model_copy(
            update={
                "wiki_path": tmp_path / "wiki",
                "db_path": tmp_path / "knowledge.db",
                "vector_dimensions": 768,
                "embedding_url": "http://test.embeddings",
                "embedding_model": "test-model",
            }
        ),
    )
    set_config(config)


def test_generate_embedding_success():
    """Mock HTTP success and verify returned vector."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "data": [{"embedding": [0.1] * 768}],
    }

    with patch("linglong.knowledge.embeddings.requests.post", return_value=mock_resp):
        gen = EmbeddingGenerator()
        result = gen.generate("hello world")

    assert result is not None
    assert len(result) == 768
    assert result[0] == 0.1


def test_generate_embedding_failure():
    """Mock HTTP failure returns None."""
    from requests import HTTPError

    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = HTTPError("500 error")

    with patch("linglong.knowledge.embeddings.requests.post", return_value=mock_resp):
        gen = EmbeddingGenerator()
        result = gen.generate("hello world")

    assert result is None


def test_generate_embedding_timeout():
    """Mock timeout returns None."""
    from requests import Timeout

    with patch(
        "linglong.knowledge.embeddings.requests.post",
        side_effect=Timeout("connection timed out"),
    ):
        gen = EmbeddingGenerator()
        result = gen.generate("hello world")

    assert result is None


def test_generate_empty_text():
    """Empty or whitespace-only text returns None."""
    gen = EmbeddingGenerator()
    assert gen.generate("") is None
    assert gen.generate("   ") is None


def test_dimension_mismatch_warning(caplog):
    """Log warning when response dimension doesn't match config."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "data": [{"embedding": [0.1] * 512}],
    }

    with patch("linglong.knowledge.embeddings.requests.post", return_value=mock_resp):
        gen = EmbeddingGenerator()
        result = gen.generate("test")

    assert result is not None
    assert len(result) == 512
    assert "dimension mismatch" in caplog.text


def test_generate_id():
    """generate_id returns unique hex strings."""
    gen = EmbeddingGenerator()
    id1 = gen.generate_id()
    id2 = gen.generate_id()
    assert id1 != id2
    assert len(id1) == 32  # uuid4 hex
