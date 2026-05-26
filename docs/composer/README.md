# Composer — 内容生产模块

## 职责

从知识库读取已沉淀的知识 → 聚合 → 提炼 → 套模板 → 输出成品。

## 设计原则

**composer 只从知识库读取已沉淀的知识。** 知识库中的内容都经过人和 Agent 讨论筛选，不存在原始 ingest 数据。composer 不关心知识的来源，只消费知识库中的确认内容。

**输出追踪**：发布后通过 `output_log` 表记录哪些 entity 已被输出到哪个平台，避免重复消费。

## 流水线流程

```mermaid
graph TD
    A[KnowledgeStore<br/>已沉淀的知识] -->|search| B[KnowledgeAdapter]
    B --> C[ComposerState<br/>去重 + output_log 检查]
    C --> D{distiller_use_llm?}
    D -->|是| E[LLMDistiller<br/>LLM 智能提炼]
    D -->|否| F[DailyAggregator<br/>规则聚合]
    E --> G[BlogTemplate<br/>套用模板]
    F --> G
    G --> H{image_assets.enabled?}
    H -->|是| I[ImageAssetSelector → PageImageResolver → ImageAssetFetcher]
    H -->|否| J{auto_publish?}
    I --> J
    J -->|是| K[DispatchManager.publish]
    J -->|否| L[返回 ComposerResult]
    K --> M[写 output_log]
    M --> L
```

## 组件列表

| 组件 | 路径 | 说明 |
|------|------|------|
| `Composer` | `composer/composer.py` | 编排器 |
| `QualityLint` | `composer/lint.py` | 质量校验（规则层 + LLM 层） |
| `OutputLog` | `composer/output_log.py` | 溯源记录（JSONL 审计日志） |
| `DraftManager` | `composer/draft.py` | 草稿生命周期管理 |
| `ComposerState` | `composer/state.py` | 内容哈希去重与状态持久化 |
| `IngestAdapter` | `composer/ingest_adapter.py` | Entity → MemoryFragment 适配层 |
| `DailyAggregator` | `composer/distiller/aggregator.py` | 按天聚合记忆片段 |
| `LLMDistiller` | `composer/distiller/llm_distiller.py` | LLM 智能提炼与主题合并 |
| `BlogTemplate` | `composer/templates/blog.py` | Hexo 博客模板 |
| `TextAssetGenerator` | `composer/assets/text.py` | 摘要、标签、引言生成 |
| `ImageAssetFetcher` | `composer/assets/image_asset_fetcher.py` | 图片下载/压缩/EXIF 清理 |
| `ImageAssetSelector` | `composer/assets/image_asset_selector.py` | URL 文件解析 + 随机选择 + 去重 |
| `PageImageResolver` | `composer/assets/page_image_resolver.py` | Playwright 页面 → 图片 URL |

## 使用方式

```bash
# CLI
linglong compose              # 正常运行
linglong compose --dry-run    # 试运行（不保存）
linglong compose --draft      # 草稿模式（保存待审核）
```

```python
# Python
from linglong.composer.composer import Composer

composer = Composer()
result = composer.run(dry_run=False, draft=False)
# result.success, result.articles, result.errors
```

## 配置

```yaml
# .linglong.yaml
composer:
  llm_provider: openai
  llm_model: gpt-4
  distiller_use_llm: false
  auto_publish: false
  default_publisher: hexo
  drafts_dir: ~/linglong/data/drafts
  image_assets:
    enabled: true
    sources:
      - name: tuchong
        url_file: ~/Downloads/resource.txt
        resolve_via: playwright
```

## 相关文档

- [图片资产系统](image-assets.md)
- [模板引擎](templates.md)
- [设计文档](design/00-overview.md) — 架构图、子设计索引、全局设计决策
