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

        for r in results:
            if r.fixed:
                continue
            if r.rule == "index_consistency" and r.entity_id:
                # 删除孤立文件
                if r.facet:
                    orphan = self.store.wiki_path / r.facet / f"{r.entity_id}.md"
                    if orphan.exists():
                        orphan.unlink()
                        r.fixed = True
                        r.message += " (已修复：删除孤立文件)"
        return results

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

            for md_file in facet_dir.glob("*.md"):
                # 验证文件在 SQLite 中存在
                entity_id = md_file.stem
                entity = self.store.get(entity_id)
                if entity is None:
                    results.append(LintResult(
                        rule="index_consistency",
                        severity=LintSeverity.WARNING,
                        message=f"文件存在但数据库中无记录：{md_file.name}",
                        entity_id=entity_id,
                        facet=facet.value,
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
