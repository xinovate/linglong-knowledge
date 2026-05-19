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
    rule: str           # 规则名称
    severity: LintSeverity
    message: str        # 问题描述
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
        return results

    def fix_all(self, results: list[LintResult] | None = None, stale_days: int = 90) -> list[LintResult]:
        """Auto-fix issues where possible. Returns updated results."""
        if results is None:
            results = self.run_all(stale_days=stale_days)

        # 先处理 index_consistency
        for r in results:
            if r.fixed:
                continue
            if r.rule == "index_consistency" and r.entity_id:
                # 删除孤立文件（优先使用 details 中记录的实际路径）
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

        # 再处理 wikilinks — 按实体聚合后批量修复
        wikilink_results = [r for r in results if r.rule == "wikilinks" and not r.fixed and r.entity_id]
        if wikilink_results:
            self._fix_wikilinks(wikilink_results)

        return results

    def _fix_wikilinks(self, results: list[LintResult]) -> None:
        """Batch-fix dead wikilinks by converting [[target]] to plain text."""
        import re

        # 按 entity_id 聚合死链目标
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
                    # 标记该实体相关的所有 wikilink 结果为已修复
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

        # 检查每个分面目录
        for facet in EntityFacet:
            facet_dir = wiki_path / facet.value
            if not facet_dir.exists():
                continue

            for md_file in facet_dir.rglob("*.md"):
                # 验证文件在 SQLite 中存在
                # 文件名格式：{id[:8]}-{slug}.md 或 {id}.md
                stem = md_file.stem
                if "-" in stem:
                    partial_id = stem.split("-", 1)[0]
                    # 用前8位模糊匹配数据库
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

        # 获取所有实体标题/ID 集合
        all_entities = self.store.search(limit=10000, include_archived=True)
        known_ids = {e.id for e in all_entities}
        known_titles: set[str] = set()
        for e in all_entities:
            # 从 content 提取标题（第一行 # heading）
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

        # 简单去重：检查标题重复
        seen_titles: dict[str, str] = {}
        for e in entities:
            # 豁免 memory 目录的标题重复（diary 和 task-record 的标题重复是正常的）
            sub_dir = e.metadata.get("_subdir", "") if e.metadata else ""
            if sub_dir in ("diary", "task-record"):
                continue

            title = ""
            for line in e.content.split("\n"):
                if line.startswith("# "):
                    title = line[2:].strip().lower()
                    break

            if not title:
                continue

            if title in seen_titles:
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
