# 代码风格

基线：PEP 8。以下为项目特化规则。

## 注释

- **语言**：统一英文，禁止中文注释
- **策略**：默认不写注释，只在 WHY 不显而易见时写一行
- **不写什么**：代码做了什么（标识符自解释）
- **写什么**：隐藏约束、微妙不变量、特定 bug 的 workaround、会令读者意外的行为
- **禁止 TODO/FIXME**：用 issue 或 journal 记录

## 命名

- 函数、方法、变量：`snake_case`
- 类：`PascalCase`
- 常量：`UPPER_SNAKE_CASE`
- 模块级私有辅助函数：`_` 前缀
- 布尔变量/函数：使用 `is_`、`has_`、`should_` 前缀

## 类型注解

- 所有公共函数和方法必须标注参数类型和返回类型
- `__init__` 必须标注 `-> None`
- 使用现代联合语法：`str | None`，不用 `Optional[str]`
- 复杂类型表达式的文件顶部加 `from __future__ import annotations`

## 导入

- 顺序：标准库 → 第三方库 → 本项目模块（`linglong.*`）
- 每组之间空一行
- 禁止通配符导入（`from module import *`）
- 日志统一用 `logging.getLogger(__name__)`，禁止 `print()`（`cli.py` 豁免）

## 错误处理

按语义分层，让调用方能区分不同失败模式：

| 异常类型 | 使用场景 |
|---------|---------|
| `ValueError` | 调用方传入无效参数 |
| `LookupError` | 实体/资源未找到 |
| `RuntimeError` | 外部服务故障（LLM、SearXNG、RSS） |
| `Exception` | 批处理兜底（需 `noqa: BLE001`） |

- MCP 工具函数：捕获领域异常，返回结构化错误 JSON，不让原始异常泄露给客户端
- 外部依赖（网络调用、文件 I/O）：必须 try/except，单个来源失败不能中断整批

## 同步/异步边界

- IO 密集操作（HTTP 调用、embedding 生成）：用 `async` + `httpx.AsyncClient`
- CPU 密集或 SQLite 操作：用同步代码
- 同一层次不要混用 `requests`（同步）和 `httpx`（异步）
- `EmbeddingGenerator` 应从同步 `requests` 迁移到异步 `httpx`

## SQL

- 所有用户输入必须用参数化查询（`?` 占位符），禁止拼接用户数据到 SQL
- 动态 WHERE 子句：只从硬编码列名构建，不用用户输入
- PRAGMA 用 f-string 可接受（值来自已验证的配置）

## 文件长度

- 目标：单文件 300 行以内
- 超过 400 行时考虑按职责拆分
- 函数只做一件事。如果需要注释分隔段落，说明应该拆成独立函数
