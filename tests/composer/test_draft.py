"""DraftManager tests."""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from linglong.core.config import LinglongConfig, set_config
from linglong.composer.draft import DraftManager, DraftEntry


class TestDraftManager:
    """DraftManager tests"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, monkeypatch):
        """每个测试用独立临时目录和配置"""
        self.tmpdir = Path(tempfile.mkdtemp())
        config = LinglongConfig(
            data_dir=self.tmpdir / "data",
            knowledge=LinglongConfig().knowledge.model_copy(
                update={
                    "wiki_path": self.tmpdir / "wiki",
                    "db_path": self.tmpdir / "knowledge.db",
                }
            ),
            composer=LinglongConfig().composer.model_copy(
                update={"drafts_dir": self.tmpdir / "drafts"}
            ),
        )
        set_config(config)
        self.dm = DraftManager()
        yield
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_draft_creates_files(self):
        """保存草稿应创建文件和状态"""
        entry = self.dm.save_draft(
            title="测试标题",
            date="2026-05-11",
            content="# 测试内容",
            metadata={"title": "测试标题", "tags": ["AI"], "excerpt": "摘要"},
            fragment_hashes=["abc123"],
        )

        assert len(entry.id) == 6
        assert entry.status == "pending"
        assert entry.title == "测试标题"

        draft_dir = self.tmpdir / "drafts" / entry.id
        assert (draft_dir / "article.md").exists()
        assert (draft_dir / "review.md").exists()
        assert (draft_dir / "metadata.json").exists()

        content = (draft_dir / "article.md").read_text(encoding="utf-8")
        assert content == "# 测试内容"

        meta = json.loads((draft_dir / "metadata.json").read_text(encoding="utf-8"))
        assert meta["title"] == "测试标题"
        assert meta["tags"] == ["AI"]

    def test_list_drafts_filters_by_status(self):
        """列出草稿应按状态筛选"""
        e1 = self.dm.save_draft("草稿1", "2026-05-11", "内容1", {"title": "草稿1"}, ["h1"])
        e2 = self.dm.save_draft("草稿2", "2026-05-12", "内容2", {"title": "草稿2"}, ["h2"])

        # 废弃第二个
        self.dm.discard_draft(e2.id)

        pending = self.dm.list_drafts(status="pending")
        assert len(pending) == 1
        assert pending[0].id == e1.id

        discarded = self.dm.list_drafts(status="discarded")
        assert len(discarded) == 1
        assert discarded[0].id == e2.id

        all_drafts = self.dm.list_drafts(status=None)
        assert len(all_drafts) == 2

    def test_get_draft_returns_none_for_missing(self):
        """获取不存在的草稿应返回 None"""
        assert self.dm.get_draft("nonexist") is None

    def test_publish_draft_success(self):
        """发布草稿应更新状态并返回 dispatch-ready payload"""
        entry = self.dm.save_draft(
            title="发布测试",
            date="2026-05-11",
            content="正文",
            metadata={"title": "发布测试", "tags": []},
            fragment_hashes=["h1"],
        )

        result = self.dm.publish_draft(entry.id)

        assert result["status"] == "dispatch_ready"
        assert result["draft_id"] == entry.id
        assert "content" in result
        assert "metadata" in result

        updated = self.dm.get_draft(entry.id)
        assert updated.status == "published"
        assert updated.published_at is not None

    def test_publish_draft_prevents_double_publish(self):
        """已发布的草稿不能再次发布"""
        entry = self.dm.save_draft("双发测试", "2026-05-11", "正文", {"title": "双发测试"}, ["h1"])

        self.dm.publish_draft(entry.id)
        with pytest.raises(ValueError, match="已发布"):
            self.dm.publish_draft(entry.id)

    def test_discard_draft_deletes_files(self):
        """废弃草稿应删除文件"""
        entry = self.dm.save_draft("废弃测试", "2026-05-11", "正文", {"title": "废弃测试"}, ["h1"])
        draft_dir = self.tmpdir / "drafts" / entry.id

        assert draft_dir.exists()
        self.dm.discard_draft(entry.id, keep=False)
        assert not draft_dir.exists()

        updated = self.dm.get_draft(entry.id)
        assert updated.status == "discarded"

    def test_discard_draft_keep_moves_to_discard_dir(self):
        """废弃草稿带 keep 应移动到 discard 目录"""
        entry = self.dm.save_draft("保留测试", "2026-05-11", "正文", {"title": "保留测试"}, ["h1"])
        draft_dir = self.tmpdir / "drafts" / entry.id

        self.dm.discard_draft(entry.id, keep=True)
        assert not draft_dir.exists()
        assert (self.tmpdir / "drafts" / "discard" / entry.id / "article.md").exists()

    def test_read_draft_metadata(self):
        """读取保存的元数据"""
        entry = self.dm.save_draft(
            title="元数据测试",
            date="2026-05-11",
            content="正文",
            metadata={"title": "元数据测试", "tags": ["AI", "工程"], "excerpt": "摘要内容"},
            fragment_hashes=["h1"],
        )

        meta = self.dm.read_draft_metadata(entry.id)
        assert meta["title"] == "元数据测试"
        assert meta["tags"] == ["AI", "工程"]

    def test_get_word_count(self):
        """字数统计"""
        entry = self.dm.save_draft(
            title="字数测试",
            date="2026-05-11",
            content="这是一个测试内容。Hello world!",
            metadata={"title": "字数测试"},
            fragment_hashes=[],
        )

        wc = self.dm.get_word_count(entry.id)
        # 中文字符 8 个 + 英文单词 2 个 = 10
        assert wc == 10

    def test_review_content_generated(self):
        """审核摘要应包含检查项"""
        entry = self.dm.save_draft(
            title="审核摘要测试",
            date="2026-05-11",
            content="正文",
            metadata={"title": "审核摘要测试", "excerpt": "摘要", "tags": ["测试"]},
            fragment_hashes=["h1", "h2"],
        )

        review = self.dm.read_draft_review(entry.id)
        assert "审核检查项" in review
        assert "标题长度 10–18 汉字" in review
        assert "来源片段**: 2 条" in review
