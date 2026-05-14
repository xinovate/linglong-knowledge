# 知识库模块实施方案

> 日期：2026-05-14
> 状态：已确认
> 依据：设计文档 00-08 + 参考研究

---

## 背景

Linglong 知识库设计阶段完成（9 篇设计文档 + 6 篇参考研究），现进入实施阶段。当前代码库已有 Entity 模型、KnowledgeStore（SQLite + sqlite-vec）、ReviewEngine、3 个 Sync Adapter，但缺少 facet 分类、FTS5 搜索、CLI 知识库命令、索引生成、lint 巡检等核心能力。

## 策略

分 4 个 Milestone 交付，每个 M 可独立验证，按依赖关系顺序执行。

---

## M1：数据模型 + 存储层重构

### 目标

Entity 有 facet，KnowledgeStore 支持三层存储 + FTS5，搜索能按 facet 过滤。

### 任务

| # | 任务 | 关键文件 | 说明 |
|---|------|----------|------|
| 1.1 | EntityFacet 枚举 | `core/models.py` | 7 分面：source/entity/concept/synthesis/experience/methodology/personal |
| 1.2 | Entity 增加 facet + archived_at | `core/models.py` | facet 必填，archived_at 默认 None |
| 1.3 | KnowledgeConfig 扩展 | `core/config.py` | write_mode, search_mode, auto_index, max_versions, lock_timeout, db_mode |
| 1.4 | FTS5 全文搜索 | `knowledge/store.py` | 建虚拟表 entity_fts，create/update/delete 同步 |
| 1.5 | search() 重写 | `knowledge/store.py` | 支持 query + facet + status + created_by + since + limit 过滤 |
| 1.6 | wiki 目录存储 | `knowledge/store.py` | create 时写入 wiki/{facet}/ 目录，frontmatter 规范 |
| 1.7 | update() 版本管理 | `knowledge/store.py` | --content 产生新版本，--append 就地更新 |
| 1.8 | archive() 方法 | `knowledge/store.py` | 标记 archived_at + 移入 archive/YYYY-MM/ |
| 1.9 | 测试对齐 | `tests/knowledge/` | 更新现有测试 + 新增 facet/FTS5/版本/归档测试 |

### 验证

```bash
pytest tests/knowledge/ -v  # 全绿
python -c "
from linglong.knowledge.store import KnowledgeStore
from linglong.core.models import Entity, EntityFacet
s = KnowledgeStore()
e = s.create(Entity(content='测试', facet=EntityFacet.CONCEPT, created_by='agent:claude'))
assert e.facet == EntityFacet.CONCEPT
results = s.search(query='测试', facet=EntityFacet.CONCEPT)
assert len(results) > 0
"
```

---

## M2：CLI 命令（核心 CRUD）

### 目标

6 个知识库 CLI 命令可用。

### 任务

| # | 任务 | 关键文件 | 说明 |
|---|------|----------|------|
| 2.1 | CLI 子命令框架 | `cli.py` | 知识库子命令组，保持现有 ingest/compose/publish/sync |
| 2.2 | linglong write | `cli.py` | --facet 必填 + --title + --content/--from-file + --yes + --no-index |
| 2.3 | linglong read | `cli.py` | 按 ID 或 --path 读取，--format json/markdown |
| 2.4 | linglong search | `cli.py` | --facet / --mode keyword/vector/hybrid/auto / --deep / --limit / --since |
| 2.5 | linglong update | `cli.py` | --content / --append / --metadata / --history / --show-version |
| 2.6 | linglong review | `cli.py` | --list-pending / --approve / --reject |
| 2.7 | linglong archive | `cli.py` | 按 ID + --older-than |
| 2.8 | CLI 测试 | `tests/test_cli.py` | 每个命令的集成测试 |

### 验证

```bash
linglong write --facet concept --title "测试知识" --content "Hello Linglong"
linglong search "测试"
linglong read <id>
linglong update <id> --append "补充内容"
linglong archive <id>
```

---

## M3：索引 + 巡检

### 目标

index.md 自动生成，lint 能检测死链/孤儿/冲突。

### 任务

| # | 任务 | 关键文件 | 说明 |
|---|------|----------|------|
| 3.1 | IndexGenerator | 新建 `knowledge/indexer.py` | 扫描 wiki/ → index.md + 7 个 index-*.md |
| 3.2 | LintEngine | 新建 `knowledge/lint.py` | 索引一致性 + WikiLinks + 内容冲突 + 过期检测 |
| 3.3 | 操作日志 | `knowledge/store.py` | create/update/archive/lint 写入 log.md |
| 3.4 | WikiLinks 解析 | 新建 `knowledge/wikilinks.py` | 提取 [[target]] → 填充 relations |
| 3.5 | CLI 命令 | `cli.py` | linglong lint / linglong index / linglong stats |
| 3.6 | 测试 | `tests/knowledge/` | 索引 + 巡检 + WikiLinks |

### 验证

```bash
linglong lint                  # 输出结构化报告
linglong index --rebuild       # 生成完整索引
linglong index --facet concept # 查看分类索引
linglong stats                 # 统计信息
```

---

## M4：init + 并发 + 集成

### 目标

新电脑 linglong init 即可使用，多 Agent 并发安全。

### 任务

| # | 任务 | 关键文件 | 说明 |
|---|------|----------|------|
| 4.1 | linglong init | `cli.py` + 新建 `knowledge/init.py` | 裸初始化 + --from-git + --from-backup + --from-openclaw |
| 4.2 | 文件锁 | 新建 `knowledge/lock.py` | fcntl.flock 全局写锁 + 可配置超时 |
| 4.3 | SQLite WAL | `knowledge/store.py` | journal_mode=WAL + busy_timeout |
| 4.4 | linglong migrate | `cli.py` | 从 OpenClaw wiki 迁移 |
| 4.5 | 端到端集成测试 | `tests/integration/` | init → write → search → update → lint → archive |
| 4.6 | 文档更新 | CLAUDE.md / docs/ | 更新 CLI 命令说明 |

### 验证

```bash
# 全新目录
linglong init
linglong write --facet concept --title "首条知识" --content "Hello"
linglong search "首条"
linglong lint
linglong stats
```

---

## 依赖关系

```
M1 → M2 → M3 → M4
```

每个 M 结束时：全部测试通过 + 手动验证命令可用。

## 现有代码影响

| 文件 | 影响 | 说明 |
|------|------|------|
| `core/models.py` | 修改 | 增加 EntityFacet、archived_at |
| `core/config.py` | 修改 | KnowledgeConfig 增加字段 |
| `knowledge/store.py` | 重构 | FTS5 + wiki 存储 + facet + 版本管理 + 归档 |
| `knowledge/review.py` | 小改 | ReviewEngine 支持 facet 相关规则 |
| `knowledge/embeddings.py` | 不变 | 已实现 |
| `knowledge/sync/*.py` | 小改 | 适配 facet 字段 |
| `cli.py` | 扩展 | 增加知识库子命令组 |
| `tests/` | 扩展 | 每阶段新增测试 |

## 新增文件

| 文件 | M | 说明 |
|------|---|------|
| `knowledge/indexer.py` | M3 | 索引生成器 |
| `knowledge/lint.py` | M3 | 巡检引擎 |
| `knowledge/wikilinks.py` | M3 | WikiLinks 解析 |
| `knowledge/init.py` | M4 | 初始化逻辑 |
| `knowledge/lock.py` | M4 | 文件锁 |
