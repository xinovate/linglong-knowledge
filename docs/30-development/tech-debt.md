# 技术债务登记册

> 本文件记录 linglong 项目中已知的技术债务，按严重程度排序。
> 更新日期: 2026-05-12
> 责任人: 项目 Owner（王鑫）及所有贡献者

---

## 债务清单

### DEBT-001: `BlogTemplate.MAX_TITLE_LENGTH = 50` 与下游博客规范冲突

- **严重程度**: 高
- **影响范围**: `src/linglong/composer/templates/blog.py`
- **问题描述**:
  下游博客项目 `hexo-blog` 要求标题 10–18 个汉字，但 `BlogTemplate` 的验证阈值曾设为 50 字符，导致生成的标题过长。
- **当前状态**: 已在 v0.2 修复，`MAX_TITLE_LENGTH` 改为 18，Prompt 中已要求 10–18 字。
- **相关文件**:
  - `src/linglong/composer/templates/blog.py`
  - `src/linglong/composer/distiller/llm_distiller.py`（Prompt 模板）

### 已解决

- **解决时间**: 2026-05-11
- **解决方式**: 将 `MAX_TITLE_LENGTH` 从 `50` 改为 `18`，与下游博客规范对齐。

---

### DEBT-002: `---` 分隔符与 Markdown frontmatter 冲突

- **严重程度**: 高
- **影响范围**: `src/linglong/composer/distiller/aggregator.py` 中的 `ArticleMaterial.compile_content()`
- **问题描述**:
  `ArticleMaterial.compile_content()` 曾使用 `\n---\n` 拼接多个记忆片段，与 Markdown 的 frontmatter 结束标记冲突。
- **当前状态**: 已修复。
- **相关文件**:
  - `src/linglong/composer/distiller/aggregator.py`

### 已解决

- **解决时间**: 2026-05-11
- **解决方式**: 将片段拼接分隔符改为 `\n\n----\n\n`（四横线），避免与 Markdown frontmatter 的 `---` 结束符冲突。

---

### DEBT-003: frontmatter 不支持复杂 YAML 列表（历史遗留，部分已修复）

- **严重程度**: 中
- **影响范围**: `src/linglong/composer/templates/blog.py` 中的 `_build_frontmatter()`
- **问题描述**:
  早期 `_build_frontmatter()` 只输出简单 `key: value`，导致 `tags` 和 `categories` 的 YAML list 格式不正确。当前代码已改用 `yaml.dump()` 生成 frontmatter，但需确认所有模板和下游消费方兼容。
- **当前状态**: 代码已修复，但未经过完整回归测试。
- **计划缓解**:
  1. **短期（v0.2）**: 在 `tests/` 中补充 frontmatter 解析测试，验证 `yaml.safe_load()` 能正确还原 `tags` 和 `categories` 列表。
  2. **中期（v0.2.x）**: 在 `BlogTemplate.validate()` 中增加 frontmatter YAML 结构校验。
- **相关文件**:
  - `src/linglong/composer/templates/blog.py`

---

### DEBT-004: 临时目录硬编码

- **严重程度**: 中
- **影响范围**: 历史实现中 `assets_output_dir` 硬编码为 `/tmp/linglong/assets`
- **问题描述**:
  旧 pipeline 中 `assets_output_dir` 的默认值硬编码为 `/tmp/linglong/assets`，在 Windows 或受限权限环境下会失败。
- **当前状态**: 迁移到 linglong 后，所有路径统一由 `core/config.py` 中的 `LinglongConfig` 管理，已消除硬编码。
- **相关文件**:
  - `src/linglong/core/config.py`

### 已解决

- **解决时间**: 2026-05-12
- **解决方式**: 迁移到 linglong 统一配置体系，路径由 `LinglongConfig` 驱动。

---

### DEBT-005: 缺少 lint / format 工具 ✅ 已解决

- **解决时间**: 2026-05-12
- **解决方式**: `pyproject.toml` 已配置 ruff、black、mypy，CI workflow 运行 `make check`。

---

### DEBT-006: `tests/` 目录覆盖率不足 ✅ 已解决

- **解决时间**: 2026-05-12
- **解决方式**: 所有模块均有测试覆盖（core/knowledge/composer/dispatch/ingest/integration），75+ 测试通过。

---

### DEBT-007: `OpenClawSource` 按 mtime 去重不可靠（已修复，需验证长期稳定性）

- **严重程度**: 低
- **影响范围**: 历史实现 `src/linglong_pipeline/sources/openclaw.py`
- **问题描述**:
  早期 `OpenClawSource` 使用文件 `mtime` 判断记忆是否已处理，Git 克隆或 `touch` 后会导致全部重新处理。
- **当前状态**: 迁移后 composer 不再直接读取文件系统，改为从 `KnowledgeStore` 读取 `Entity`。去重逻辑在 `ComposerState` 中通过内容哈希实现。
- **计划缓解**:
  1. **短期（v0.2）**: 观察内容哈希在长期使用中的稳定性，确认无哈希碰撞导致的漏处理。
  2. **中期（v0.2.x）**: 若记忆量增大，考虑将哈希算法从 `md5` 升级为 `sha256`，或引入布隆过滤器加速查询。
- **相关文件**:
  - `src/linglong/composer/state.py`

---

### DEBT-008: 封面图生成与下游博客项目冲突 ✅ 已解决

- **解决时间**: 2026-05-13
- **解决方式**: 图片资产管线已实现（ImageAssetFetcher/Selector/PageImageResolver），支持 background 和 article_image 两种用途，通过 `.linglong.yaml` 配置。原 `image.py` 已替换为实际实现。

---

### DEBT-009: LLM Prompt 硬编码在 Python 文件中 ✅ 已解决

- **解决时间**: 2026-05-12
- **解决方式**: Prompt 已外部化至 `assets/prompts/blog/*.md`，`llm_distiller.py` 通过 `_load_prompt()` 运行时读取。

---

### DEBT-010: Composer State 使用内容哈希而非 entity_id 去重

- **严重程度**: 低
- **影响范围**: `src/linglong/composer/state.py`
- **问题描述**:
  当前 `ComposerState` 通过 `MemoryFragment.content_hash`（MD5）去重，而非跟踪 `Entity.id`。若同一 Entity 内容被修改后重新处理，可能因哈希变化而重复生成。
- **当前状态**: MVP 阶段内容哈希足够；未来实体量增大后需升级。
- **计划缓解**:
  1. **中期（v0.2.x）**: 将 state 跟踪键从 `content_hash` 升级为 `entity_id`，同时支持按版本号判断。
  2. **长期（v1.0）**: 在 `KnowledgeStore` 中增加 `processed_by_composer` 标志，状态完全由存储层维护。
- **相关文件**:
  - `src/linglong/composer/state.py`

---

## 统计概览

| 严重程度 | 数量 | 债务编号 |
|----------|------|----------|
| 高 | 0 | — |
| 中 | 1 | DEBT-003 |
| 低 | 2 | DEBT-007, DEBT-010 |
| ✅ 已解决 | 5 | DEBT-001, DEBT-002, DEBT-004, DEBT-005, DEBT-006, DEBT-008, DEBT-009 |

---

## 更新规则

1. 发现新债务时，按编号递增追加到本文件。
2. 债务缓解后，在对应条目下增加"已解决"章节，并保留历史记录。
3. 每季度（或每个 MINOR 版本发布前）回顾本文件，评估债务是否已累积到需要专门排期的程度。
