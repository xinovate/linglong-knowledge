"""Embedding generation for vector search.

Supports remote embedding services (OpenAI-compatible API)
and graceful fallback when the service is unavailable.

Long texts are truncated to fit the model's context window,
keeping the title and leading content which carry the most
semantic signal.
"""

import logging
import uuid
from typing import Any

import requests

from linglong.core.config import get_config

logger = logging.getLogger(__name__)

# nomic-embed-text-v1.5: 8192 tokens, ~4 chars/token → ~32000 chars
_MAX_TEXT_LENGTH = 30000
_TIMEOUT = 600


class EmbeddingGenerator:
    """Generate text embeddings via a remote embedding service."""

    def __init__(self) -> None:
        self.config = get_config().knowledge

    def generate(self, text: str) -> list[float] | None:
        """Generate embedding for text, truncating if over context limit.

        Returns ``None`` if the service is unreachable or returns an error.
        """
        if not text or not text.strip():
            return None

        if len(text) > _MAX_TEXT_LENGTH:
            logger.info(
                "Truncating text from %d to %d chars for embedding",
                len(text), _MAX_TEXT_LENGTH,
            )
            text = text[:_MAX_TEXT_LENGTH]

        url = f"{self.config.embedding_url.rstrip('/')}/embeddings"
        payload: dict[str, Any] = {
            "model": self.config.embedding_model,
            "input": [text],
        }
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.config.embedding_api_key:
            headers["Authorization"] = f"Bearer {self.config.embedding_api_key}"

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            embedding = data["data"][0]["embedding"]
            if len(embedding) != self.config.vector_dimensions:
                logger.warning(
                    "Embedding dimension mismatch: expected %d, got %d",
                    self.config.vector_dimensions,
                    len(embedding),
                )
            return embedding
        except requests.Timeout:
            logger.error(
                "Embedding timeout after %ds (text len=%d, url=%s)",
                _TIMEOUT, len(text), url,
            )
        except requests.RequestException as exc:
            logger.error("Embedding request error (text len=%d): %s", len(text), exc)
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Embedding response format error: %s", exc)

        return None

    def generate_id(self) -> str:
        """Generate a unique embedding identifier."""
        return uuid.uuid4().hex
