# Dispatch 模块启动 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `dispatch/_pending_publishers/` 中的完整发布器实现正式接入 Linglong，创建 `DispatchManager` 消费 composer 的 `dispatch_ready` payload，打通审核-发布闭环。

**Architecture:** 保持现有 Publisher ABC 不变，新增 `DispatchManager` 作为调度核心（ Publisher 发现 → 路由 → 执行 → 状态追踪）。配置通过 `core/config.py` 的 `DispatchConfig` 统一管理。`composer/draft.py` 的 `publish_draft()` 返回的 payload 直接作为 `DispatchManager.publish()` 的输入。

**Tech Stack:** Python 3.11+, pydantic-settings, subprocess (git/hexo/ssh), pytest

---

## File Structure

| Path | Action | Responsibility |
|------|--------|--------------|
| `src/linglong/core/config.py` | Modify | 添加 `DispatchConfig`，注册到 `LinglongConfig` |
| `src/linglong/dispatch/__init__.py` | Modify | 导出 `DispatchManager`, `Publisher`, `PublishResult` |
| `src/linglong/dispatch/manager.py` | Create | `DispatchManager`：Publisher 注册、路由、执行、状态追踪 |
| `src/linglong/dispatch/publishers/__init__.py` | Create | 导出所有 Publisher 实现 |
| `src/linglong/dispatch/publishers/base.py` | Move from `_pending_publishers/` | `Publisher` ABC + `PublishResult`（保持原样） |
| `src/linglong/dispatch/publishers/hexo.py` | Move from `_pending_publishers/` | `HexoPublisher`（Git/Local/SSH 三种工作流） |
| `src/linglong/dispatch/publishers/local.py` | Move from `_pending_publishers/` | `LocalPublisher`（本地文件输出） |
| `tests/dispatch/test_dispatch_manager.py` | Create | `DispatchManager` 注册、路由、mock 发布测试 |
| `tests/dispatch/test_publishers.py` | Create | `LocalPublisher` 文件写入测试，`HexoPublisher` mock 测试 |
| `docs/superpowers/plans/2026-05-12-dispatch-module.md` | Create | 本计划文档（实施前保存） |

---

## Task 1: DispatchConfig 配置扩展

**Files:**
- Modify: `src/linglong/core/config.py`
- Test: `tests/core/test_config.py`

- [ ] **Step 1: 在 `config.py` 中添加 `DispatchConfig`**

在 `IngestConfig` 下方插入：

```python
class DispatchConfig(BaseSettings):
    """Dispatch module configuration."""

    model_config = SettingsConfigDict(env_prefix="LL_DISPATCH_")

    enabled: bool = Field(default=True, description="Enable dispatch module")
    default_publisher: str = Field(default="hexo", description="Default publisher name")
    publishers: list[dict[str, Any]] = Field(
        default_factory=lambda: [
            {
                "name": "hexo",
                "type": "hexo",
                "enabled": True,
                "config": {
                    "hexo_path": "~/blog",
                    "use_git_workflow": True,
                    "git_remote": "origin",
                    "git_branch": "master",
                },
            },
            {
                "name": "local",
                "type": "local",
                "enabled": False,
                "config": {
                    "output_dir": "~/Downloads",
                    "overwrite": False,
                },
            },
        ],
        description="Publisher configurations",
    )
```

- [ ] **Step 2: 将 `dispatch` 注册到 `LinglongConfig`**

在 `LinglongConfig` 类中，找到：

```python
    # Module configs
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    ingest: IngestConfig = Field(default_factory=IngestConfig)
    composer: ComposerConfig = Field(default_factory=ComposerConfig)
```

改为：

```python
    # Module configs
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    ingest: IngestConfig = Field(default_factory=IngestConfig)
    composer: ComposerConfig = Field(default_factory=ComposerConfig)
    dispatch: DispatchConfig = Field(default_factory=DispatchConfig)
```

- [ ] **Step 3: 为 `DispatchConfig` 添加测试断言**

