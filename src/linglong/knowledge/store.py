"""Knowledge storage layer - File + SQLite + Vector."""

import json
import logging

try:
    import sqlean.dbapi2 as sqlite3
except ImportError:
    import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import sqlite_vec

from linglong.core.config import get_config
from linglong.core.models import Entity, EntityStatus
from linglong.knowledge.embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class KnowledgeStore:
    """Unified storage: Filesystem + SQLite + Vector index."""

    def __init__(self):
        self.config = get_config().knowledge
        self.wiki_path = self.config.wiki_path
        self.db_path = self.config.db_path
        self._vector_available = False
        self._embedding_generator = EmbeddingGenerator()
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            # Entities table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    summary TEXT,
                    created_by TEXT NOT NULL,
                    confirmed_by TEXT,
                    confirmed_at TIMESTAMP,
                    confidence REAL DEFAULT 0.5,
                    status TEXT DEFAULT 'raw',
                    sources TEXT,  -- JSON
                    relations TEXT,  -- JSON
                    versions TEXT,  -- JSON
                    current_version INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    embedding_id TEXT,
                    metadata TEXT  -- JSON
                )
            """)

            # Vector virtual table (sqlite-vec)
            if self.config.vector_enabled:
                try:
                    if hasattr(conn, "enable_load_extension"):
                        conn.enable_load_extension(True)
                    sqlite_vec.load(conn)
                    conn.execute(f"""
                        CREATE VIRTUAL TABLE IF NOT EXISTS entity_embeddings USING vec0(
                            embedding_id TEXT PRIMARY KEY,
                            embedding FLOAT[{self.config.vector_dimensions}] distance_metric=cosine
                        )
                    """)
                    self._vector_available = True
                except Exception:
                    # sqlite-vec extension not available; disable vector features
                    self._vector_available = False

            conn.commit()

    def _write_embedding(
        self, conn: sqlite3.Connection, embedding_id: str, embedding: list[float]
    ) -> None:
        """Write embedding vector into the sqlite-vec virtual table."""
        if hasattr(conn, "enable_load_extension"):
            conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.execute(
            "INSERT OR REPLACE INTO entity_embeddings (embedding_id, embedding) VALUES (?, ?)",
            (embedding_id, json.dumps(embedding)),
        )

    def _delete_embedding(self, conn: sqlite3.Connection, embedding_id: str | None) -> None:
        """Remove embedding vector from the sqlite-vec virtual table."""
        if embedding_id:
            if hasattr(conn, "enable_load_extension"):
                conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.execute(
                "DELETE FROM entity_embeddings WHERE embedding_id = ?",
                (embedding_id,),
            )

    def _generate_and_store_embedding(self, entity: Entity) -> None:
        """Generate embedding for entity and store it if vector search is available."""
        if not self._vector_available or not self.config.generate_embeddings:
            return

        embedding = self._embedding_generator.generate(entity.content)
        if embedding is not None:
            entity.embedding_id = self._embedding_generator.generate_id()
            with sqlite3.connect(self.db_path) as conn:
                self._write_embedding(conn, entity.embedding_id, embedding)
                conn.commit()

    def create(self, entity: Entity) -> Entity:
        """Create a new entity."""
        entity.id = entity.id or str(uuid.uuid4())
        entity.created_at = entity.created_at or datetime.utcnow()
        entity.updated_at = entity.updated_at or entity.created_at

        # Save to filesystem
        self._save_to_filesystem(entity)

        # Save to SQLite
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO entities
                (id, content, summary, created_by, confirmed_by, confirmed_at,
                 confidence, status, sources, relations, versions, current_version,
                 created_at, updated_at, embedding_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entity.id,
                    entity.content,
                    entity.summary,
                    entity.created_by,
                    entity.confirmed_by,
                    entity.confirmed_at.isoformat() if entity.confirmed_at else None,
                    float(entity.confidence),
                    entity.status.value,
                    json.dumps([s.model_dump() for s in entity.sources]),
                    json.dumps([r.model_dump() for r in entity.relations]),
                    json.dumps([v.model_dump() for v in entity.versions]),
                    entity.current_version,
                    entity.created_at.isoformat(),
                    entity.updated_at.isoformat(),
                    entity.embedding_id,
                    json.dumps(entity.metadata),
                ),
            )
            conn.commit()

        # Generate embedding after entity is persisted
        self._generate_and_store_embedding(entity)

        # Update embedding_id if embedding was generated
        if entity.embedding_id:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE entities SET embedding_id = ? WHERE id = ?",
                    (entity.embedding_id, entity.id),
                )
                conn.commit()

        return entity

    def get(self, entity_id: str) -> Entity | None:
        """Get entity by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()

            if row is None:
                return None

            return self._row_to_entity(row)

    def search(
        self,
        query: str | None = None,
        status: EntityStatus | None = None,
        created_by: str | None = None,
        limit: int = 50,
    ) -> list[Entity]:
        """Search entities with filters."""
        conditions = []
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status.value)

        if created_by:
            conditions.append("created_by = ?")
            params.append(created_by)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                SELECT * FROM entities
                WHERE {where_clause}
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()

            return [self._row_to_entity(row) for row in rows]

    def search_similar(
        self,
        query: str,
        limit: int = 10,
        status: EntityStatus | None = None,
    ) -> list[Entity]:
        """Search entities by vector similarity to the query text.

        Falls back to filter-only search if vector search is unavailable.
        """
        if not self._vector_available:
            logger.warning("Vector search unavailable; falling back to filter search")
            return self.search(query=query, status=status, limit=limit)

        query_embedding = self._embedding_generator.generate(query)
        if query_embedding is None:
            logger.warning("Failed to generate query embedding; falling back to filter search")
            return self.search(query=query, status=status, limit=limit)

        with sqlite3.connect(self.db_path) as conn:
            if hasattr(conn, "enable_load_extension"):
                conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.row_factory = sqlite3.Row

            # Build base query with optional status filter
            conditions = []
            params: list = [json.dumps(query_embedding), limit]

            if status:
                conditions.append("e.status = ?")
                params.insert(1, status.value)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            rows = conn.execute(
                f"""
                SELECT e.*, vec_distance_cosine(emb.embedding, ?) AS distance
                FROM entity_embeddings AS emb
                JOIN entities AS e ON e.embedding_id = emb.embedding_id
                WHERE {where_clause}
                ORDER BY distance
                LIMIT ?
                """,
                params,
            ).fetchall()

            return [self._row_to_entity(row) for row in rows]

    def update(self, entity: Entity) -> Entity:
        """Update an existing entity."""
        entity.updated_at = datetime.utcnow()

        # Update filesystem
        self._save_to_filesystem(entity)

        # Update SQLite
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE entities SET
                    content = ?,
                    summary = ?,
                    confirmed_by = ?,
                    confirmed_at = ?,
                    confidence = ?,
                    status = ?,
                    sources = ?,
                    relations = ?,
                    versions = ?,
                    current_version = ?,
                    updated_at = ?,
                    embedding_id = ?,
                    metadata = ?
                WHERE id = ?
                """,
                (
                    entity.content,
                    entity.summary,
                    entity.confirmed_by,
                    entity.confirmed_at.isoformat() if entity.confirmed_at else None,
                    float(entity.confidence),
                    entity.status.value,
                    json.dumps([s.model_dump() for s in entity.sources]),
                    json.dumps([r.model_dump() for r in entity.relations]),
                    json.dumps([v.model_dump() for v in entity.versions]),
                    entity.current_version,
                    entity.updated_at.isoformat(),
                    entity.embedding_id,
                    json.dumps(entity.metadata),
                    entity.id,
                ),
            )
            conn.commit()

        # Regenerate embedding if content changed and vector search is available
        if self._vector_available and self.config.generate_embeddings:
            old_entity = self.get(entity.id)
            if old_entity is None or old_entity.content != entity.content:
                if entity.embedding_id:
                    with sqlite3.connect(self.db_path) as conn:
                        self._delete_embedding(conn, entity.embedding_id)
                        conn.commit()
                self._generate_and_store_embedding(entity)
                # Re-update embedding_id in entities table
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "UPDATE entities SET embedding_id = ? WHERE id = ?",
                        (entity.embedding_id, entity.id),
                    )
                    conn.commit()

        return entity

    def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        # Get embedding_id before deleting
        embedding_id = None
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT embedding_id FROM entities WHERE id = ?", (entity_id,)
            ).fetchone()
            if row:
                embedding_id = row[0]

        # Delete from filesystem
        entity_path = self._get_entity_path(entity_id)
        if entity_path.exists():
            entity_path.unlink()

        # Delete from SQLite
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
            conn.commit()
            deleted = cursor.rowcount > 0

        # Delete embedding if vector search is available
        if deleted and embedding_id and self._vector_available:
            with sqlite3.connect(self.db_path) as conn:
                self._delete_embedding(conn, embedding_id)
                conn.commit()

        return deleted

    def _save_to_filesystem(self, entity: Entity) -> None:
        """Save entity as Markdown file."""
        entity_path = self._get_entity_path(entity.id)
        entity_path.parent.mkdir(parents=True, exist_ok=True)

        # Build frontmatter
        frontmatter = {
            "id": entity.id,
            "created_by": entity.created_by,
            "confirmed_by": entity.confirmed_by,
            "confidence": float(entity.confidence),
            "status": entity.status.value,
            "created_at": entity.created_at.isoformat(),
            "updated_at": entity.updated_at.isoformat(),
        }

        # Write markdown with YAML frontmatter
        content = f"""---
{json.dumps(frontmatter, indent=2, ensure_ascii=False)}
---

{entity.content}
"""
        entity_path.write_text(content, encoding="utf-8")

    def _get_entity_path(self, entity_id: str) -> Path:
        """Get filesystem path for an entity."""
        # Use first 2 chars as subdirectory for distribution
        return self.wiki_path / entity_id[:2] / f"{entity_id}.md"

    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
        """Convert database row to Entity."""
        return Entity(
            id=row["id"],
            content=row["content"],
            summary=row["summary"],
            created_by=row["created_by"],
            confirmed_by=row["confirmed_by"],
            confirmed_at=(
                datetime.fromisoformat(row["confirmed_at"]) if row["confirmed_at"] else None
            ),
            confidence=row["confidence"],
            status=EntityStatus(row["status"]),
            sources=json.loads(row["sources"]) if row["sources"] else [],
            relations=json.loads(row["relations"]) if row["relations"] else [],
            versions=json.loads(row["versions"]) if row["versions"] else [],
            current_version=row["current_version"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            embedding_id=row["embedding_id"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )
