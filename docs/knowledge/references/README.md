# 调研参考

> 项目早期（2026-05-14）为验证知识库设计完备性所做的调研，设计已定型，仅供参考。

## 竞品架构

| 文件 | 来源 | 关注点 |
|------|------|--------|
| [claude-mem.md](claude-mem.md) | thedotmack/claude-mem v12.1.0 | MCP 持久记忆插件，6 组件架构，3 层渐进式披露 |
| [memgpt.md](memgpt.md) | 论文 MemGPT (arXiv:2310.08560) | OS 级记忆管理，虚拟上下文，分层存储 |

## 参考设计

| 文件 | 来源 | 关注点 |
|------|------|--------|
| [llm-wiki-reference.md](llm-wiki-reference.md) | Karpathy LLM-Wiki Gist | 四层架构、两步索引查询、lint 巡检、归档机制 |
| [llm-wiki-community.md](llm-wiki-community.md) | LLM-Wiki 评论区 35+ 评论 | 6 个社区实现：实体消解、候选暂存、权重衰减、Dream Cycle |

## 综合分析

| 文件 | 内容 |
|------|------|
| [convergence.md](convergence.md) | 全方案对比 + P2/P3 增强建议 |
| [gap-analysis.md](gap-analysis.md) | LLM-Wiki 参考设计 vs Linglong 实现的逐项差距 |
| [industry-trends.md](industry-trends.md) | 4 大范式演进：RAG → 自治记忆 → 知识图谱 → 多 Agent |
| [modern-knowledge-systems.md](modern-knowledge-systems.md) | 7 篇设计文档的完备性交叉验证 |
