# 测试策略

## 测试分层

```mermaid
graph TD
    A[单元测试<br/>纯逻辑，无外部依赖] --> B[集成测试<br/>跨模块协作，Mock 外部]
    B --> C[端到端测试<br/>CLI 真实环境]
```

### 单元测试

不依赖外部服务、不读写真实文件系统的纯逻辑测试。

| 模块 | 测试要点 |
|------|----------|
| `core.config` | LinglongConfig 加载、默认值、YAML 配置 |
| `core.models` | Entity 构造、AgentID 验证、ConfidenceScore 边界 |
| `composer.state` | 内容哈希计算、去重逻辑、状态流转 |
| `composer.draft` | DraftManager 保存/列出/发布/废弃 |
| `composer.distiller` | KnowledgeAdapter、DailyAggregator、ArticleMaterial |

### 集成测试

跨模块协作，使用 Mock 替代外部依赖。

- **KnowledgeStore + Entity**: 写入 → search 按 status 过滤
- **Composer 编排**: 注入 fixture → 验证完整调用链
- **Draft 生命周期**: draft=True → 读取 → 发布 → 废弃

### 端到端测试

手动执行，验证 CLI 主流程。

- `Composer.run(dry_run=True)` — 不触发发布
- `Composer.run(draft=True)` — 草稿保存到独立目录
- 真实 KnowledgeStore — 验证输出格式

## Mock 原则

| 依赖 | Mock 方式 |
|------|----------|
| 文件系统 | `tempfile.TemporaryDirectory()` + `set_config()` |
| LLM API | `unittest.mock.patch` 替换 `LLMClient.call()` |
| 网络 | `responses` 或 `httpx.MockTransport` |

## 测试纪律

1. **新增功能必带测试**
2. **Mock 外部依赖** — 禁止调用真实 LLM API / 真实文件系统
3. **状态隔离** — 使用临时目录，避免污染 `~/.linglong/`
4. **配置隔离** — `set_config()` 注入临时 LinglongConfig

## 运行

```bash
pytest                          # 全部测试
pytest tests/core/ -v           # core 模块
pytest tests/composer/ -v       # composer 模块
pytest --cov=linglong           # 带覆盖率
```

## 目录结构

```
tests/
├── core/           # core 模块测试
├── ingest/         # ingest 模块测试
├── knowledge/      # knowledge 模块测试
├── composer/       # composer 模块测试
├── dispatch/       # dispatch 模块测试
└── integration/    # 端到端集成测试
```
