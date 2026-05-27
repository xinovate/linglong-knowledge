# 文档同步

## 何时更新文档

| 代码改动 | 必须更新 |
|---------|---------|
| 新增/删除/修改 MCP 工具 | `docs/api.md` + `PROJECT_OVERVIEW.md` 测试计数 |
| 新增/修改配置字段 | `docs/api.md` + `.linglong.yaml` |
| ingest 数据源变化 | `docs/ingest/README.md` + `docs/roadmap.md` |
| 版本级改动 | `PROJECT_OVERVIEW.md` 版本表 + Next Actions + `docs/roadmap.md` |
| 架构决策变更 | `docs/architecture.md` + `docs/roadmap.md` ADR |
| 测试数量变化 | `PROJECT_OVERVIEW.md` 测试覆盖表 |
| 安全/运维相关 | `docs/operations.md` |

## 准确性规则

- `PROJECT_OVERVIEW.md` 测试计数必须与 `grep -r "def test_" tests/ | wc -l` 一致，验证不估算
- 按模块计数必须准确，测试增减后重新计数
- `docs/api.md` 文档中的配置字段必须与 `src/linglong/core/config.py` 一致，删除已不存在的字段
- MCP 工具表必须列出所有已注册工具，与 `server.py` 中 `_TOOL_GROUPS` 交叉验证
- Entity 模型示例必须与 `models.py` 一致（字段名、类型、默认值）
- 架构描述必须反映代码实际行为，未实现功能用 `// 计划中` 标注

## doc-check Hook

- `scripts/doc-check.py` 在 `git commit` 时自动运行
- 检查过时引用和缺失的文档更新
- 禁止忽略 `⚠️ doc-check` 提醒直接提交，必须修复后再提交

## 架构图要求

`docs/architecture.md` 应包含：
- 模块依赖图（哪个模块导入哪个）
- 数据流图：ingest → knowledge → 博客项目（评审+发布）
- MCP 路由图：远程（ingest）vs 本地（knowledge）
- 部署架构：Cloudflare Tunnel → MCP Server → SearXNG/RSS/LLM

图用 Mermaid 代码块或 ASCII art，必须与代码保持同步。

## CLAUDE.md 定位

`CLAUDE.md` 是入口路由文件，控制在 150 行以内。详细规则在 `.claude/rules/` 中。

## 文档写作规范

- 文档语言：项目文档（`docs/`、`PROJECT_OVERVIEW.md`）中文为主，技术术语保留英文
- 每个文档文件开头有简短的一句话说明文档用途
- 表格优先于列表展示结构化信息（配置字段、工具列表、版本历史）
- 代码示例可运行、可复制，不写伪代码
- 文档中的路径使用项目相对路径（`src/linglong/...`），不用绝对路径
