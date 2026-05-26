"""Output log for tracing entity-to-article provenance."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _default_log_path() -> Path:
    return Path.home() / "linglong" / "state" / "output_log.jsonl"


class OutputLog:
    """Append-only audit log tracing which entities went into which articles."""

    def __init__(self, log_path: Path | None = None):
        self.log_path = log_path or _default_log_path()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        article_id: str,
        article_title: str,
        entity_ids: list[str],
        publisher: str = "",
        status: str = "published",
    ) -> None:
        """Append a record to the output log."""
        record = {
            "article_id": article_id,
            "article_title": article_title,
            "entity_ids": entity_ids,
            "publisher": publisher,
            "published_at": datetime.now(UTC).isoformat(),
            "status": status,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info(
            "OutputLog: article=%s entities=%d publisher=%s",
            article_id,
            len(entity_ids),
            publisher,
        )

    def query_by_entity(self, entity_id: str) -> list[dict]:
        """Find all articles that consumed a given entity."""
        results = []
        if not self.log_path.exists():
            return results
        with open(self.log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entity_id in record.get("entity_ids", []):
                    results.append(record)
        return results

    def query_by_article(self, article_id: str) -> dict | None:
        """Find the record for a given article (latest match)."""
        if not self.log_path.exists():
            return None
        result = None
        with open(self.log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("article_id") == article_id:
                    result = record
        return result
