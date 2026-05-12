# 测试策略

本文档定义 linglong 的分层测试策略，覆盖单元测试、集成测试与端到端（E2E）测试。

## 测试目标

1. 保证核心数据结构与工具函数的行为正确（配置加载、状态管理、模型验证）。
2. 保证各模块抽象的实现符合契约（Store / Distiller / Template）。
3. 保证 CLI 主流程在真实环境中可运行，输出符合预期。

## 测试分层

### 1. 单元测试（Unit Tests）

**范围**：不依赖外部服务、不读写真实文件系统的纯逻辑测试。

**覆盖模块**：

| 模块 | 测试要点 |
|------|----------|
| `core.config` | `LinglongConfig` 加载、默认值、`ComposerConfig` 嵌套属性读取 |
| `core.models` | `Entity` 构造、`AgentID`/`HumanID` 验证、`ConfidenceScore` 边界 |
| `composer.state` | 内容哈希计算、去重逻辑、`filter_new` 与 `mark_processed` 状态流转 |
| `composer.draft` | `DraftManager` 保存/列出/发布/废弃、状态持久化 |
| `composer.distiller` | `IngestAdapter.adapt()`、`DailyAggregator.aggregate()`、`ArticleMaterial.compile_content()` |

**技术选型**：pytest + `tmp_path` / `monkeypatch` 隔离文件系统。

**运行方式**：

```bash
cd /home/user/projects/linglong
source venv/bin/activate
python -m pytest tests/ -v
```

### 2. 集成测试（Integration Tests）

**范围**：跨模块协作，使用 Mock 替代外部依赖（LLM API、文件系统）。

**测试场景**：

- **KnowledgeStore + Entity**: 构造 `Entity` 写入 `KnowledgeStore`，验证 `search()` 能正确按 `status` 过滤。
- **Composer 编排**: 注入 `KnowledgeStore` fixture，验证 `Composer.run()` 的完整调用链（提取 → 聚合 → 模板 → 输出）。
- **Draft 生命周期**: 验证 `Composer.run(draft=True)` 生成的草稿可被 `DraftManager` 读取、发布、废弃。

**Mock 原则**：

- 对文件系统：使用 `tempfile.TemporaryDirectory()` 创建临时目录，通过 `set_config()` 注入隔离配置。
- 对 LLM：使用 `unittest.mock.patch` 替换 `LLMClient.call()`。
- 对网络：使用 `responses` 或 `httpx.MockTransport`（未来引入 LLM 调用时）。

### 3. 端到端测试（E2E / Manual Validation）

**范围**：在真实环境中运行 CLI，验证人机交互与外部系统联动。

**执行方式**：手动执行，按《test-cases.md》中的清单逐项检查。

**典型场景**：

- `Composer.run(dry_run=True)`：验证不触发实际发布、不标记已处理。
- `Composer.run(draft=True)`：验证草稿保存到独立目录，不污染输出。
- 真实 KnowledgeStore：验证生成文件格式正确、frontmatter 完整、`<!-- more -->` 唯一。

## pytest 环境搭建

### 安装依赖

```bash
pip install -e ".[dev]"
```

### 目录结构

```
tests/
  core/              # core 模块测试
    test_config.py
    test_models.py
  ingest/            # ingest 模块测试（待补充）
  knowledge/         # knowledge 模块测试
    test_store.py
  composer/          # composer 模块测试
    test_composer.py
    test_state.py
    test_draft.py
    test_distiller.py
```

### 常用配置

在 `pyproject.toml` 中已配置：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

## 测试纪律

1. **新增功能必带测试**：任何向 `src/linglong/` 提交的代码变更，应至少包含对应的单元测试。
2. **Mock 外部依赖**：禁止在自动化测试中调用真实 LLM API、访问真实文件系统（使用 `tempfile` 隔离）。
3. **状态隔离**：`ComposerState` 和 `DraftManager` 的测试必须使用临时目录，避免污染开发者本地的 `~/.linglong/`。
4. **配置隔离**：使用 `set_config()` 注入临时 `LinglongConfig`，确保测试之间互不干扰。
5. **持续集成（未来）**：在 CI 中执行 `pytest tests/`，失败即阻断合并。
