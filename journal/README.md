# 工作日志

> **定位**：按天记录工作过程中的问题调查、决策和发现。
> **不记录**：阶段方向（去 `docs/PROJECT_OVERVIEW.md`）、设计决策（去 `docs/knowledge/design/00-overview.md`）。
> **结构**：概览 → 问题/任务 → 结论 → 关联链接。
> **更新时机**：当天工作结束或会话压缩前。

| 日期 | 主题 | 关键结论 |
|------|------|----------|
| 2026-05-22 | facet 重分类 + DB先行写入 + embedding守卫 + kb sync | BACKLOG-005 完成；create/update DB先行；content hash守卫；kb sync 双向校验 |
| 2026-05-21 | lint 增强 + OpenClaw 接入 + 搜索增强 + 文档审计 + v1.0 验证 + CLI 重构 | lint 5 项补齐；OpenClaw MCP 全链路通过；RRF 混合搜索；tracking 合并；设计文档审计对齐；v1.0 端到端验证通过；CLI kb/pipeline 分组重构 |
| 2026-05-20 | MCP Server + 模板体系 | 9 个 MCP 工具上线；search_and_read 截断控制；模板体系 8 facet；文件名 slug-ID 后缀调整；双层同步去重 |
| 2026-05-19 | 同步去重策略 | BACKLOG-001 双层去重实现（ID 去重 + Content Hash 去重） |
| 2026-05-18 | 知识库同步质量检查 | entity facet 缺失是正常状态；发现 614 个 lint 问题；清理 Sleep 日志 75 条；343 个死链修复；34 个孤立文件清理 |
| 2026-05-16 | 存储层优化 + 同步增强 | 语义文件名；OpenClaw 15 种类型映射补全；管线数据流修复 |
| 2026-05-15 | 知识库功能增强 + OpenClaw 映射 | 日期过滤、facet 过滤、JSON 输出；ReviewEngine 差异化规则；datetime 弃用 API 全局修复 |
| 2026-05-14 | 知识库核心开发（28 提交） | 7 facet 分类、FTS5 搜索、版本管理、归档、索引生成、巡检、CLI 命令集、文件锁+WAL；M1–M3 完成 |
| 2026-05-13 | 图片资产管线 + 文档整理 | 图片下载/压缩/EXIF/Playwright；OSS CDN 上传；文档按模块重组 |
| 2026-05-12 | 项目启动（42 提交） | v0.2–v0.9 全部完成；五模块骨架；三 Agent 同步适配器；向量搜索；全链路集成测试 |

---

## 长期待办

> 从 `tracking/` 迁移。已完成项归档在各日日志。

| 编号 | 标题 | 分类 | 优先级 | 状态 |
|------|------|------|--------|------|
| BACKLOG-002 | OpenClaw 默认 wiki 路径支持 | 多用户适配 | 中 | 待实现 |
| BACKLOG-003 | 索引文件自动生成（index --rebuild 结构不完整） | 存储层 | 中 | 待实现 |
| BACKLOG-005 | source facet 批量重分类（94/142 条全在 source，需 LLM 辅助细分到 concept/experience/synthesis） | 数据质量 | 高 | 待审核 |
| LIMIT-001 | OpenClaw frontmatter 解析失败（2 个文件） | 数据质量 | 低 | ✅ 已修复 |
