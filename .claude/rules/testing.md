# 测试约定

## 框架与运行

- 框架：`pytest`
- 全量：`.venv/bin/pytest`
- 指定模块：`.venv/bin/pytest tests/ingest/ -v`
- 单个测试：`.venv/bin/pytest tests/knowledge/test_store.py::test_add_entity -v`

## 文件与命名

- 测试文件：`tests/<模块>/test_<组件>.py`
- 测试函数：`def test_<行为描述>()` — 描述预期行为，不描述实现
- 组件测试用例多时，用 class 分组

## 覆盖要求

- **每个公共方法**至少一个测试
- **关键路径**（MCP 工具依赖）必须有多个测试覆盖正常 + 边界：
  - `KnowledgeStore.search_auto()`、`search_hybrid()`
  - `KnowledgeStore.sync()`、`rebuild_embeddings()`
  - `Reviewer.review()` — 当前 9 个测试，需扩展
  - `IngestAgent.generate_brief()` — 必测 LLM 失败、空结果、部分数据
- 只有抽象基类可以无直接测试，其他都必须覆盖

## Mock 规则

- **禁止调用真实外部服务**：不联网 SearXNG、LLM API、RSS、GitHub
- 在 HTTP 层（`httpx`/`requests`）或适配器边界 mock
- 不 mock 内部模块。如果需要 mock 内部函数，说明测试层次可能不对
- 共享测试数据和 mock 用 `pytest.fixture`

## 测试结构

遵循 Arrange → Act → Assert：

```python
def test_search_returns_matching_entities(store_with_data):
    # Arrange — fixture 处理
    # Act
    results = store_with_data.search_hybrid("machine learning")
    # Assert
    assert len(results) > 0
    assert all(r.confidence >= 0.5 for r in results)
```

## 不测什么

- 第三方库行为（如 "SQLite 能不能用"）
- 无逻辑的 getter/setter
- 抽象基类方法（测具体子类）

## 测试计数追踪

- 测试增减后必须更新 `PROJECT_OVERVIEW.md` 测试覆盖表
- 总数必须与 `grep -r "def test_" tests/ | wc -l` 一致
- 按模块计数必须实际验证，不估算