在 `tests/core/test_config.py` 的 `TestLinglongConfig` 类中新增：

```python
def test_dispatch_defaults(self):
    """Test DispatchConfig defaults."""
    config = DispatchConfig()
    assert config.enabled is True
    assert config.default_publisher == "hexo"
    assert len(config.publishers) == 2
    assert config.publishers[0]["name"] == "hexo"
```

- [ ] **Step 4: 运行 config 测试**

Run: `pytest tests/core/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/linglong/core/config.py tests/core/test_config.py
git commit -m "feat(dispatch): add DispatchConfig to core config"
```

---

## Task 2: Publisher 基类正式化

**Files:**
- Move: `src/linglong/dispatch/_pending_publishers/base.py` → `src/linglong/dispatch/publishers/base.py`
- Create: `src/linglong/dispatch/publishers/__init__.py`

- [ ] **Step 1: 创建 `publishers/` 包并迁移 `base.py`**

```bash
mkdir -p src/linglong/dispatch/publishers
cp src/linglong/dispatch/_pending_publishers/base.py src/linglong/dispatch/publishers/base.py
```

`src/linglong/dispatch/publishers/__init__.py`：

```python
"""Linglong dispatch publishers."""

from linglong.dispatch.publishers.base import Publisher, PublishResult

__all__ = ["Publisher", "PublishResult"]
```

- [ ] **Step 2: 运行 import 测试**

Run: `python -c "from linglong.dispatch.publishers import Publisher, PublishResult; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/linglong/dispatch/publishers/
git commit -m "feat(dispatch): formalize Publisher base class under publishers/"
```

---

## Task 3: LocalPublisher 迁移

**Files:**
- Move: `src/linglong/dispatch/_pending_publishers/local.py` → `src/linglong/dispatch/publishers/local.py`
- Create: `tests/dispatch/test_publishers.py`

- [ ] **Step 1: 迁移并修复 import 路径**

```bash
cp src/linglong/dispatch/_pending_publishers/local.py src/linglong/dispatch/publishers/local.py
```

修改 `src/linglong/dispatch/publishers/local.py` 第 10 行：

```python
# 旧
from ..publishers.base import Publisher, PublishResult
# 新
from linglong.dispatch.publishers.base import Publisher, PublishResult
```

更新 `src/linglong/dispatch/publishers/__init__.py`：

```python
from linglong.dispatch.publishers.base import Publisher, PublishResult
from linglong.dispatch.publishers.local import LocalPublisher

__all__ = ["Publisher", "PublishResult", "LocalPublisher"]
```

- [ ] **Step 2: 编写 LocalPublisher 测试**

`tests/dispatch/test_publishers.py`：

```python
"""Tests for dispatch publishers."""

import tempfile
from pathlib import Path

import pytest

from linglong.dispatch.publishers.local import LocalPublisher


def test_local_publisher_article():
    """LocalPublisher writes article to output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {
            "name": "local-test",
            "output_dir": tmpdir,
            "overwrite": False,
        }
        publisher = LocalPublisher(config)
        result = publisher.publish(
            "# Hello World\n\nTest content.",
            {"title": "Test Article", "date": "2026-05-12"},
        )

        assert result.success is True
        assert result.error == ""
        assert (Path(tmpdir) / "2026-05-12_Test_Article.md").exists()


def test_local_publisher_health_check():
    """LocalPublisher health check verifies output dir is writable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {"name": "local-test", "output_dir": tmpdir}
        publisher = LocalPublisher(config)
        assert publisher.health_check() is True
```

- [ ] **Step 3: 运行 publisher 测试**

Run: `pytest tests/dispatch/test_publishers.py -v`
Expected: PASS (2 passed)

- [ ] **Step 4: Commit**

```bash
git add src/linglong/dispatch/publishers/ tests/dispatch/test_publishers.py
git commit -m "feat(dispatch): migrate LocalPublisher with tests"
```

---

## Task 4: HexoPublisher 迁移

**Files:**
- Move: `src/linglong/dispatch/_pending_publishers/hexo.py` → `src/linglong/dispatch/publishers/hexo.py`
- Modify: `tests/dispatch/test_publishers.py`

- [ ] **Step 1: 迁移并修复 import 路径**

```bash
cp src/linglong/dispatch/_pending_publishers/hexo.py src/linglong/dispatch/publishers/hexo.py
```

修改 `src/linglong/dispatch/publishers/hexo.py` 第 7 行：

```python
# 旧
from .base import Publisher, PublishResult
# 新
from linglong.dispatch.publishers.base import Publisher, PublishResult
```

更新 `src/linglong/dispatch/publishers/__init__.py`：

```python
from linglong.dispatch.publishers.base import Publisher, PublishResult
from linglong.dispatch.publishers.hexo import HexoPublisher
from linglong.dispatch.publishers.local import LocalPublisher

__all__ = ["Publisher", "PublishResult", "HexoPublisher", "LocalPublisher"]
```

- [ ] **Step 2: 编写 HexoPublisher mock 测试**

在 `tests/dispatch/test_publishers.py` 中追加：

```python
from unittest.mock import patch

from linglong.dispatch.publishers.hexo import HexoPublisher


def test_hexo_publisher_git_publish_mock():
    """HexoPublisher git workflow mocked."""
    config = {
        "name": "hexo-test",
        "hexo_path": "/tmp/fake-hexo",
        "use_git_workflow": True,
        "git_remote": "origin",
        "git_branch": "main",
    }
    publisher = HexoPublisher(config)

    # Mock hexo_path exists
    with patch("pathlib.Path.exists", return_value=True):
        with patch("subprocess.run", return_value=type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})()):
            result = publisher.publish("# Test", {"title": "Test", "date": "2026-05-12", "slug": "test"})

    assert result.success is True
    assert "Test" in result.message or "test" in result.message
```

- [ ] **Step 3: 运行 publisher 测试**

Run: `pytest tests/dispatch/test_publishers.py -v`
Expected: PASS (3 passed)

- [ ] **Step 4: Commit**

```bash
git add src/linglong/dispatch/publishers/ tests/dispatch/test_publishers.py
git commit -m "feat(dispatch): migrate HexoPublisher with mock tests"
```

---

## Task 5: DispatchManager 核心实现

**Files:**
- Create: `src/linglong/dispatch/manager.py`
- Create: `tests/dispatch/test_dispatch_manager.py`
- Modify: `src/linglong/dispatch/__init__.py`

- [ ] **Step 1: 实现 `DispatchManager`**

`src/linglong/dispatch/manager.py`：

```python
"""Dispatch manager - routes drafts to appropriate publishers."""

import logging
from typing import Any

from linglong.core.config import get_config
from linglong.dispatch.publishers.base import Publisher, PublishResult
from linglong.dispatch.publishers.hexo import HexoPublisher
from linglong.dispatch.publishers.local import LocalPublisher

logger = logging.getLogger(__name__)

_PUBLISHER_REGISTRY: dict[str, type[Publisher]] = {
    "hexo": HexoPublisher,
    "local": LocalPublisher,
}


class DispatchManager:
    """Manages publisher discovery, routing, and execution."""

    def __init__(self) -> None:
        self.config = get_config().dispatch
        self._publishers: dict[str, Publisher] = {}
        self._init_publishers()

    def _init_publishers(self) -> None:
        """Initialize enabled publishers from config."""
        for pub_conf in self.config.publishers:
            if not pub_conf.get("enabled", True):
                continue
            pub_type = pub_conf.get("type")
            pub_name = pub_conf.get("name", pub_type)
            cls = _PUBLISHER_REGISTRY.get(pub_type)
            if cls is None:
                logger.warning("Unknown publisher type: %s", pub_type)
                continue
            self._publishers[pub_name] = cls(pub_conf.get("config", {}))
            logger.info("Initialized publisher: %s", pub_name)

    def publish(self, payload: dict[str, Any], publisher_name: str | None = None) -> PublishResult:
        """Publish a dispatch-ready payload.

        Args:
            payload: dict with ``content``, ``metadata``, ``draft_id``
            publisher_name: Target publisher; defaults to ``DispatchConfig.default_publisher``

        Returns:
            PublishResult: outcome of the publish operation
        """
        name = publisher_name or self.config.default_publisher
        publisher = self._publishers.get(name)
        if publisher is None:
            return PublishResult(
                success=False,
                error=f"Publisher '{name}' not found or not enabled",
            )

        content = payload.get("content", "")
        metadata = payload.get("metadata", {})
        return publisher.publish(content, metadata)

    def health_check(self) -> dict[str, bool]:
        """Run health checks on all initialized publishers."""
        return {
            name: pub.health_check()
            for name, pub in self._publishers.items()
        }

    def list_publishers(self) -> list[str]:
        """Return names of initialized publishers."""
        return list(self._publishers.keys())
```

- [ ] **Step 2: 更新 `dispatch/__init__.py`**

```python
"""Linglong Dispatch - Multi-platform distribution."""

from linglong.dispatch.manager import DispatchManager
from linglong.dispatch.publishers.base import Publisher, PublishResult

__all__ = ["DispatchManager", "Publisher", "PublishResult"]
```

- [ ] **Step 3: 编写 DispatchManager 测试**

`tests/dispatch/test_dispatch_manager.py`：

```python
"""Tests for DispatchManager."""

from unittest.mock import patch

import pytest

from linglong.core.config import LinglongConfig, set_config
from linglong.dispatch.manager import DispatchManager


@pytest.fixture(autouse=True)
def _reset_config(tmp_path):
    config = LinglongConfig(
        data_dir=tmp_path / "data",
        knowledge=LinglongConfig().knowledge.model_copy(
            update={
                "wiki_path": tmp_path / "wiki",
                "db_path": tmp_path / "knowledge.db",
            }
        ),
        dispatch=LinglongConfig().dispatch.model_copy(
            update={
                "enabled": True,
                "default_publisher": "local",
                "publishers": [
                    {
                        "name": "local",
                        "type": "local",
                        "enabled": True,
                        "config": {
                            "output_dir": str(tmp_path / "output"),
                            "overwrite": True,
                        },
                    }
                ],
            }
        ),
    )
    set_config(config)


def test_dispatch_manager_list_publishers():
    """DispatchManager initializes enabled publishers from config."""
    manager = DispatchManager()
    assert manager.list_publishers() == ["local"]


def test_dispatch_manager_publish_routing():
    """DispatchManager routes payload to configured publisher."""
    manager = DispatchManager()
    payload = {
        "draft_id": "test-123",
        "content": "# Hello",
        "metadata": {"title": "Hello", "date": "2026-05-12"},
    }
    result = manager.publish(payload)
    assert result.success is True
    assert "已保存到" in result.message


def test_dispatch_manager_publish_unknown_publisher():
    """Publishing to unknown publisher returns error result."""
    manager = DispatchManager()
    result = manager.publish({}, publisher_name="nonexistent")
    assert result.success is False
    assert "not found" in result.error
```

- [ ] **Step 4: 运行 manager 测试**

Run: `pytest tests/dispatch/test_dispatch_manager.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/linglong/dispatch/
git add tests/dispatch/test_dispatch_manager.py
git commit -m "feat(dispatch): add DispatchManager with publisher registry and routing"
```

---

## Task 6: composer/draft.py 集成验证

**Files:**
- Modify: `src/linglong/composer/draft.py`（可选：添加 `dispatch()` 便捷方法）
- Create: `tests/dispatch/test_integration.py`

- [ ] **Step 1: 编写 composer → dispatch 集成测试**

`tests/dispatch/test_integration.py`：

```python
"""Integration test: composer DraftManager → DispatchManager."""

import tempfile
from pathlib import Path

import pytest

from linglong.composer.draft import DraftManager
from linglong.core.config import LinglongConfig, set_config
from linglong.dispatch.manager import DispatchManager


@pytest.fixture
def integrated_setup(tmp_path):
    drafts_dir = tmp_path / "drafts"
    drafts_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    config = LinglongConfig(
        data_dir=tmp_path / "data",
        composer=LinglongConfig().composer.model_copy(
            update={"drafts_dir": drafts_dir}
        ),
        knowledge=LinglongConfig().knowledge.model_copy(
            update={
                "wiki_path": tmp_path / "wiki",
                "db_path": tmp_path / "knowledge.db",
            }
        ),
        dispatch=LinglongConfig().dispatch.model_copy(
            update={
                "default_publisher": "local",
                "publishers": [
                    {
                        "name": "local",
                        "type": "local",
                        "enabled": True,
                        "config": {
                            "output_dir": str(output_dir),
                            "overwrite": True,
                        },
                    }
                ],
            }
        ),
    )
    set_config(config)
    return {"drafts_dir": drafts_dir, "output_dir": output_dir}


def test_draft_to_publish_pipeline(integrated_setup):
    """Full pipeline: create draft → publish draft → dispatch publishes file."""
    dm = DraftManager()
    draft_id = dm.save_draft(
        content="---\ntitle: Integration Test\ndate: 2026-05-12\n---\n\n# Hello",
        metadata={"title": "Integration Test"},
        source_hashes=["abc123"],
    )

    payload = dm.publish_draft(draft_id)
    assert payload["status"] == "dispatch_ready"

    dispatch = DispatchManager()
    result = dispatch.publish(payload)
    assert result.success is True
    assert (integrated_setup["output_dir"] / "2026-05-12_Integration_Test.md").exists()
```

- [ ] **Step 2: 运行集成测试**

Run: `pytest tests/dispatch/test_integration.py -v`
Expected: PASS (1 passed)

- [ ] **Step 3: Commit**

```bash
git add tests/dispatch/test_integration.py
git commit -m "test(dispatch): add composer-to-dispatch integration test"
```

---

## Task 7: 清理遗留目录 + 全量验证

**Files:**
- Delete: `src/linglong/dispatch/_pending_publishers/` 目录
- Modify: `tests/dispatch/__init__.py`（如不存在则创建）

- [ ] **Step 1: 删除 `_pending_publishers/` 并验证 import 不受影响**

```bash
rm -rf src/linglong/dispatch/_pending_publishers/
python -c "from linglong.dispatch import DispatchManager; from linglong.dispatch.publishers import HexoPublisher, LocalPublisher; print('Imports OK')"
```

Expected: `Imports OK`

- [ ] **Step 2: 运行 make check**

Run: `make check`
Expected: ruff PASS, black PASS, pytest PASS（新增 ~7 个测试，总测试数 103 → ~110）

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore(dispatch): remove _pending_publishers/ stub directory"
```

---

## Spec Coverage Check

| 需求 | 对应 Task | 状态 |
|------|----------|------|
| DispatchConfig 配置 | Task 1 | ✅ |
| Publisher 基类正式化 | Task 2 | ✅ |
| LocalPublisher 迁移 + 测试 | Task 3 | ✅ |
| HexoPublisher 迁移 + 测试 | Task 4 | ✅ |
| DispatchManager 注册/路由/执行 | Task 5 | ✅ |
| composer draft → dispatch 集成 | Task 6 | ✅ |
| 清理遗留 stub 目录 | Task 7 | ✅ |

## Placeholder Scan

无 TBD/TODO/"implement later"/"similar to" 等 placeholder。

## Type Consistency

- `PublishResult` 字段：success, url, message, error — 全 plan 一致
- `Publisher.publish()` 签名：`(content: str, metadata: dict[str, Any]) -> PublishResult` — 全 plan 一致
- `DispatchManager.publish()` 签名：`(payload, publisher_name=None) -> PublishResult` — 全 plan 一致

---

## Execution Handoff

Plan complete. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach do you prefer?
