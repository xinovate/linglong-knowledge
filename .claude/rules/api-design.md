# API 与 MCP 工具设计

## MCP 工具注册

- 工具按模块组织：`ingest`、`knowledge`（reviewer / dispatch 暂不维护）
- 每个模块独立 FastMCP 实例，专属 HTTP 路径（`/mcp/<模块>`）
- 远程部署仅暴露 `ingest`，本地 stdio 暴露全部模块
- 工具函数名必须描述性强、动词开头：`generate_brief`、`search_web`、`add_entity`

## 工具函数模板

```python
@mcp_tool
async def tool_name(param: str) -> dict:
    """一句话描述工具功能。"""
    try:
        # 领域逻辑
        return {"status": "ok", ...}
    except ValueError as exc:
        return {"error": f"Invalid input: {exc}"}
    except LookupError as exc:
        return {"error": f"Not found: {exc}"}
    except Exception as exc:
        logger.exception("tool_name failed")
        return {"error": str(exc)}
```

- 返回类型：`dict`（JSON 可序列化）
- 显式捕获领域异常，`Exception` 仅作兜底并配合 `logger.exception()`
- 禁止向客户端暴露内部堆栈

## 错误响应格式

```json
{"error": "人类可读的错误信息"}
```

不自创错误码，HTTP 状态码 + 错误信息足够。

## 配置字段

- Python 中用 `snake_case`，YAML 中用 `snake_case`
- 环境变量覆盖：`LL_<节>_<字段>`（如 `LL_MCP_AUTH_TOKEN`）
- 新增配置字段必须同步到 `docs/api.md` 配置节
- 配置字段和环境变量不重复 — 只用一种机制

## 新增工具 Checklist

1. 在 `src/linglong/<模块>/` 实现工具函数
2. 在 `src/linglong/mcp/server.py` 的 `_TOOL_GROUPS` 中注册
3. 编写单元测试：正常路径 + 至少一个错误路径
4. 更新 `docs/api.md` MCP 工具表（名称、描述、参数、返回格式）
5. 更新 `PROJECT_OVERVIEW.md` 测试计数
6. 确认 `doc-check.py` 通过
