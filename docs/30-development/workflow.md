# 开发工作流与协作规范

> 适用范围: linglong 项目所有贡献者（含人类开发者与 AI Agent）
> 更新日期: 2026-05-12

---

## 1. Git 分支模型

### 1.1 分支定义

| 分支 | 用途 | 保护规则 |
|------|------|----------|
| `main` | 稳定版本，始终可运行 | 禁止直接推送，需 PR/MR 合并 |
| `feature/*` | 新功能开发 | 从 `main` 切出，合并回 `main` 后删除 |
| `fix/*` | 缺陷修复 | 从 `main` 切出，合并回 `main` 后删除 |
| `docs/*` | 文档更新 | 从 `main` 切出，合并回 `main` 后删除 |

### 1.2 工作流步骤

1. **创建功能分支**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/llm-distiller
   ```

2. **开发与提交**
   - 遵循"小步快跑"原则，每次提交只做一个逻辑变更。
   - 提交前确保对应模块的测试通过。

3. **合并回 main**
   - 通过 Pull Request / Merge Request 合并。
   - 合并前至少经过一次代码审查（人类或 AI Agent 均可）。
   - 合并后删除功能分支：
     ```bash
     git branch -d feature/llm-distiller
     git push origin --delete feature/llm-distiller
     ```

### 1.3 紧急修复

若 `main` 出现严重缺陷：

1. 从 `main` 切出 `fix/critical-bug`。
2. 修复后通过快速通道合并（可跳过部分审查环节，但需在合并后 24h 内补审）。
3. 在 `docs/30-development/tech-debt.md` 中记录根因，防止复发。

---

## 2. 开发约定

### 2.1 代码风格

- **Python 版本**: 3.11+
- **命名规范**: PEP 8
  - 类名: `PascalCase`
  - 函数/变量: `snake_case`
  - 常量: `UPPER_SNAKE_CASE`
  - 私有方法: `_leading_underscore`
- **类型注解**: 所有公共函数必须标注参数类型和返回值类型。
  ```python
  def distill(self, date: str, fragments: List[MemoryFragment]) -> ArticleMaterial:
      ...
  ```
- **文档字符串**: 公共类和方法使用 Google Style docstring。
- **字符串引号**: 代码内统一使用双引号 `"`，仅在避免转义时使用单引号。

### 2.2 日志规范

- 使用 `logging.getLogger(__name__)`，禁止 `print` 输出到 stdout（CLI 展示除外）。
- 日志级别约定：
  - `DEBUG`: 详细的内部状态（如 Prompt 内容、API 响应原文）
  - `INFO`: 用户关心的里程碑（如"LLM 提炼完成: xxx"）
  - `WARNING`: 可恢复异常（如"LLM 调用失败，回退到规则模式"）
  - `ERROR`: 需要人工介入的错误（如"主题分析输出解析失败"）

### 2.3 配置管理

- 所有可调整参数必须通过 `core/config.py` 中的 Pydantic Settings 暴露，禁止在代码中硬编码业务常量。
- 例外: 真正的技术常量（如 HTTP 超时秒数、JSON 解析最大重试次数）可在代码中定义，但需注释说明。
- 环境变量前缀统一为 `LL_`，模块级配置使用 `LL_{MODULE}_` 前缀（如 `LL_COMPOSER_LLM_MODEL`）。

### 2.4 错误处理

- 对外部依赖（LLM API、文件系统、subprocess）的调用必须包裹 `try/except`，并记录详细错误信息。
- 关键路径（如 `Composer.run()`）中的单组失败不应阻断整批处理，应收集错误后继续下一组。

---

## 3. 文档驱动开发流程

所有变更必须先遵循 `docs/` 中定义的流程，再写代码。

### 3.1 变更类型与对应文档

| 变更类型 | 前置文档动作 | 关联文档 |
|---------|------------|---------|
| 需求变更 | 先更新对应版本的 roadmap | `docs/00-roadmap/` |
| 架构决策 | 先写 ADR（Architecture Decision Record） | `docs/20-architecture/adr/` |
| 开发工作 | 遵循本文档的 Git 分支策略 | `docs/30-development/workflow.md` |
| 新增测试 | 遵循测试策略，代码与测试同步提交 | `docs/40-testing/strategy.md` |
| 发版 | 遵循发版 checklist | `docs/50-operations/release-process.md` |
| 技术债务 | 同步更新债务清单 | `docs/30-development/tech-debt.md` |

