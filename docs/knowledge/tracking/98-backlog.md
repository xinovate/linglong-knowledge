# 知识库待办事项

> **定位**：长期产品待办、已知限制和后续优化项。
> **不记录**：短期任务（去 `97-tasks.md`）、阶段方向（去 `99-milestones.md`）、已完成工作（去 `journal/`）。
> **更新时机**：新增 BACKLOG 项、限制状态变化、功能实现后归档。
>
> 创建日期：2026-05-18

---

## 待办总览

| 编号 | 标题 | 分类 | 优先级 | 状态 | 创建日期 |
|------|------|------|--------|------|----------|
| BACKLOG-001 | 同步去重策略 | 数据质量 | 高 | 已完成 | 2026-05-18 |
| BACKLOG-002 | OpenClaw 默认 wiki 路径支持 | 多用户适配 | 中 | 待实现 | 2026-05-18 |
| BACKLOG-003 | 索引文件自动生成 | 存储层 | 中 | 待实现 | 2026-05-18 |
| BACKLOG-004 | 文件名调整为 slug-ID 后缀格式 | 存储层 | 中 | 已完成 | 2026-05-18 |

## 已知限制

| 编号 | 标题 | 分类 | 影响范围 | 状态 | 记录日期 |
|------|------|------|----------|------|----------|
| LIMIT-001 | OpenClaw frontmatter 解析失败 | 数据质量 | 2 个文件同步跳过 | 观察中 | 2026-05-18 |

---

## 待办详情

### BACKLOG-001: 同步去重策略

**关联文件**: `src/linglong/knowledge/store.py`, `src/linglong/knowledge/sync/openclaw.py`

**状态**: 已完成

**实现方案**: 双层去重
- **Layer 1 — ID 去重（源级）**: Entity ID 基于 source path 的 SHA256，同一文件始终相同 ID。`store.create()` 检查 ID 是否存在：相同 content → 幂等跳过；不同 content → 更新（不增加版本）。
- **Layer 2 — Content Hash 去重（跨源）**: 数据库新增 `content_hash` 列。不同 ID 但相同 content hash → 返回已有实体，避免重复创建。
- **语义相近**: 留给 `lint content_conflict` 人工处理。

**测试覆盖**:
- `test_sync_idempotent` — 同一文件同步两次，第二次 skipped
- `test_sync_update_content` — 修改文件后同步，验证 updated
- `test_create_dedup_same_id_same_content` — store 层幂等
- `test_create_dedup_same_id_different_content` — store 层更新
- `test_create_dedup_cross_source_same_content` — store 层跨源去重

**阻塞项**: 已解决。可继续 BACKLOG-002（默认 wiki 路径支持）。

---

### BACKLOG-002: OpenClaw 默认 wiki 路径支持

**关联文件**: `src/linglong/knowledge/sync/openclaw.py`, `src/linglong/cli.py`

**问题**: 当前同步路径为用户定制 wiki（`workspace/memory/wiki`）。其他 OpenClaw 用户使用默认路径 `~/.openclaw/wiki`，无法直接同步。

**当前状态**: 适配器本身路径无关，CLI `--path` 可覆盖，但文档和默认配置未覆盖此场景。

**前置依赖**: BACKLOG-001（去重策略）

**方案**:
1. 完成 BACKLOG-001
2. CLI 默认配置增加 `openclaw_wiki_path` 指向 `~/.openclaw/wiki`
3. 用户定制路径通过 `--path` 覆盖

---

### BACKLOG-004: 文件名调整为 slug-ID 后缀格式

**关联文件**: `src/linglong/knowledge/store.py`, `src/linglong/knowledge/lint.py`

**问题**: 当前文件名格式为 `{id[:8]}-{slug}.md`（如 `b2778921-agent-mastery-项目完成总结.md`），ID 前缀占用空间且降低可读性。

**方案**: 将文件名格式调整为 `{slug}-{id[:8]}.md`（如 `agent-mastery-项目完成总结-b2778921.md`）。
- **优点**: slug 打头，目录列表一眼识别；反查仍为 O(1)；无需改数据库 schema
- **风险评估**: 无碰撞风险（ID 后缀保证唯一）

**实现**:
1. `store.py`: `_get_entity_path()` 调整文件名拼接顺序
2. `lint.py`: `check_index_consistency` ID 提取改为 `rsplit("-", 1)[-1]`
3. 批量重命名现有 331 个文件

**状态**: 已完成（2026-05-20）

**测试**: 253 个测试全部通过

---

### BACKLOG-003: 索引文件自动生成

**关联文件**: `src/linglong/knowledge/indexer.py`, `docs/knowledge/design/02-directory-structure.md`

**问题**: 设计文档规划了 `index.md` + `index-{facet}.md` 索引文件体系，当前仅 `index --rebuild` 生成，且不包含两步索引查询所需的结构。

**当前状态**: `IndexGenerator` 存在但生成的索引不完整。

**方案**: 按 `02-directory-structure.md` 的索引文件规范完善 `IndexGenerator`。

---

## 限制详情

### LIMIT-001: OpenClaw frontmatter 解析失败

**影响文件**:

| 文件 | 原因 |
|------|------|
| `wiki/user/communication-style.md` | YAML block scalar 格式错误 |
| `wiki/emotion/emotion-memory.md` | YAML alias 字符不合法 |

**临时方案**: sync adapter 已有异常捕获，自动跳过。后续可考虑容错解析。
