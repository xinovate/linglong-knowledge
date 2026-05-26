# CLAUDE.md — Linglong 项目协作指南

> 本文件面向 Claude Code（及其他 AI 助手），说明项目背景、架构决策和协作规范。

---

## 项目定位

Linglong 是一个**跨 Agent 知识中枢**。OpenClaw、Claude Code、Codex 等各自维护独立知识库，互不相通。Linglong 作为统一知识底座，串联信息采集 → 讨论沉淀 → 内容生产 → 多平台分发的完整闭环。

```
OpenClaw ──┐
Claude Code ┼──→ Linglong Knowledge Store ←── ingest (多源采集)
Codex ──────┘         ↓
                  composer (知识编译)
                       ↓
                  dispatch (智能分发)
```

---

## 架构决策（必须遵守）

### 模块边界

```
ingest（工具，不写知识库）→ 返回数据给对话
knowledge（已沉淀的知识）→ composer → dispatch
                                  ↓
                            output_log（已输出追踪）
```

- **ingest 是信息采集助手**：采集结果交给用户阅读思考，不写知识库
- **知识库只接受讨论沉淀后的写入**：人和 Agent 讨论筛选后通过 MCP/CLI 写入
- **composer 只从 knowledge 读取**，不直接读文件系统
- **composer 不处理发布**，发布逻辑在 dispatch
- **dispatch 发布后写 output_log**：记录 entity_id + publisher + published_at

### 数据模型

所有模块共享 `core/models.py` 中的模型。关键字段：

- `facet` — 六分面（concept/experience/methodology/project/reference/personal）
- `group` — 子目录分组（可选）
- `created_by` — 创建者（`agent:claude`、`agent:openclaw`；不再有 `agent:ingest`）
- `confidence` — AI 置信度 | `status` — 审核状态

### 存储抽象

KnowledgeStore 统一接口：`create` / `get` / `search` / `search_similar` / `search_auto` / `update`（乐观锁） / `archive`。详见 `docs/api.md`。

### 配置管理

主配置文件 `.linglong.yaml`（搜索路径：CWD → home），也支持环境变量（前缀 `LL_`）。

---

## 文档同步规则（每次代码改动必须遵守）

**核心原则**：这个项目是文档驱动的。代码改了，对应文档必须同步更新。

### 按改动类型的文档检查清单

| 改了什么 | 必须检查并更新 |
|----------|---------------|
| 新增/删除/修改 MCP 工具 | `docs/api.md` 工具清单 + `PROJECT_OVERVIEW.md` 测试计数 |
| 新增/修改配置字段 | `docs/api.md` 配置 API + `.linglong.yaml` 示例 |
| ingest 数据源变化 | `docs/ingest/README.md` 数据源表 + `docs/roadmap.md` |
| 版本级改动（新功能/重构/修复） | `PROJECT_OVERVIEW.md` 版本表 + Next Actions + 近5次提交 + `docs/roadmap.md` |
| 架构决策变更 | `docs/architecture.md` + `docs/roadmap.md` ADR 新增 |
| 测试数量变化 | `PROJECT_OVERVIEW.md` 测试覆盖表总计行 |
| 安全/运维相关 | `docs/operations.md` |

### 自动检查

项目配置了 PreToolUse hook（`.claude/settings.json`），`git commit` 前自动检查：
- 映射配置：`docs/doc-map.yaml`（代码路径 → 文档路径）
- 检查脚本：`scripts/doc-check.py --claude-hook`
- 提交时如果出现 `⚠️ doc-check` 提醒，必须检查对应文档后再提交

### 提交流程

1. 代码改动 + 对应文档一起 stage
2. commit 时 doc-check hook 自动运行
3. 如有 `⚠️ doc-check` 提醒 → 补充文档 → 重新 commit
4. **禁止忽略 doc-check 提醒直接提交**（除非是纯测试调整或 typo 修复）

---

## 代码规范

### 导入顺序

```python
# 1. 标准库 → 2. 第三方库 → 3. 本项目模块
```

### 类型注解 + 错误处理

- 所有公共函数必须标注参数和返回值类型
- 使用异常而非返回错误码
- 外部依赖调用必须 try/except，单组失败不阻断整批

### 日志

`logging.getLogger(__name__)`，禁止 `print`（CLI 展示除外）。

### 注释

默认不写注释。仅在 WHY 不显而易见时写一行。

---

## 测试要求

```bash
source .venv/bin/activate  # 或直接用 .venv/bin/pytest
pytest                    # 全部
pytest tests/composer/ -v # 指定模块
```

- 文件命名：`tests/{module}/test_{component}.py`
- 使用 `pytest` 框架 + fixtures 管理依赖
- 禁止在自动化测试中调用真实外部服务

---

## 你的任务

1. 阅读本文档和 `docs/` 目录（尤其是 `PROJECT_OVERVIEW.md`、`roadmap.md`）
2. 优先处理 `PROJECT_OVERVIEW.md` Next Actions 列表
3. 确保测试通过
4. **代码改动必须同步更新文档**（见上方文档同步规则）

---

## 参考文档

- [项目总览](docs/PROJECT_OVERVIEW.md) — 版本进度、测试覆盖、技术债务、Next Actions
- [架构设计](docs/architecture.md) — 模块详解、数据流、ADR
- [开发规范](docs/rules.md) — 代码风格、Git 工作流、测试规范
- [版本路线图](docs/roadmap.md) — 版本演进、已完成项、收尾项、ADR 全集
- [API 文档](docs/api.md) — 模型定义、KnowledgeStore API、MCP 工具清单
- [运维与发布](docs/operations.md) — 发布流程、服务安全、技术债务
- 模块文档：[ingest](docs/ingest/) | [knowledge](docs/knowledge/) | [composer](docs/composer/) | [dispatch](docs/dispatch/)
