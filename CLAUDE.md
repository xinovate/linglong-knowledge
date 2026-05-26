# CLAUDE.md — Linglong 项目协作指南

## 项目定位

Linglong 是**跨 Agent 知识中枢**，串联信息采集 → 讨论沉淀 → 内容生产 → 多平台分发。

```
ingest（采集，不写知识库）→ 用户阅读思考 → 知识库 → composer → dispatch
```

---

## ⚠️ 执行前检查（每次任务开始时，必须遵守）

**文档驱动开发：先更新文档，再写代码。**

1. **读 `journal/今天.md`** — 了解当日上下文、待办、已有进度
2. **判断任务影响范围** — 以下文档是否需要更新：
   - 今日日志 `journal/今天.md` — 新增任务/状态变化 → **先更新再动手**
   - 设计文档 `docs/*/design/` — 架构/接口变更 → **先更新设计再实现**
   - 路线图 `docs/roadmap.md` — 新增功能/版本规划 → **先记录再开始**
3. **代码改完后**，按下方文档同步规则补全受影响的文档

---

## 架构规则

- **ingest 不写知识库** — 采集结果返回给对话，写入由人决定
- **知识库只接受讨论沉淀** — 人和 Agent 讨论筛选后通过 MCP/CLI 写入
- **composer 只读 knowledge**，不直接读文件系统
- **composer 不处理发布**，发布逻辑在 dispatch
- **dispatch 发布后写 output_log** — 记录 entity_id + publisher + published_at

关键模型字段：`facet`（六分面）| `confidence`（AI 置信度）| `status`（审核状态）| `created_by`（`agent:claude`/`agent:openclaw`）

---

## 文档同步规则（代码改动后必须遵守）

| 改了什么 | 必须检查并更新 |
|----------|---------------|
| 新增/删除/修改 MCP 工具 | `docs/api.md` + `PROJECT_OVERVIEW.md` 测试计数 |
| 新增/修改配置字段 | `docs/api.md` + `.linglong.yaml` |
| ingest 数据源变化 | `docs/ingest/README.md` + `docs/roadmap.md` |
| 版本级改动 | `PROJECT_OVERVIEW.md` 版本表 + Next Actions + `docs/roadmap.md` |
| 架构决策变更 | `docs/architecture.md` + `docs/roadmap.md` ADR |
| 测试数量变化 | `PROJECT_OVERVIEW.md` 测试覆盖表 |
| 安全/运维相关 | `docs/operations.md` |

doc-check hook（`scripts/doc-check.py`）在 `git commit` 时自动检查。禁止忽略 `⚠️ doc-check` 提醒直接提交。

---

## 代码规范

- 导入：标准库 → 第三方库 → 本项目模块
- 公共函数必须标注类型注解
- 外部依赖调用 try/except，单组失败不阻断整批
- `logging.getLogger(__name__)`，禁止 `print`
- 默认不写注释，WHY 不显而易见时写一行

## 测试

```bash
.venv/bin/pytest           # 全部
.venv/bin/pytest tests/ingest/ -v  # 指定模块
```

禁止自动化测试调用真实外部服务。

---

## 每日工作

- 日志在 `journal/YYYY-MM-DD.md`：开始前读上下文，完成后更新记录
- 优先处理 `PROJECT_OVERVIEW.md` Next Actions
- 参考文档：[项目总览](docs/PROJECT_OVERVIEW.md) | [架构](docs/architecture.md) | [路线图](docs/roadmap.md) | [API](docs/api.md) | [运维](docs/operations.md)
