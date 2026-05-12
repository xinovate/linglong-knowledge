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

### DEBT-005: 缺少 lint / format 工具

- **严重程度**: 中
- **影响范围**: 整个代码库
- **问题描述**:
  项目未配置 `ruff`、`black`、`mypy` 等工具，代码风格依赖人工约束，长期会导致风格不一致和类型安全隐患。
- **当前状态**: 无配置文件，无 CI 检查。
- **计划缓解**:
  1. **短期（v0.2）**: 引入 `ruff`（lint + format 合一）和 `mypy`，编写 `pyproject.toml` 配置段。
  2. **中期（v0.2.x）**: 在 GitHub/GitLab CI 中增加 lint 检查门禁，未通过的 PR 禁止合并。
  3. **长期（v1.0）**: 引入 `pre-commit` 钩子，本地提交前自动格式化。
- **相关文件**:
  - `pyproject.toml`（待新增配置）

---

### DEBT-006: `tests/` 目录覆盖率不足

- **严重程度**: 中
- **影响范围**: `tests/` 目录
- **问题描述**:
  旧 pipeline 项目尚未配置 pytest，无任何单元测试或集成测试。迁移到 linglong 后已补充 pipeline 模块测试，但其他模块（ingest、dispatch）仍待补充。
- **当前状态**:
  - `tests/core/` — 待补充
  - `tests/knowledge/` — 已部分覆盖
  - `tests/composer/` — 已补充 32 个测试，全部通过
- **计划缓解**:
  1. **短期（v0.2）**: 补充 `tests/core/` 和 `tests/ingest/` 单元测试。
  2. **中期（v0.2.x）**: 增加集成测试：使用 mock LLM client 跑完整 `Composer.run()`。
  3. **长期（v1.0）**: 达到核心代码 80%+ 覆盖率。
- **相关文件**:
  - `tests/`
  - `pyproject.toml`

### 已部分解决

- **解决时间**: 2026-05-12
- **解决方式**: Composer 模块已迁移并建立完整测试套件（32 个测试通过）。

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

### DEBT-008: 封面图生成与下游博客项目冲突

- **严重程度**: 低
- **影响范围**: `src/linglong/composer/assets/image.py`
- **问题描述**:
  流水线曾生成 `cover_image` frontmatter，但下游博客项目通过 `.post-covers.json` 和 `post-filter.js` 自动分配封面图，两者可能冲突。
- **当前状态**: `ImageAssetGenerator` 在迁移时未接入 linglong composer（依赖 HTTP 调用，与架构规则冲突）。MVP 中暂不生成封面图。
- **计划缓解**:
  1. **短期（v0.2）**: 统一使用 `cover_id` 机制，由博客项目分配封面，流水线只输出 `cover_id`。
  2. **中期（v0.2.x）**: 若引入 AI 生成封面图，则作为独立渠道（不写入 Hexo frontmatter，而是输出到图床）。
- **相关文件**:
  - `src/linglong/composer/assets/image.py`（预留）
  - `config/pipeline.yaml`

---

### DEBT-009: LLM Prompt 硬编码在 Python 文件中

- **严重程度**: 低
- **影响范围**: `src/linglong/composer/distiller/llm_distiller.py`
- **问题描述**:
  `SYSTEM_PROMPT` 和 `USER_PROMPT_TEMPLATE` 硬编码在 Python 源码中，修改 Prompt 需要改代码并重新部署，不便于非开发者调优。
- **当前状态**: Prompt 已直接写入 `llm_distiller.py`。
- **计划缓解**:
  1. **短期（v0.2）**: 将 Prompt 提取到 `assets/prompts/` 目录下的 `.md` 文件中，`llm_distiller.py` 运行时从文件读取。
  2. **中期（v0.2.x）**: 支持按主题/场景切换不同 Prompt 模板。
- **相关文件**:
  - `src/linglong/composer/distiller/llm_distiller.py`
  - `assets/prompts/`（待创建）

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
| 中 | 3 | DEBT-003, DEBT-005, DEBT-006 |
| 低 | 4 | DEBT-007, DEBT-008, DEBT-009, DEBT-010 |

---

## 更新规则

1. 发现新债务时，按编号递增追加到本文件。
2. 债务缓解后，在对应条目下增加"已解决"章节，并保留历史记录。
3. 每季度（或每个 MINOR 版本发布前）回顾本文件，评估债务是否已累积到需要专门排期的程度。
