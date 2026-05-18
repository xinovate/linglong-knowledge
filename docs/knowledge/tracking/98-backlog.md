# 知识库待办事项

> 创建日期：2026-05-18
> 记录已完成设计但暂未实现的功能、已知限制和后续优化项。

---

## 待办总览

| 编号 | 标题 | 分类 | 优先级 | 状态 | 创建日期 |
|------|------|------|--------|------|----------|
| BACKLOG-001 | 同步去重策略 | 数据质量 | 高 | 待实现 | 2026-05-18 |
| BACKLOG-002 | OpenClaw 默认 wiki 路径支持 | 多用户适配 | 中 | 待实现 | 2026-05-18 |
| BACKLOG-003 | 索引文件自动生成 | 存储层 | 中 | 待实现 | 2026-05-18 |

## 已知限制

| 编号 | 标题 | 分类 | 影响范围 | 状态 | 记录日期 |
|------|------|------|----------|------|----------|
| LIMIT-001 | OpenClaw frontmatter 解析失败 | 数据质量 | 2 个文件同步跳过 | 观察中 | 2026-05-18 |

---

## 待办详情

### BACKLOG-001: 同步去重策略

**关联文件**: `src/linglong/knowledge/sync/openclaw.py`

**问题**: 多数据源同步时，相同内容的文件会产生重复 Entity（ID 不同，内容相同）。例如 OpenClaw 默认 wiki（`~/.openclaw/wiki`）与用户定制 wiki（`~/.openclaw/workspace/memory/wiki`）可能包含重叠内容。

**当前状态**: `store.create` 的去重仅按标题做模糊匹配，非严格 content hash 去重。

**方案**: 引入 content hash 去重或 source URL 去重，同步时自动跳过已存在的条目。

**阻塞项**: 解决去重后，可支持 BACKLOG-002（默认 wiki 路径同步）。

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
