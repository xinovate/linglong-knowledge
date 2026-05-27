"""Knowledge storage layer - File + SQLite + Vector."""

import hashlib
import json
import logging

try:
    import sqlean.dbapi2 as sqlite3
except ImportError:
    import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

import sqlite_vec

from linglong.core.config import get_config
from linglong.core.models import Entity, EntityFacet, EntityStatus, Relation
from linglong.knowledge.embeddings import EmbeddingGenerator
from linglong.knowledge.lock import KnowledgeLock

logger = logging.getLogger(__name__)


class ConcurrentModificationError(Exception):
    """Raised when an entity was modified by another process after being read."""
    pass


def _fts_escape(term: str) -> str:
    """Escape a term for FTS5 quoted matching."""
    return term.replace('"', '""')


class KnowledgeStore:
    """Unified storage: Filesystem + SQLite + Vector index."""

    def __init__(self):
        self.config = get_config().knowledge
        self.wiki_path = self.config.wiki_path
        self.db_path = self.config.db_path
        self._vector_available = False
        self._embedding_generator = EmbeddingGenerator()
        self._init_database()

        lock_path = self.config.db_path.parent / ".knowledge.lock"
        self._lock = KnowledgeLock(lock_path, timeout=self.config.lock_timeout)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"PRAGMA journal_mode={self.config.db_mode}")
            conn.execute("PRAGMA busy_timeout=5000")

    def _log_operation(self, action: str, entity_id: str, details: str = "", entity: Entity | None = None) -> None:
        """Append operation to log file with agent and title info."""
        log_path = self.wiki_path / "log.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

        parts = [f"- **{timestamp}** `[{action}]`"]
        if entity:
            if entity.created_by:
                parts.append(f"**{entity.created_by}**")
            parts.append(entity_id)
            parts.append(f"facet={entity.facet.value}")
            # Extract title from first heading
            title = self._extract_title(entity.content)
            if title:
                parts.append(f"「{title[:50]}」")
        else:
            parts.append(entity_id)

        if details:
            parts.append(details)

        entry = " ".join(parts) + "\n"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)

    @staticmethod
    def _extract_title(content: str) -> str | None:
        """Extract title from first markdown heading."""
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return None

    def rebuild_embeddings(self) -> dict[str, int]:
        """Re-generate embeddings for entities whose content has changed.

        Scans all non-archived entities, compares content_hash, and
        regenerates embeddings for those that changed. Returns stats.
        """
        stats = {"total": 0, "regenerated": 0, "unchanged": 0, "failed": 0}

        if not self._vector_available or not self.config.generate_embeddings:
            logger.warning("Vector search disabled; skipping embedding rebuild")
            return stats

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, content, content_hash, embedding_id FROM entities WHERE archived_at IS NULL"
            ).fetchall()

        stats["total"] = len(rows)
        for row in rows:
            entity_id = row["id"]
            content = row["content"]
            old_hash = row["content_hash"]
            old_embedding_id = row["embedding_id"]

            current_hash = self._content_hash(content)
            if current_hash == old_hash and old_embedding_id:
                stats["unchanged"] += 1
                continue

            try:
                # Delete old embedding
                if old_embedding_id:
                    with sqlite3.connect(self.db_path) as conn:
                        self._delete_embedding(conn, old_embedding_id)
                        conn.commit()

                # Generate new embedding
                embedding = self._embedding_generator.generate(content)
                if embedding is not None:
                    new_embedding_id = self._embedding_generator.generate_id()
                    with sqlite3.connect(self.db_path) as conn:
                        self._write_embedding(conn, new_embedding_id, embedding)
                        conn.execute(
                            "UPDATE entities SET embedding_id = ? WHERE id = ?",
                            (new_embedding_id, entity_id),
                        )
                        conn.commit()
                    stats["regenerated"] += 1
                else:
                    stats["failed"] += 1
            except Exception as exc:
                logger.warning("Failed to rebuild embedding for %s: %s", entity_id, exc)
                stats["failed"] += 1

        return stats

    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    content_hash TEXT,  -- SHA256 of content for deduplication
                    summary TEXT,
                    facet TEXT NOT NULL DEFAULT 'concept',
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
                    archived_at TIMESTAMP,
                    embedding_id TEXT,
                    metadata TEXT  -- JSON
                )
            """)

            # Migration: older DBs may lack this column
            try:
                conn.execute("ALTER TABLE entities ADD COLUMN content_hash TEXT")
            except sqlite3.OperationalError:
                pass

            # Migration: older DBs may lack this column
            try:
                conn.execute("ALTER TABLE entities ADD COLUMN `group` TEXT")
            except sqlite3.OperationalError:
                pass

            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS entity_fts USING fts5(
                    id,
                    content,
                    facet,
                    status,
                    content='entities',
                    content_rowid='rowid'
                )
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS entities_ai AFTER INSERT ON entities BEGIN
                    INSERT INTO entity_fts(rowid, id, content, facet, status)
                    VALUES (new.rowid, new.id, new.content, new.facet, new.status);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS entities_ad AFTER DELETE ON entities BEGIN
                    INSERT INTO entity_fts(entity_fts, rowid, id, content, facet, status)
                    VALUES ('delete', old.rowid, old.id, old.content, old.facet, old.status);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS entities_au AFTER UPDATE ON entities BEGIN
                    INSERT INTO entity_fts(entity_fts, rowid, id, content, facet, status)
                    VALUES ('delete', old.rowid, old.id, old.content, old.facet, old.status);
                    INSERT INTO entity_fts(rowid, id, content, facet, status)
                    VALUES (new.rowid, new.id, new.content, new.facet, new.status);
                END
            """)

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

            conn.execute(f"PRAGMA journal_mode={self.config.db_mode}")
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

    def _write_embedding_with_hash_guard(
        self, entity_id: str, expected_hash: str, embedding_id: str
    ) -> None:
        """Write embedding_id only if content_hash hasn't changed (lock-free guard)."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT content_hash FROM entities WHERE id = ?", (entity_id,)
            ).fetchone()
            if row and row[0] == expected_hash:
                conn.execute(
                    "UPDATE entities SET embedding_id = ? WHERE id = ?",
                    (embedding_id, entity_id),
                )
                conn.commit()
                logger.debug("Embedding written for %s", entity_id)
            else:
                logger.info(
                    "Skipping embedding for %s: content changed since generation",
                    entity_id,
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

    def _content_hash(self, content: str) -> str:
        """Compute SHA256 hash of content for deduplication."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def create(self, entity: Entity) -> Entity:
        """Create a new entity with deduplication.

        Deduplication logic:
        - Same ID (same source path) + same content → return existing (idempotent)
        - Same ID + different content → update without version bump
        - Different ID + same content → link as duplicate and return existing
        """
        with self._lock:
            entity.id = entity.id or str(uuid.uuid4())
            entity.created_at = entity.created_at or datetime.now(UTC)
            entity.updated_at = entity.updated_at or entity.created_at

            content_hash = self._content_hash(entity.content)

            # --- Layer 1: source-level dedup by ID ---
            existing = self.get(entity.id)
            if existing is not None:
                if existing.content == entity.content:
                    logger.debug("Deduplication: same ID+content, skipping %s", entity.id)
                    return existing
                # Content changed → update without version bump
                entity.metadata["update_mode"] = "append"
                entity.updated_at = existing.updated_at  # bypass optimistic lock
                return self.update(entity)

            # --- Layer 2: cross-source dedup by content hash ---
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT id FROM entities WHERE content_hash = ? AND archived_at IS NULL",
                    (content_hash,),
                ).fetchone()
                if row is not None:
                    dup_id = row[0]
                    logger.info(
                        "Deduplication: content hash matches %s, linking %s as duplicate",
                        dup_id, entity.id,
                    )
                    # Return the existing entity (do not create a new one)
                    dup_entity = self.get(dup_id)
                    if dup_entity is not None:
                        return dup_entity

            self._resolve_wikilinks(entity)

            # Persist to DB first, then filesystem
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO entities
                    (id, content, content_hash, summary, facet, `group`, created_by, confirmed_by, confirmed_at,
                     confidence, status, sources, relations, versions, current_version,
                     created_at, updated_at, archived_at, embedding_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity.id,
                        entity.content,
                        content_hash,
                        entity.summary,
                        entity.facet.value,
                        entity.group,
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
                        None,  # archived_at
                        entity.embedding_id,
                        json.dumps(entity.metadata),
                    ),
                )
                conn.commit()

            self._save_to_filesystem(entity)

            # Embedding generated outside lock; hash guard prevents stale writes
            self._generate_and_store_embedding(entity)

            if entity.embedding_id:
                self._write_embedding_with_hash_guard(entity.id, content_hash, entity.embedding_id)

            self._log_operation("create", entity.id, entity=entity)

            # Auto-lint after write
            if self.config.auto_lint:
                try:
                    from linglong.knowledge.lint import LintEngine
                    lint_engine = LintEngine(self)
                    lint_results = lint_engine.run_all()
                    if lint_results:
                        logger.info("Auto-lint found %d issues after %s", len(lint_results), entity.id)
                except Exception as e:
                    logger.warning("Auto-lint failed: %s", e)

            return entity

    def check_facet_crowding(self, facet: EntityFacet, threshold: int = 10) -> dict | None:
        """Check if a facet root has too many ungrouped entities.

        Returns a warning dict if crowded, None otherwise.
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM entities WHERE facet = ? AND (`group` IS NULL OR `group` = '')",
                (facet.value,),
            ).fetchone()
            root_count = row[0]

        if root_count >= threshold:
            # List existing groups for suggestion
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT `group`, COUNT(*) FROM entities WHERE facet = ? AND `group` IS NOT NULL AND `group` != '' GROUP BY `group` ORDER BY COUNT(*) DESC",
                    (facet.value,),
                ).fetchall()
            existing_groups = {r[0]: r[1] for r in rows}
            return {
                "facet": facet.value,
                "root_count": root_count,
                "threshold": threshold,
                "existing_groups": existing_groups,
            }
        return None

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
        facet: EntityFacet | None = None,
        status: EntityStatus | None = None,
        created_by: str | None = None,
        limit: int = 50,
        include_archived: bool = False,
        since: str | None = None,
    ) -> list[Entity]:
        """Search entities with filters. Uses FTS5 when query is provided."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if query:
                # Quote each token to prevent hyphens being parsed as FTS column filters
                tokens = query.split()
                if len(tokens) > 1:
                    escaped_query = " OR ".join(
                        f'"{_fts_escape(t)}"' for t in tokens
                    )
                else:
                    escaped_query = f'"{_fts_escape(query)}"'
                params: list = [escaped_query]
                fts_conditions = []

                if facet:
                    fts_conditions.append("entity_fts.facet = ?")
                    params.append(facet.value)
                if status:
                    fts_conditions.append("entity_fts.status = ?")
                    params.append(status.value)
                if not include_archived:
                    fts_conditions.append("e.archived_at IS NULL")
                if since:
                    fts_conditions.append("e.updated_at >= ?")
                    params.append(since)

                fts_where = " AND ".join(fts_conditions) if fts_conditions else "1=1"

                rows = conn.execute(
                    f"""
                    SELECT e.* FROM entity_fts
                    JOIN entities AS e ON e.id = entity_fts.id
                    WHERE entity_fts MATCH ? AND {fts_where}
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (*params, limit),
                ).fetchall()
                return [self._row_to_entity(row) for row in rows]

            conditions = []
            params = []

            if facet:
                conditions.append("facet = ?")
                params.append(facet.value)
            if status:
                conditions.append("status = ?")
                params.append(status.value)
            if created_by:
                conditions.append("created_by = ?")
                params.append(created_by)
            if not include_archived:
                conditions.append("archived_at IS NULL")
            if since:
                conditions.append("updated_at >= ?")
                params.append(since)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

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
        facet: EntityFacet | None = None,
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

            conditions = []
            params: list = [json.dumps(query_embedding), limit]

            if status:
                conditions.append("e.status = ?")
                params.insert(1, status.value)

            if facet:
                conditions.append("e.facet = ?")
                params.insert(-1, facet.value)

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

    def search_hybrid(
        self,
        query: str,
        facet: EntityFacet | None = None,
        limit: int = 10,
    ) -> list[Entity]:
        """Hybrid search combining FTS5 and vector results via RRF.

        Reciprocal Rank Fusion: score = sum(1 / (k + rank)) for each source.
        """
        k = 60  # RRF constant

        # Fetch from both sources (oversample for better fusion)
        fetch_limit = limit * 2
        fts_results = self.search(query=query, facet=facet, limit=fetch_limit)
        vec_results = (
            self.search_similar(query=query, facet=facet, limit=fetch_limit)
            if self._vector_available
            else []
        )

        # Build id → entity map and RRF scores
        entities: dict[str, Entity] = {}
        scores: dict[str, float] = {}

        for rank, entity in enumerate(fts_results):
            entities[entity.id] = entity
            scores[entity.id] = scores.get(entity.id, 0.0) + 1.0 / (k + rank + 1)

        for rank, entity in enumerate(vec_results):
            entities[entity.id] = entity
            scores[entity.id] = scores.get(entity.id, 0.0) + 1.0 / (k + rank + 1)

        # Sort by fused score, return top N
        ranked_ids = sorted(scores, key=lambda eid: scores[eid], reverse=True)[:limit]
        return [entities[eid] for eid in ranked_ids]

    def search_auto(
        self,
        query: str,
        facet: EntityFacet | None = None,
        limit: int = 10,
    ) -> list[Entity]:
        """Auto-select search mode based on query and service availability."""
        # Heuristic: if query looks like an ID or path, use keyword only
        import re
        if re.match(r'^[a-f0-9]{8,}$', query.strip()) or '/' in query:
            return self.search(query=query, facet=facet, limit=limit)

        # If vector search available, use hybrid for best results
        if self._vector_available:
            return self.search_hybrid(query=query, facet=facet, limit=limit)

        # Fallback to FTS5
        return self.search(query=query, facet=facet, limit=limit)

    def update(self, entity: Entity) -> Entity:
        """Update an existing entity.

        Version management:
        - Content replacement (default): creates a new version entry.
        - Append mode (metadata['update_mode'] = 'append'): no version bump.
        - Versions beyond max_versions are auto-compacted.
        """
        with self._lock:
            current = self.get(entity.id)
            if current is None:
                raise ValueError(f"Entity {entity.id} not found")

            # Optimistic lock: reject if modified since read
            if entity.updated_at and current.updated_at != entity.updated_at:
                raise ConcurrentModificationError(
                    f"Entity {entity.id} was modified at {current.updated_at}, "
                    f"but you have version from {entity.updated_at}. "
                    f"Please re-read and retry."
                )

            update_mode = entity.metadata.pop("update_mode", None)
            content_changed = current.content != entity.content

            if content_changed and update_mode != "append":
                # Versions may be dict (from json.loads) or BaseModel (Pydantic); normalize
                existing_versions = []
                for v in current.versions:
                    if isinstance(v, dict):
                        existing_versions.append(v)
                    else:
                        d = v.model_dump()
                        if isinstance(d.get("modified_at"), datetime):
                            d["modified_at"] = d["modified_at"].isoformat()
                        existing_versions.append(d)
                version_entry = {
                    "version": current.current_version,
                    "content": current.content,
                    "modified_by": current.created_by,
                    "modified_at": current.updated_at.isoformat(),
                }
                entity.versions = existing_versions + [version_entry]
                entity.current_version = current.current_version + 1

                # Compact oldest versions beyond limit
                max_versions = self.config.max_versions
                if len(entity.versions) > max_versions:
                    first = entity.versions[0]
                    recent = entity.versions[-(max_versions - 1):]
                    first_compact = {
                        "version": first["version"],
                        "content": "(compressed)",
                        "modified_by": first["modified_by"],
                        "modified_at": first["modified_at"],
                    }
                    entity.versions = [first_compact] + recent

            self._resolve_wikilinks(entity)

            entity.updated_at = datetime.now(UTC)

            self._save_to_filesystem(entity)

            content_hash = self._content_hash(entity.content)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE entities SET
                        content = ?,
                        content_hash = ?,
                        summary = ?,
                        facet = ?,
                        `group` = ?,
                        confirmed_by = ?,
                        confirmed_at = ?,
                        confidence = ?,
                        status = ?,
                        sources = ?,
                        relations = ?,
                        versions = ?,
                        current_version = ?,
                        updated_at = ?,
                        archived_at = ?,
                        embedding_id = ?,
                        metadata = ?
                    WHERE id = ?
                    """,
                    (
                        entity.content,
                        content_hash,
                        entity.summary,
                        entity.facet.value,
                        entity.group,
                        entity.confirmed_by,
                        entity.confirmed_at.isoformat() if entity.confirmed_at else None,
                        float(entity.confidence),
                        entity.status.value,
                        json.dumps([s.model_dump() for s in entity.sources]),
                        json.dumps([r.model_dump() for r in entity.relations]),
                        json.dumps([
                            v if isinstance(v, dict) else v.model_dump()
                            for v in entity.versions
                        ]),
                        entity.current_version,
                        entity.updated_at.isoformat(),
                        entity.archived_at.isoformat() if entity.archived_at else None,
                        entity.embedding_id,
                        json.dumps(entity.metadata),
                        entity.id,
                    ),
                )
                conn.commit()

            # Regenerate embedding on content change; hash guard prevents stale writes
            if self._vector_available and self.config.generate_embeddings:
                old_entity = self.get(entity.id)
                if old_entity is None or old_entity.content != entity.content:
                    new_hash = self._content_hash(entity.content)
                    if entity.embedding_id:
                        with sqlite3.connect(self.db_path) as conn:
                            self._delete_embedding(conn, entity.embedding_id)
                            conn.commit()
                    self._generate_and_store_embedding(entity)
                    if entity.embedding_id:
                        self._write_embedding_with_hash_guard(entity.id, new_hash, entity.embedding_id)

            self._log_operation("update", entity.id, details=f"v{entity.current_version}", entity=entity)

            # Auto-lint after write
            if self.config.auto_lint:
                try:
                    from linglong.knowledge.lint import LintEngine
                    lint_engine = LintEngine(self)
                    lint_results = lint_engine.run_all()
                    if lint_results:
                        logger.info("Auto-lint found %d issues after %s", len(lint_results), entity.id)
                except Exception as e:
                    logger.warning("Auto-lint failed: %s", e)

            return entity

    def sync(self, fix: bool = False) -> list[dict]:
        """Check and fix consistency between DB and filesystem.

        Returns list of issues found. If fix=True, also repairs them.
        """
        issues: list[dict] = []

        # Build maps
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM entities WHERE archived_at IS NULL").fetchall()
        db_entities = {}
        for row in rows:
            entity = self._row_to_entity(row)
            db_entities[entity.id] = entity

        # Phase 1: DB → File (ensure every entity has correct file)
        for entity in db_entities.values():
            expected = self._get_entity_path(
                entity.id, entity.facet.value,
                content=entity.content, subdir=entity.group or "",
            )
            actual = self._find_entity_file(entity.id, entity.facet.value)

            if not actual:
                issues.append({
                    "type": "missing_file", "entity_id": entity.id,
                    "facet": entity.facet.value, "group": entity.group,
                    "expected_path": str(expected.relative_to(self.wiki_path)),
                })
                if fix:
                    self._save_to_filesystem(entity)
            elif actual != expected:
                issues.append({
                    "type": "wrong_path", "entity_id": entity.id,
                    "facet": entity.facet.value, "group": entity.group,
                    "actual_path": str(actual.relative_to(self.wiki_path)),
                    "expected_path": str(expected.relative_to(self.wiki_path)),
                })
                if fix:
                    expected.parent.mkdir(parents=True, exist_ok=True)
                    actual.rename(expected)

        # Phase 2: File → DB (find orphans and duplicates)
        short_id_to_entity: dict[str, Entity] = {}
        for eid, entity in db_entities.items():
            short_id_to_entity[eid[:8]] = entity

        files_by_short_id: dict[str, list[Path]] = {}
        files_by_full_id: dict[str, list[Path]] = {}
        all_db_ids = set(db_entities.keys())

        for facet_dir in self.wiki_path.iterdir():
            if not facet_dir.is_dir() or facet_dir.name in ("archive", "_staging"):
                continue
            for md_file in facet_dir.rglob("*.md"):
                if md_file.name.startswith("index") or md_file.name == "log.md":
                    continue
                stem = md_file.stem
                parts = stem.rsplit("-", 1)
                short_id = parts[1] if len(parts) == 2 and len(parts[1]) == 8 else stem
                files_by_short_id.setdefault(short_id, []).append(md_file)
                # Also index by full stem for exact ID match
                files_by_full_id.setdefault(stem, []).append(md_file)

        for short_id, files in files_by_short_id.items():
            entity = short_id_to_entity.get(short_id)
            if not entity:
                # Check if any file matches a full DB ID (non-standard ID format)
                matched = False
                for f in files:
                    if f.stem in all_db_ids:
                        matched = True
                        break
                if matched:
                    continue
                # Truly orphan files
                for f in files:
                    issues.append({
                        "type": "orphan_file",
                        "path": str(f.relative_to(self.wiki_path)),
                    })
                    if fix:
                        staging = self.wiki_path / "_staging"
                        staging.mkdir(parents=True, exist_ok=True)
                        f.rename(staging / f.name)
            elif len(files) > 1:
                # Duplicate: keep correct path, remove others
                expected = self._get_entity_path(
                    entity.id, entity.facet.value,
                    content=entity.content, subdir=entity.group or "",
                )
                for f in files:
                    if f != expected:
                        issues.append({
                            "type": "duplicate_file", "entity_id": entity.id,
                            "path": str(f.relative_to(self.wiki_path)),
                            "keep_path": str(expected.relative_to(self.wiki_path)),
                        })
                        if fix:
                            f.unlink()

        # Phase 3: Clean empty directories
        if fix:
            for facet_dir in self.wiki_path.iterdir():
                if not facet_dir.is_dir():
                    continue
                for sub in sorted(facet_dir.rglob("*"), reverse=True):
                    if sub.is_dir() and not any(sub.iterdir()):
                        sub.rmdir()

        return issues

    def archive(self, entity_id: str) -> Entity:
        """Archive an entity: mark archived_at and move file to archive/."""
        with self._lock:
            entity = self.get(entity_id)
            if entity is None:
                raise ValueError(f"Entity {entity_id} not found")

            entity.archived_at = datetime.now(UTC)
            entity.updated_at = datetime.now(UTC)

            old_path = self._get_entity_path(
                entity.id, entity.facet.value, content=entity.content
            )
            if old_path.exists():
                old_path.unlink()

            archive_dir = self.wiki_path / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / f"{entity.id}.md"
            archive_path.write_text(
                f"---\nid: {entity.id}\ntype: {entity.facet.value}\narchived_at: {entity.archived_at.isoformat()}\n---\n\n{entity.content}",
                encoding="utf-8",
            )

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE entities SET archived_at = ?, updated_at = ? WHERE id = ?",
                    (entity.archived_at.isoformat(), entity.updated_at.isoformat(), entity.id),
                )
                conn.commit()

            self._log_operation("archive", entity.id, entity=entity)
            return entity

    def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        with self._lock:
            # Fetch embedding_id, facet, content before deletion (needed for cleanup)
            embedding_id = None
            facet = "concept"
            content = ""
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT embedding_id, facet, content FROM entities WHERE id = ?",
                    (entity_id,),
                ).fetchone()
                if row:
                    embedding_id = row[0]
                    facet = row[1] or "concept"
                    content = row[2] or ""

            entity_path = self._get_entity_path(entity_id, facet, content=content)
            if entity_path.exists():
                entity_path.unlink()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
                conn.commit()
                deleted = cursor.rowcount > 0

            if deleted and embedding_id and self._vector_available:
                with sqlite3.connect(self.db_path) as conn:
                    self._delete_embedding(conn, embedding_id)
                    conn.commit()

            return deleted

    def _resolve_wikilinks(self, entity: Entity) -> None:
        """Parse [[links]] and auto-fill entity.relations."""
        from linglong.knowledge.wikilinks import WikiLinksParser
        parser = WikiLinksParser()
        links = parser.parse(entity.content)
        if not links:
            return

        all_entities = self.search(limit=10000, include_archived=False)
        title_to_id: dict[str, str] = {}
        for e in all_entities:
            for line in e.content.split("\n"):
                if line.startswith("# "):
                    title_to_id[line[2:].strip()] = e.id
                    break
            title_to_id[e.id] = e.id

        existing_targets = {r.target_id for r in entity.relations}

        for link in links:
            target_id = title_to_id.get(link.target)
            if target_id and target_id not in existing_targets:
                entity.relations.append(Relation(
                    target_id=target_id,
                    relation_type="wikilink",
                    strength=1.0,
                ))
                existing_targets.add(target_id)

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to a filesystem-safe slug."""
        import re

        slug = text.strip().lower()
        slug = re.sub(r'[\\/:*?"<>|]', "", slug)
        slug = re.sub(r"\s+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        slug = slug.strip("-")
        return slug[:80] or "untitled"

    @staticmethod
    def _extract_title(content: str) -> str | None:
        """Extract title from first markdown heading."""
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return None

    def _get_entity_path(self, entity_id: str, facet: str = "concept",
                         content: str = "", subdir: str = "") -> Path:
        """Get filesystem path for an entity, using semantic filename when possible."""
        title = self._extract_title(content) if content else None
        base = self.wiki_path / facet / subdir if subdir else self.wiki_path / facet
        if title:
            slug = self._slugify(title)
            return base / f"{slug}-{entity_id[:8]}.md"
        return base / f"{entity_id}.md"

    def _find_entity_file(self, entity_id: str, facet: str) -> Path | None:
        """Find existing entity file in facet directory (including subdirs)."""
        facet_dir = self.wiki_path / facet
        if not facet_dir.exists():
            return None
        short_id = entity_id[:8]
        for md_file in facet_dir.rglob("*.md"):
            name = md_file.stem
            if name == entity_id or name.endswith(f"-{short_id}"):
                return md_file
        return None

    def _save_to_filesystem(self, entity: Entity) -> None:
        """Save entity as Markdown file with YAML frontmatter."""
        subdir = entity.group or ""
        # Find old file across all possible locations
        old_path = self._find_entity_file(entity.id, entity.facet.value)
        entity_path = self._get_entity_path(
            entity.id, entity.facet.value, content=entity.content, subdir=subdir
        )
        entity_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove old file if path changed (facet/group/filename shift)
        if old_path and old_path != entity_path:
            old_path.unlink()

        # OpenClaw-compatible frontmatter
        fm_lines = [
            f"id: {entity.id}",
            f"type: {entity.facet.value}",
            f"created_by: {entity.created_by}",
        ]
        if entity.confirmed_by:
            fm_lines.append(f"confirmed_by: {entity.confirmed_by}")
        fm_lines.append(f"confidence: {float(entity.confidence)}")
        fm_lines.append(f"status: {entity.status.value}")
        if entity.group:
            fm_lines.append(f"group: {entity.group}")
        fm_lines.append(f"created_at: {entity.created_at.isoformat()}")
        fm_lines.append(f"updated_at: {entity.updated_at.isoformat()}")
        if entity.summary:
            fm_lines.append(f"summary: {entity.summary}")

        file_content = f"---\n{'\n'.join(fm_lines)}\n---\n\n{entity.content}\n"
        entity_path.write_text(file_content, encoding="utf-8")

    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
        """Convert database row to Entity."""
        # Gracefully handle older schemas missing this column
        facet_str = row["facet"] if "facet" in row.keys() else None
        facet = EntityFacet(facet_str) if facet_str else EntityFacet.CONCEPT

        # Gracefully handle older schemas missing this column
        archived_at_raw = row["archived_at"] if "archived_at" in row.keys() else None

        group = row["group"] if "group" in row.keys() else None

        return Entity(
            id=row["id"],
            content=row["content"],
            facet=facet,
            group=group,
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
            archived_at=(
                datetime.fromisoformat(archived_at_raw) if archived_at_raw else None
            ),
            embedding_id=row["embedding_id"],
            distance=row["distance"] if "distance" in row.keys() else None,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )
