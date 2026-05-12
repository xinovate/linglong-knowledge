# Plan: ClaudeCodeSyncAdapter — v0.4 跨 Agent 知识同步

## Context

Linglong v0.4 的核心目标是建立跨 Agent 知识统一。OpenClawSyncAdapter 已实现（OpenClaw wiki → Linglong），现在需要对称地实现 Claude Code memory → Linglong 的同步，让 Claude Code 的记忆也能被统一管理和复用。

Claude Code memory 文件存储在 `~/.claude/projects/{project}/memory/`，格式为 Markdown + YAML frontmatter（name, description, type, originSessionId）。

## Design Decisions

### ADR-004: Agent 命名空间前缀

**决策**：各 Agent 的实体 ID 必须带命名空间前缀，避免同一概念在不同 Agent 中冲突。

**理由**：
- OpenClaw 和 Claude Code 可能有同名文件（如 `user/profile.md`）
- 不带前缀会导致后同步的覆盖先同步的
- 前缀格式：`{agent}:{sha256(path)}`

**实现**：
- OpenClaw: `openclaw:{sha256(relative_path)[:16]}`
- Claude Code: `claude:{sha256(filename)[:16]}`

### ADR-005: Memory 类型映射

**决策**：Claude Code memory 的 `type` 字段映射到 Linglong wiki 目录结构。

| Claude Code type | Linglong wiki 目录 | 理由 |
|------------------|-------------------|------|
| `feedback` | `experiences/` | 反馈属于经验 |
| `project` | `projects/` | 项目状态 |
| `user` | `user/` | 用户画像 |
| `reference` | `references/` | 参考资料 |
| (无 type 或未知) | `concepts/` | 默认归类 |

## Tasks

### Task 1: 实现 ClaudeCodeSyncAdapter

**文件**：`src/linglong/knowledge/sync/claude_code.py`（新建）

**接口**：
```python
class ClaudeCodeSyncAdapter:
    def __init__(self, memory_path: str, store: KnowledgeStore) -> None
    def sync_to_linglong(self) -> dict  # {"total": N, "created": N, "failed": N, "skipped": N}
```

**功能要求**：
1. 读取 `memory_path` 下所有 `.md` 文件（不包括 `MEMORY.md` 索引文件）
2. 解析 YAML frontmatter（name, description, type, originSessionId）
3. 将 `type` 映射到 Linglong wiki 目录（见 ADR-005）
4. 生成实体 ID：`claude:{sha256(filename)[:16]}`
5. `created_by`: `"agent:claude"`
6. `status`: `EntityStatus.AUTO_CONFIRMED`
7. `confidence`: `0.95`
8. `sources`: `[Source(type=SourceType.FILE, name="claude-code-memory", url=relative_path)]`
9. `metadata`: 包含 frontmatter 字段 + 原始文件名
10. 冲突检测：如果 `store.get(entity_id)` 已存在，跳过并计入 `skipped`
11. 错误处理：文件读取/解析失败计入 `failed`，不中断批量同步

**关键区别**（与 OpenClawSyncAdapter）：
- Claude Code memory 没有 `[[wikilinks]]`，无需提取
- Claude Code memory 是平铺结构（无子目录），所有文件在 `memory/` 根目录
- 需要跳过 `MEMORY.md`（索引文件，不是知识条目）
- ID 需要命名空间前缀 `claude:`
- 需要冲突检测（跳过已存在）

### Task 2: 编写测试

**文件**：`tests/knowledge/test_claude_code_sync.py`（新建）

**测试用例**：
1. `test_sync_single_feedback` — 同步单个 feedback 类型文件，验证 Entity 字段和 metadata
2. `test_sync_single_project` — 同步单个 project 类型文件，验证目录映射
3. `test_sync_skips_memory_md` — `MEMORY.md` 被跳过
4. `test_sync_skips_existing` — 已存在的实体被跳过（`skipped` 计数）
5. `test_sync_conflict_detection` — 同一 ID 已存在时不覆盖
6. `test_sync_handles_corrupt_file` — 无效 UTF-8 文件计入 failed
7. `test_sync_unknown_type` — 无 type 的文件默认映射到 concepts/

**测试 fixture**：
- `temp_store`: 复用 OpenClawSyncAdapter 测试中的 fixture 模式
- `memory_dir`: `tmp_path / "memory"`
- `_make_memory_file(memory_dir, filename, content)` 辅助函数

### Task 3: 更新模块导出

**文件**：`src/linglong/knowledge/sync/__init__.py`

添加：
```python
from .claude_code import ClaudeCodeSyncAdapter

__all__ = ["OpenClawSyncAdapter", "ClaudeCodeSyncAdapter"]
```

## Files to Create/Modify

| Path | Action |
|------|--------|
| `src/linglong/knowledge/sync/claude_code.py` | 新建 |
| `tests/knowledge/test_claude_code_sync.py` | 新建 |
| `src/linglong/knowledge/sync/__init__.py` | 修改（添加导出） |

## Constraints

- **不修改** `core/models.py`（OpenClawSyncAdapter 已添加 `SourceType.FILE` 和 `Entity.metadata`）
- **不修改** `knowledge/store.py`
- 复用 OpenClawSyncAdapter 的代码结构（`_compute_id`, 错误处理模式）
- 所有新增代码必须通过 `make check`

## Verification

1. 本地运行 `make check`：lint 通过 + 所有测试通过（预计新增 7 个测试，总测试数 80+ → 87+）
2. 手动验证（可选）：在本地临时目录创建 sample memory 文件，运行 adapter，检查 store 中的实体

## Future Agent Integration Roadmap

Based on user feedback (2026-05-12):

| Agent | Status | Storage Location | Priority |
|-------|--------|-----------------|----------|
| OpenClaw | ✅ Shipped | `~/.openclaw/workspace/memory/wiki/` | — |
| Claude Code | 🔄 In Progress | `~/.claude/projects/{project}/memory/` | P0 |
| Codex | ⏳ Planned | `~/.codex/` (`AGENTS.md`, `history.jsonl`, SQLite) | P1 |
| Hermes | ❌ Deprecated | `~/.hermes/memories/` (wiki废弃, 仅保留 MEMORY.md/USER.md/SOUL.md) | P2 |

## Multi-Agent Collaboration Flow

沿用已验证的 Phase 2 流程：

```
Architect（本会话）→ 制定本计划 → ExitPlanMode
    ↓
Developer（子 Agent）→ 实现代码 + 测试
    ↓
Spec Reviewer（子 Agent）→ 审查规格合规性
    ↓
Code Quality Reviewer（子 Agent）→ 审查代码质量
    ↓
Architect → 合并提交 → 推送
```
