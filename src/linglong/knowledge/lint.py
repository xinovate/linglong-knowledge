"""Knowledge lint engine — health checks for the wiki."""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path

from linglong.core.models import EntityFacet
from linglong.knowledge.store import KnowledgeStore
from linglong.knowledge.wikilinks import WikiLinksParser

logger = logging.getLogger(__name__)


class LintSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class LintResult:
    """A single lint finding."""
    rule: str
    severity: LintSeverity
    message: str
    entity_id: str | None = None
    facet: str | None = None
    details: dict = field(default_factory=dict)
    fixed: bool = False


class LintEngine:
    """Run health checks on the knowledge base."""

    def __init__(self, store: KnowledgeStore):
        self.store = store
        self.parser = WikiLinksParser()

    def run_all(self, stale_days: int = 90) -> list[LintResult]:
        """Run all lint checks and return results."""
        results = []
        results.extend(self.check_index_consistency())
        results.extend(self.check_wikilinks())
        results.extend(self.check_content_conflicts())
        results.extend(self.check_stale_content(stale_days))
        results.extend(self.check_orphans())
        results.extend(self.check_crowded_facets())
        return results

    def fix_all(self, results: list[LintResult] | None = None, stale_days: int = 90) -> list[LintResult]:
        """Auto-fix issues where possible. Returns updated results."""
        if results is None:
            results = self.run_all(stale_days=stale_days)

        for r in results:
            if r.fixed:
                continue
            if r.rule == "index_consistency" and r.entity_id:
                orphan_path = r.details.get("path")
                if orphan_path:
                    orphan = self.store.wiki_path / orphan_path
                elif r.facet:
                    orphan = self.store.wiki_path / r.facet / f"{r.entity_id}.md"
                else:
                    orphan = None
                if orphan and orphan.exists():
                    orphan.unlink()
                    r.fixed = True
                    r.message += " (已修复：删除孤立文件)"

        wikilink_results = [r for r in results if r.rule == "wikilinks" and not r.fixed and r.entity_id]
        if wikilink_results:
            self._fix_wikilinks(wikilink_results)

        return results

    def _fix_wikilinks(self, results: list[LintResult]) -> None:
        """Batch-fix dead wikilinks by converting [[target]] to plain text."""
        import re

        entity_dead_links: dict[str, set[str]] = {}
        for r in results:
            entity_id = r.entity_id
            target = r.details.get("target", "")
            if entity_id and target:
                entity_dead_links.setdefault(entity_id, set()).add(target)

        _WIKILINK_RE = re.compile(r"\[\[(.*?)\]\]")

        for entity_id, dead_targets in entity_dead_links.items():
            entity = self.store.get(entity_id)
            if entity is None:
                continue

            original_content = entity.content

            def _replace_link(match: re.Match) -> str:
                link_text = match.group(1)
                parts = link_text.split("|", 1)
                target = parts[0].strip()
                display = parts[1].strip() if len(parts) > 1 else target
                if target in dead_targets:
                    return display
                return match.group(0)

            new_content = _WIKILINK_RE.sub(_replace_link, original_content)
            if new_content != original_content:
                entity.content = new_content
                try:
                    self.store.update(entity)
                    for r in results:
                        if r.entity_id == entity_id and r.details.get("target") in dead_targets:
                            r.fixed = True
                            r.message += " (已修复：删除死链)"
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed to fix wikilinks for %s: %s", entity_id, exc)


    def check_index_consistency(self) -> list[LintResult]:
        """Check that index files reflect actual wiki files."""
        results = []
        wiki_path = self.store.wiki_path
        if not wiki_path.exists():
            return results

        for facet in EntityFacet:
            facet_dir = wiki_path / facet.value
            if not facet_dir.exists():
                continue

            for md_file in facet_dir.rglob("*.md"):
                # Filename convention: {slug}-{id[:8]}.md or {id}.md
                stem = md_file.stem
                if "-" in stem:
                    partial_id = stem.rsplit("-", 1)[-1]
                    import sqlite3
                    with sqlite3.connect(self.store.db_path) as conn:
                        row = conn.execute(
                            "SELECT id FROM entities WHERE id LIKE ?",
                            (f"{partial_id}%",),
                        ).fetchone()
                    if row is None:
                        results.append(LintResult(
                            rule="index_consistency",
                            severity=LintSeverity.WARNING,
                            message=f"文件存在但数据库中无记录：{md_file.name}",
                            entity_id=partial_id,
                            facet=facet.value,
                            details={"path": str(md_file.relative_to(self.store.wiki_path))},
                        ))
                else:
                    entity_id = stem
                    entity = self.store.get(entity_id)
                    if entity is None:
                        results.append(LintResult(
                            rule="index_consistency",
                            severity=LintSeverity.WARNING,
                            message=f"文件存在但数据库中无记录：{md_file.name}",
                            entity_id=entity_id,
                            facet=facet.value,
                            details={"path": str(md_file.relative_to(self.store.wiki_path))},
                        ))

        return results

    def check_wikilinks(self) -> list[LintResult]:
        """Check that all [[links]] point to existing entities."""
        results = []

        all_entities = self.store.search(limit=10000, include_archived=True)
        known_ids = {e.id for e in all_entities}
        known_titles: set[str] = set()
        for e in all_entities:
            for line in e.content.split("\n"):
                if line.startswith("# "):
                    known_titles.add(line[2:].strip())
                    break
            known_titles.add(e.id)

        for entity in all_entities:
            links = self.parser.parse(entity.content)
            for link in links:
                target = link.target
                if target not in known_ids and target not in known_titles:
                    results.append(LintResult(
                        rule="wikilinks",
                        severity=LintSeverity.WARNING,
                        message=f"死链：[[{target}]] 目标不存在",
                        entity_id=entity.id,
                        facet=entity.facet.value,
                        details={"target": target},
                    ))

        return results

    def check_content_conflicts(self) -> list[LintResult]:
        """Check for potential content conflicts (similar content across entities)."""
        results = []
        entities = self.store.search(limit=1000)

        seen_titles: dict[str, str] = {}
        reported_pairs: set[tuple[str, str]] = set()

        for e in entities:
            # Diary/task-record entries legitimately share titles
            sub_dir = e.metadata.get("_subdir", "") if e.metadata else ""
            if sub_dir in ("diary", "task-record"):
                continue

            title = ""
            for line in e.content.split("\n"):
                if line.startswith("# "):
                    title = line[2:].strip().lower()
                    break

            if title:
                if title in seen_titles:
                    pair = tuple(sorted([e.id, seen_titles[title]]))
                    if pair not in reported_pairs:
                        reported_pairs.add(pair)
                        results.append(LintResult(
                            rule="content_conflict",
                            severity=LintSeverity.WARNING,
                            message=f"标题重复：'{title}'",
                            entity_id=e.id,
                            facet=e.facet.value,
                            details={"duplicate_of": seen_titles[title]},
                        ))
                else:
                    seen_titles[title] = e.id

        try:
            for e in entities:
                sub_dir = e.metadata.get("_subdir", "") if e.metadata else ""
                if sub_dir in ("diary", "task-record"):
                    continue

                query = e.content[:500]
                similar = self.store.search_similar(
                    query=query,
                    facet=e.facet,
                    limit=5,
                )
                for candidate in similar:
                    if candidate.id == e.id:
                        continue
                    if candidate.distance is None:
                        continue
                    # vec_distance_cosine returns cosine distance in [0, 2];
                    # similarity = 1 - distance/2, so threshold 0.95 means distance < 0.1
                    similarity = 1.0 - candidate.distance / 2.0
                    if similarity > 0.95:
                        pair = tuple(sorted([e.id, candidate.id]))
                        if pair not in reported_pairs:
                            reported_pairs.add(pair)
                            results.append(LintResult(
                                rule="content_conflict",
                                severity=LintSeverity.WARNING,
                                message=f"语义重复（相似度 {similarity:.2f}）",
                                entity_id=e.id,
                                facet=e.facet.value,
                                details={
                                    "similarity": similarity,
                                    "duplicate_of": candidate.id,
                                },
                            ))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Vector similarity check skipped: %s", exc)

        return results

    def check_stale_content(self, days: int = 90) -> list[LintResult]:
        """Check for content that hasn't been updated in a while."""
        results = []
        cutoff = datetime.now(UTC) - timedelta(days=days)

        entities = self.store.search(limit=10000)
        for e in entities:
            if e.updated_at and e.updated_at < cutoff:
                days_old = (datetime.now(UTC) - e.updated_at).days
                results.append(LintResult(
                    rule="stale_content",
                    severity=LintSeverity.INFO,
                    message=f"内容已 {days_old} 天未更新",
                    entity_id=e.id,
                    facet=e.facet.value,
                    details={"days_old": days_old},
                ))

        return results

    def check_orphans(self) -> list[LintResult]:
        """Check for orphan entities (never referenced by any other entity)."""
        results = []
        entities = self.store.search(limit=10000, include_archived=True)

        # Build a set of all referenced targets
        referenced: set[str] = set()
        for e in entities:
            for link in self.parser.parse(e.content):
                referenced.add(link.target)

        # Build title -> entity mapping for resolving references by title
        title_to_id: dict[str, str] = {}
        for e in entities:
            title_to_id[e.id] = e.id
            for line in e.content.split("\n"):
                if line.startswith("# "):
                    title_to_id[line[2:].strip()] = e.id
                    break

        # Count references per entity
        ref_counts: dict[str, int] = {e.id: 0 for e in entities}
        for target in referenced:
            entity_id = title_to_id.get(target)
            if entity_id:
                ref_counts[entity_id] = ref_counts.get(entity_id, 0) + 1

        # Pre-extract titles for suggestion scanning
        entity_titles: dict[str, str] = {}
        for e in entities:
            for line in e.content.split("\n"):
                if line.startswith("# "):
                    entity_titles[e.id] = line[2:].strip()
                    break

        for e in entities:
            # Only check concept facet — other facets are standalone documents
            if e.facet != EntityFacet.CONCEPT:
                continue

            if ref_counts.get(e.id, 0) == 0:
                # Scan for documents that mention this orphan's title
                orphan_title = entity_titles.get(e.id, "")
                suggestions: list[str] = []
                if orphan_title:
                    lower_title = orphan_title.lower()
                    for other in entities:
                        if other.id == e.id:
                            continue
                        if lower_title in other.content.lower():
                            other_title = entity_titles.get(other.id, other.id[:8])
                            suggestions.append(f"{other.id[:8]}... ({other_title})")

                details: dict[str, Any] = {}
                if suggestions:
                    details["suggested_references"] = suggestions[:5]  # limit to 5

                results.append(LintResult(
                    rule="orphan",
                    severity=LintSeverity.INFO,
                    message=f"孤儿资源：未被任何页面引用" + (f"，{len(suggestions)} 篇文档提到此标题" if suggestions else ""),
                    entity_id=e.id,
                    facet=e.facet.value,
                    details=details,
                ))

        return results

    def check_crowded_facets(self, threshold: int = 10) -> list[LintResult]:
        """Check if any facet has too many ungrouped entities at root level."""
        import sqlite3

        results = []
        with sqlite3.connect(self.store.db_path) as conn:
            rows = conn.execute(
                "SELECT facet, COUNT(*) FROM entities "
                "WHERE (`group` IS NULL OR `group` = '') "
                "GROUP BY facet HAVING COUNT(*) >= ?",
                (threshold,),
            ).fetchall()

        for facet_str, count in rows:
            try:
                facet = EntityFacet(facet_str)
            except ValueError:
                continue

            with sqlite3.connect(self.store.db_path) as conn:
                group_rows = conn.execute(
                    "SELECT `group`, COUNT(*) FROM entities "
                    "WHERE facet = ? AND `group` IS NOT NULL AND `group` != '' "
                    "GROUP BY `group` ORDER BY COUNT(*) DESC",
                    (facet_str,),
                ).fetchall()
            existing = [f"{g}({c})" for g, c in group_rows]

            results.append(LintResult(
                rule="crowded_facet",
                severity=LintSeverity.WARNING,
                entity_id=None,
                message=f"Facet '{facet_str}' has {count} ungrouped entities (threshold: {threshold})",
                details={
                    "facet": facet_str,
                    "root_count": count,
                    "threshold": threshold,
                    "existing_groups": existing,
                },
            ))

        return results
