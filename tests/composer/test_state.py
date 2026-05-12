"""ComposerState unit tests."""

from datetime import datetime

from linglong.composer.ingest_adapter import MemoryFragment
from linglong.composer.state import ComposerState


class TestPipelineState:
    def test_hash_fragment_deterministic(self):
        """相同内容应产生相同哈希"""
        frag = MemoryFragment(
            source="openclaw",
            content="确定性测试",
            timestamp=datetime(2026, 5, 11, 10, 0, 0),
            metadata={},
            raw_path="",
        )
        h1 = ComposerState._hash_fragment(frag)
        h2 = ComposerState._hash_fragment(frag)
        assert h1 == h2
        assert len(h1) == 32  # MD5 十六进制长度

    def test_hash_fragment_differentiates_content(self):
        """不同内容应产生不同哈希"""
        frag1 = MemoryFragment(
            source="openclaw",
            content="内容A",
            timestamp=datetime(2026, 5, 11, 10, 0, 0),
            metadata={},
            raw_path="",
        )
        frag2 = MemoryFragment(
            source="openclaw",
            content="内容B",
            timestamp=datetime(2026, 5, 11, 10, 0, 0),
            metadata={},
            raw_path="",
        )
        assert ComposerState._hash_fragment(frag1) != ComposerState._hash_fragment(frag2)

    def test_filter_new_returns_only_unprocessed(self, tmp_path):
        """filter_new 应过滤已处理片段，保留新片段"""
        state_file = tmp_path / "state.json"
        state = ComposerState(state_file=state_file)

        frag1 = MemoryFragment(
            source="openclaw",
            content="已处理",
            timestamp=datetime(2026, 5, 11, 10, 0, 0),
            metadata={},
            raw_path="",
        )
        frag2 = MemoryFragment(
            source="openclaw",
            content="新片段",
            timestamp=datetime(2026, 5, 11, 11, 0, 0),
            metadata={},
            raw_path="",
        )

        state.mark_processed([frag1])
        result = state.filter_new([frag1, frag2])

        assert len(result) == 1
        assert result[0].content == "新片段"

    def test_is_processed_after_mark(self, tmp_path):
        """mark_processed 后 is_processed 应返回 True"""
        state_file = tmp_path / "state.json"
        state = ComposerState(state_file=state_file)

        frag = MemoryFragment(
            source="openclaw",
            content="测试片段",
            timestamp=datetime(2026, 5, 11, 10, 0, 0),
            metadata={},
            raw_path="",
        )

        assert not state.is_processed(frag)
        state.mark_processed([frag])
        assert state.is_processed(frag)

    def test_state_persists_to_disk(self, tmp_path):
        """状态应持久化到磁盘，重新加载后仍有效"""
        state_file = tmp_path / "state.json"

        frag = MemoryFragment(
            source="openclaw",
            content="持久化测试",
            timestamp=datetime(2026, 5, 11, 10, 0, 0),
            metadata={},
            raw_path="",
        )

        state1 = ComposerState(state_file=state_file)
        state1.mark_processed([frag])
        del state1

        state2 = ComposerState(state_file=state_file)
        assert state2.is_processed(frag)

    def test_empty_fragments_noop(self, tmp_path):
        """传入空列表不应报错，也不应改变状态"""
        state_file = tmp_path / "state.json"
        state = ComposerState(state_file=state_file)

        state.mark_processed([])
        result = state.filter_new([])
        assert result == []
