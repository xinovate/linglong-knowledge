# Plan: 向量搜索落地 — v0.4 收尾

## Context

v0.4 的三个 SyncAdapter（OpenClaw / Claude Code / Codex）已全部完成。验收标准中唯一未达成的是：

> "向量搜索能返回语义相关的结果"

当前状态：
- `sqlite-vec` 未安装，虚拟表从未真正创建
- `KnowledgeStore.search()` 只有过滤搜索（status / created_by），无向量相似度
- `Entity.embedding_id` 存在但从未写入
- `vector_dimensions` 默认 1536，与 OpenClaw 实际使用的 `nomic-embed-text-v1.5`（768 维）不匹配

## Design Decisions

### ADR-008: Embedding 维度对齐

**决策**：`vector_dimensions` 默认改为 **768**，与 nomic-embed-text-v1.5 一致。

**理由**：
- OpenClaw 远程 embedding 服务使用 nomic-embed-text-v1.5
- 该模型输出 768 维向量
- 如果 sqlite-vec 表声明为 1536 维但实际插入 768 维，会报错
- 未来支持其他模型时，通过配置覆盖即可

### ADR-009: Embedding 生成策略

**决策**：同步生成 embedding，但提供配置开关和批量跳过机制。

**理由**：
- 同步实现简单，无需任务队列
- 单次 HTTP 调用约 100-300ms，可接受
- 批量同步时（如 OpenClaw wiki 有数百文件），可通过 `generate_embeddings=False` 跳过，后续用脚本回填

### ADR-010: Embedding 服务双模式

**决策**：优先调用 OpenClaw 远程服务，降级为本地计算（预留接口，当前不实现）。

**理由**：
- OpenClaw 已有成熟服务（`http://localhost:7997`）
- 本地计算需要额外依赖（sentence-transformers 等），增加部署复杂度
- 远程服务失败时，Entity 仍可正常存储（embedding_id 为 None），不影响核心功能

## Tasks

### Task 1: 安装 sqlite-vec 依赖

**文件**：`pyproject.toml`

添加 `sqlite-vec` 到 knowledge 可选依赖组。

### Task 2: 配置扩展

**文件**：`src/linglong/core/config.py`

在 `KnowledgeConfig` 中添加 embedding URL、model、api_key、generate_embeddings 配置，修改 `vector_dimensions` 默认值为 768。

### Task 3: 实现 EmbeddingGenerator

**文件**：`src/linglong/knowledge/embeddings.py`（新建）

调用 OpenClaw embedding 服务 HTTP API，超时处理，失败降级。

### Task 4: 扩展 KnowledgeStore

**文件**：`src/linglong/knowledge/store.py`

- `create`/`update` 时自动生成 embedding
- 新增 `search_similar` 方法（向量相似度搜索）

### Task 5: 编写测试

**文件**：`tests/knowledge/test_embeddings.py`（新建）
**文件**：`tests/knowledge/test_store.py`（修改）

### Task 6: 为已有实体回填 Embedding（可选脚本）

**文件**：`scripts/backfill_embeddings.py`（新建，可选）

## Files to Create/Modify

| Path | Action |
|------|--------|
| `pyproject.toml` | 修改（添加 sqlite-vec 依赖） |
| `src/linglong/core/config.py` | 修改（embedding 配置 + vector_dimensions=768） |
| `src/linglong/knowledge/embeddings.py` | 新建（EmbeddingGenerator） |
| `src/linglong/knowledge/store.py` | 修改（create/update/search_similar） |
| `tests/knowledge/test_embeddings.py` | 新建 |
| `tests/knowledge/test_store.py` | 修改（补充向量相关测试） |
| `scripts/backfill_embeddings.py` | 新建（可选） |

## Constraints

- **必须修改** `core/config.py`（KnowledgeConfig 扩展）
- **必须修改** `knowledge/store.py`（CRUD 扩展）
- 新增 `embeddings.py` 不破坏现有接口
- 所有新增代码必须通过 `make check`
- sqlite-vec 为可选依赖：未安装时 graceful 降级，不影响基础功能

## Verification

1. 本地运行 `make check`：lint 通过 + 所有测试通过
2. 手动验证：
   - 创建 Entity 后检查 SQLite 中 `entity_embeddings` 表是否有记录
   - 调用 `search_similar("某个查询")` 返回语义相关结果
   - 关闭 sqlite-vec 时，Entity 仍能正常创建和搜索（降级）
