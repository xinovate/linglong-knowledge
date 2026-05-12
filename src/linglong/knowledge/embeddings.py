"""Embedding generation for vector search.

Supports remote embedding services (OpenAI-compatible API)
and graceful fallback when the service is unavailable.
"""

import logging
import uuid
from typing import Any

import requests

from linglong.core.config import get_config

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate text embeddings via a remote embedding service."""

    def __init__(self) -> None:
        self.config = get_config().knowledge

    def generate(self, text: str) -> list[float] | None:
        """Generate embedding for a single text.

        Returns ``None`` if the service is unreachable or returns an error.
        """
        if not text or not text.strip():
            return None

        url = self.config.embedding_url.rstrip("/") + "/embeddings"
        payload: dict[str, Any] = {
            "model": self.config.embedding_model,
            "input": [text],
        }
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.config.embedding_api_key:
            headers["Authorization"] = f"Bearer {self.config.embedding_api_key}"

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=5)
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
            logger.warning("Embedding service timeout: %s", url)
        except requests.RequestException as exc:
            logger.warning("Embedding service error: %s", exc)
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("Unexpected embedding response format: %s", exc)

        return None

    def generate_id(self) -> str:
        """Generate a unique embedding identifier."""
        return uuid.uuid4().hex