### 3.2 文档维护原则

- **同步更新**：修改代码时同步更新对应文档，不允许 "TODO" 或 "待补充" 占位。
- **ADR 不可变**：已接受的 ADR 不可修改，只能废弃后新建。
- **单一真相源**：项目全貌以 `docs/PROJECT_OVERVIEW.md` 为准，进入项目时优先阅读。

---

## 4. 提交信息风格

### 4.1 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 4.2 Type 定义

| Type | 含义 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(distiller): 接入 LLM 智能提炼` |
| `fix` | 缺陷修复 | `fix(composer): 状态隔离 bug` |
| `docs` | 文档更新 | `docs(adr): 增加跨天主题合并决策记录` |
| `refactor` | 重构（无行为变更） | `refactor(template): 提取 frontmatter 构建逻辑` |
| `test` | 测试相关 | `test(distiller): 增加 LLMDistiller 回退路径测试` |
| `chore` | 构建/工具链 | `chore(deps): 增加 watchdog 依赖` |

### 4.3 Scope 定义

常用 scope 与代码目录对应：

- `core`: `src/linglong/core/`
- `ingest`: `src/linglong/ingest/`
- `knowledge`: `src/linglong/knowledge/`
- `composer`: `src/linglong/composer/`
- `dispatch`: `src/linglong/dispatch/`
- `distiller`: `src/linglong/composer/distiller/`
- `template`: `src/linglong/composer/templates/`
- `assets`: `src/linglong/composer/assets/`
- `cli`: CLI 入口
- `config`: `src/linglong/core/config.py`
- `docs`: `docs/` 目录

### 4.4 示例

```
feat(distiller): 实现跨天主题合并的 LLM 分组

- 在 LLMDistiller 中增加 group_by_theme() 方法
- 支持按技术主题自动识别跨天记忆
- 失败时优雅回退到 DailyAggregator

Closes #12
```

---

## 5. AI Agent 协作规范

### 5.1 职责边界

各 Agent 不得越界修改对方主责代码：

- **Claude Code (本仓库主 Agent)**: 负责骨架、流水线编排、核心逻辑。
- **Hermes**: 负责素材采集组件，通过 `ingest` 模块扩展，不修改 Composer 核心。
- **博客 Claude Code**: 负责下游博客规范对接，不修改 `src/linglong/composer/` 业务代码。
- **OpenClaw (violet)**: 负责上游知识生产，不直接参与 Composer 代码。

### 5.2 信息同步

1. **代码同步**: 通过 Git 提交同步，每个 Agent 独立 commit，commit message 需标明 Agent 身份（如 `Co-Authored-By: Hermes <...>`）。
2. **规范同步**: 修改 `core/config.py` 或 `docs/` 目录后，需在 PR 描述中 `@` 相关 Agent。
3. **陷阱同步**: 发现新的技术债务或已知陷阱时，同步更新 `CLAUDE.md` 和 `docs/30-development/tech-debt.md`。

### 5.3 代码审查

- AI Agent 提交的代码需经过至少一次其他 Agent 或人类 Owner 的审查。
- 审查重点：
  - 是否违反模块边界（core / ingest / knowledge / composer / dispatch）
  - 是否引入新的硬编码路径或魔法数字
  - 是否更新对应的文档和配置示例

---

## 5. 发布流程

### 6.1 版本号规则

采用语义化版本 `MAJOR.MINOR.PATCH`：

- `MAJOR`: 架构级不兼容变更（如替换 Publisher 抽象基类）
- `MINOR`: 功能新增（如新增 Source 类型、新增 LLM 提供商）
- `PATCH`: 缺陷修复和文档更新

### 6.2 发布检查清单

- [ ] `main` 分支的全部测试通过
- [ ] `docs/` 中与本次变更相关的文档已更新
- [ ] `CHANGELOG.md`（若存在）已记录变更
- [ ] Git tag 已打：`git tag v0.2.0`
- [ ] Tag 已推送：`git push origin v0.2.0`

---

**更新规则**: 本文档随项目演进更新，新增约定时同步修订。
