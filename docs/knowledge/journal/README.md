# 工作日志

> **定位**：按天记录工作过程中的问题调查、决策和发现。
> **不记录**：阶段方向（去 `docs/PROJECT_OVERVIEW.md`）、设计决策（去 `docs/knowledge/design/00-overview.md`）。
> **结构**：概览 → 问题/任务 → 结论 → 关联链接。
> **更新时机**：当天工作结束或会话压缩前。

| 日期 | 主题 | 关键结论 |
|------|------|----------|
| 2026-05-21 | lint 增强 + OpenClaw 接入 + 搜索增强 | lint 5 项补齐；OpenClaw Phase 0+2 完成，MCP 全链路通过；RRF 混合搜索 + 自动模式实现；SyncAdapter 移除 memory 模式 |
| 2026-05-20 | MCP Server + 模板体系 | 9 个 MCP 工具上线；search_and_read 截断控制；模板体系 9 facet |
| 2026-05-18 | 知识库同步质量检查 | entity facet 缺失是正常状态；发现 614 个 lint 问题 |

---

## 长期待办

> 从 `tracking/` 迁移。已完成项归档在各日日志。

| 编号 | 标题 | 分类 | 优先级 | 状态 |
|------|------|------|--------|------|
| BACKLOG-002 | OpenClaw 默认 wiki 路径支持 | 多用户适配 | 中 | 待实现 |
| BACKLOG-003 | 索引文件自动生成（index --rebuild 结构不完整） | 存储层 | 中 | 待实现 |
| LIMIT-001 | OpenClaw frontmatter 解析失败（2 个文件） | 数据质量 | 低 | 观察中 |
