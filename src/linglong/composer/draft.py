"""Draft manager."""

import json
import logging
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from linglong.core.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class DraftEntry:
    """Draft entry metadata."""

    id: str
    title: str
    date: str
    status: str  # pending | needs_review | published | discarded
    created_at: str
    published_at: str | None = None
    fragment_hashes: list[str] | None = None
    markdown_path: str = ""
    review_path: str = ""

    def __post_init__(self):
        if self.fragment_hashes is None:
            self.fragment_hashes = []


class DraftManager:
    """Manage drafts for human review before publishing."""

    def __init__(self, drafts_dir: Path | None = None):
        self.drafts_dir = drafts_dir or get_config().composer.drafts_dir
        self.state_file = self.drafts_dir / "state.json"
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Ensure directory structure exists."""
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        (self.drafts_dir / "discard").mkdir(exist_ok=True)

    def _load_state(self) -> dict:
        """Load state file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"状态文件加载失败: {e}，将创建新状态")
        return {"version": 1, "drafts": []}

    def _save_state(self, state: dict):
        """Save state file."""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def _generate_id(self) -> str:
        """Generate short ID."""
        return uuid.uuid4().hex[:6]

    def save_draft(
        self,
        title: str,
        date: str,
        content: str,
        metadata: dict[str, Any],
        fragment_hashes: list[str],
        needs_review: bool = False,
    ) -> DraftEntry:
        """Save a draft.

        Args:
            title: Article title
            date: Date (YYYY-MM-DD)
            content: Markdown content
            metadata: Metadata (tags, categories, excerpt, etc.)
            fragment_hashes: Associated fragment hash list

        Returns:
            DraftEntry: Draft entry
        """
        draft_id = self._generate_id()
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        day_dir = self.drafts_dir / today
        day_dir.mkdir(parents=True, exist_ok=True)
        draft_dir = day_dir / draft_id
        draft_dir.mkdir(exist_ok=True)

        # 写入 Markdown
        md_path = draft_dir / "article.md"
        md_path.write_text(content, encoding="utf-8")

        # 保存元数据
        meta_path = draft_dir / "metadata.json"
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        # 生成审核摘要
        review_content = self._build_review(metadata, fragment_hashes)
        review_path = draft_dir / "review.md"
        review_path.write_text(review_content, encoding="utf-8")

        # 更新状态
        state = self._load_state()
        entry = DraftEntry(
            id=draft_id,
            title=title,
            date=date,
            status="needs_review" if needs_review else "pending",
            created_at=datetime.now(UTC).isoformat(),
            fragment_hashes=fragment_hashes,
            markdown_path=str(md_path),
            review_path=str(review_path),
        )
        state["drafts"].append(asdict(entry))
        self._save_state(state)

        logger.info(f"草稿已保存: {draft_id} - {title}")
        return entry

    def _build_review(self, metadata: dict[str, Any], fragment_hashes: list[str]) -> str:
        """Generate review summary Markdown."""
        title = metadata.get("title", "无标题")
        excerpt = metadata.get("excerpt", "")
        tags = metadata.get("tags", [])
        categories = metadata.get("categories", [])
        cover = metadata.get("cover_image", "未生成")

        lines = [
            f"# 审核摘要: {title}",
            "",
            f"- **标题**: {title} ({len(title)} 字符)",
            f"- **摘要**: {excerpt[:100]}..." if len(excerpt) > 100 else f"- **摘要**: {excerpt}",
            f"- **标签**: {', '.join(tags) if tags else '无'}",
            f"- **分类**: {', '.join(categories) if categories else '无'}",
            f"- **封面**: {cover}",
            f"- **来源片段**: {len(fragment_hashes)} 条",
            "",
            "## 审核检查项",
            "",
            "- [ ] 标题长度 10–18 汉字",
            "- [ ] 摘要质量 30–40 汉字",
            "- [ ] 标签准确、不重复",
            "- [ ] 正文有核心洞察，非简单拼接",
            "- [ ] 封面图适配（如有）",
            "",
            "## 修改建议",
            "",
            "（如需修改，直接编辑 article.md 后执行 `linglong publish <id>`）",
            "",
        ]
        return "\n".join(lines)

    def list_drafts(self, status: str | None = "pending") -> list[DraftEntry]:
        """List drafts.

        Args:
            status: Filter status (pending | published | discarded | None for all)

        Returns:
            List[DraftEntry]: Draft list
        """
        state = self._load_state()
        drafts = []
        for d in state.get("drafts", []):
            entry = DraftEntry(**d)
            if status is None or entry.status == status:
                drafts.append(entry)
        return sorted(drafts, key=lambda x: x.created_at, reverse=True)

    def get_draft(self, draft_id: str) -> DraftEntry | None:
        """Get draft details."""
        state = self._load_state()
        for d in state.get("drafts", []):
            if d["id"] == draft_id:
                return DraftEntry(**d)
        return None

    def read_draft_content(self, draft_id: str) -> str | None:
        """Read draft Markdown content."""
        entry = self.get_draft(draft_id)
        if not entry:
            return None
        path = Path(entry.markdown_path)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def read_draft_review(self, draft_id: str) -> str | None:
        """Read review summary."""
        entry = self.get_draft(draft_id)
        if not entry:
            return None
        path = Path(entry.review_path)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def read_draft_metadata(self, draft_id: str) -> dict[str, Any] | None:
        """Read saved draft metadata."""
        entry = self.get_draft(draft_id)
        if not entry:
            return None
        meta_path = Path(entry.markdown_path).parent / "metadata.json"
        if meta_path.exists():
            try:
                with open(meta_path, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                pass
        return None

    def publish_draft(
        self, draft_id: str, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Prepare a draft for dispatch.

        In the modular architecture, pipeline does not publish directly.
        This method returns a dispatch-ready payload for the dispatch module.

        Args:
            draft_id: Draft ID
            metadata: Optional override metadata

        Returns:
            Dict containing content and metadata for dispatch
        """
        entry = self.get_draft(draft_id)
        if not entry:
            raise FileNotFoundError(f"草稿 {draft_id} 不存在")

        if entry.status == "published":
            raise ValueError(f"草稿 {draft_id} 已发布")

        if entry.status == "discarded":
            raise ValueError(f"草稿 {draft_id} 已废弃")

        content = self.read_draft_content(draft_id)
        if content is None:
            raise FileNotFoundError(f"草稿 {draft_id} 内容丢失")

        pub_metadata = metadata or self.read_draft_metadata(draft_id) or {}

        # 更新状态
        state = self._load_state()
        for d in state.get("drafts", []):
            if d["id"] == draft_id:
                d["status"] = "published"
                d["published_at"] = datetime.now(UTC).isoformat()
                break
        self._save_state(state)
        logger.info(f"草稿已标记为发布就绪: {draft_id}")

        return {
            "draft_id": draft_id,
            "content": content,
            "metadata": pub_metadata,
            "status": "dispatch_ready",
        }

    def discard_draft(self, draft_id: str, keep: bool = False) -> bool:
        """Discard a draft.

        Args:
            draft_id: Draft ID
            keep: Whether to keep files (move to discard/)

        Returns:
            bool: Success
        """
        entry = self.get_draft(draft_id)
        if not entry:
            logger.warning(f"草稿 {draft_id} 不存在")
            return False

        draft_dir = Path(entry.markdown_path).parent

        if keep:
            discard_dir = self.drafts_dir / "discard" / draft_id
            if discard_dir.exists():
                shutil.rmtree(discard_dir)
            shutil.move(str(draft_dir), str(discard_dir))
            logger.info(f"草稿已移动到 discard/: {draft_id}")
        else:
            if draft_dir.exists():
                shutil.rmtree(draft_dir)
            logger.info(f"草稿已删除: {draft_id}")

        # 更新状态
        state = self._load_state()
        for d in state.get("drafts", []):
            if d["id"] == draft_id:
                d["status"] = "discarded"
                break
        self._save_state(state)

        return True

    def get_word_count(self, draft_id: str) -> int:
        """Get draft word count."""
        content = self.read_draft_content(draft_id)
        if content is None:
            return 0
        chinese_chars = len(__import__("re").findall(r"[\u4e00-\u9fff]", content))
        english_words = len(__import__("re").findall(r"[a-zA-Z]+", content))
        return chinese_chars + english_words
