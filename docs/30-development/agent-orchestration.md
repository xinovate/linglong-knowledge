# Agent 编排手册

> 适用范围: linglong 项目所有 AI Agent（含 Claude Code、Codex、OpenClaw 等）
> 更新日期: 2026-05-12

---

## 1. 角色定义

Linglong 采用四角色协作模型，每个角色有明确的职责边界：

### 1.1 Architect（架构师）

**负责会话**: 主会话（当前会话）

**职责**:
- 理解需求，制定实施计划（`writing-plans`）
- 分解任务，确定模块边界和接口变更
- Dispatch 子 Agent 执行具体实现
- 协调跨模块变更，确保一致性
- 最终合并决策

**禁止**:
- 不直接编写业务代码（除非极小的修复）
- 不跳过审查流程直接合并

### 1.2 Developer（开发者）

**负责会话**: 子 Agent（由 Architect dispatch）

**职责**:
- 按规格实现代码
- 编写测试（遵循 TDD）
- 自审：确保代码符合模块边界
- 提交到 feature 分支

**约束**:
- 只能修改指定模块的文件
- 涉及 `core/models.py` 或 `core/config.py` 的变更必须回主会话由 Architect 决策
- 必须运行 `make check` 并确保通过后再提交

### 1.3 Reviewer（审查者）

**负责会话**: 子 Agent（由 Architect dispatch）

**职责**:
- **规格审查**: 确认实现是否匹配计划（有无遗漏、有无多余）
- **代码质量审查**: 检查代码风格、模块边界、测试覆盖
- 输出审查报告，标记通过或需修改

**两阶段审查**:
1. **Spec Review**（规格审查）: 先确认功能正确性
2. **Code Quality Review**（代码质量审查）: 再确认实现质量

**规则**:
- 必须先通过规格审查，才能进入代码质量审查
- Reviewer 发现的问题必须由原 Developer 修复，修复后需重新审查
- Reviewer 不得直接修改被审查的代码

### 1.4 Tester（测试者）

**负责会话**: 子 Agent（由 Architect dispatch，或在 Developer 自测阶段）

**职责**:
- 补充边缘 case 测试
- 验证 E2E 场景
- 检查测试覆盖率

---

## 2. 何时使用子 Agent

根据全局 skills 的指导，以下场景应 dispatch 子 Agent：

| 场景 | 推荐 Skill | 说明 |
|------|-----------|------|
| 独立模块开发 | `subagent-driven-development` | 同一主会话内，按任务逐个 dispatch |
| 跨模块并行调研 | `dispatching-parallel-agents` | 多个独立问题域，同时 dispatch |
| 复杂功能实现前 | `writing-plans` | 先写计划，再执行 |
| 已有计划需执行 | `executing-plans` | 按计划逐步 dispatch |
| 独立工作空间 | `using-git-worktrees` | 并行模块开发时创建隔离 workspace |

### 2.1 不推荐使用子 Agent 的场景

- 单文件小修复（如改常量、修 typo）
- 直接编辑文档（Architect 可直接完成）
- 与当前任务强耦合的探索（需要先理解再决定）

---

## 3. Dispatch 规则

### 3.1 子 Agent Prompt 必须包含

每次 dispatch 子 Agent 时，prompt 中必须明确以下信息：

1. **任务范围**: 修改哪些文件、不修改哪些文件
2. **模块边界**: 当前模块的职责、禁止越界调用其他模块
3. **回归命令**: `make check`（必须运行并确保通过）
4. **计划上下文**: 该任务在整体计划中的位置
5. **已知约束**: 如 Python 3.11+、Pydantic v2、现有配置等

### 3.2 子 Agent 输出要求

子 Agent 完成任务后必须报告：

- **状态**: DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED
- **修改文件列表**: 完整列出变更的文件
- **测试结果**: `make check` 输出
- **审查要点**: 自审发现的问题或需要注意的地方

### 3.3 模型选择

根据子 Agent 的任务复杂度选择模型：

| 复杂度 | 示例 | 推荐模型 |
|--------|------|----------|
| 机械实现 | 独立函数、1-2 文件修改 | 快速/便宜模型 |
| 集成协调 | 多文件、跨组件调用 | 标准模型 |
| 架构设计 | 接口设计、重大重构 | 最强模型 |

---

## 4. 审查流程

### 4.1 两阶段审查

```
Developer 完成实现
        │
        ▼
┌─────────────────┐
│  Spec Reviewer  │  ← 确认：功能是否按规格实现？
│   规格审查       │     有无遗漏？有无多余？
└────────┬────────┘
         │
    ✅ 通过 │ ❌ 不通过
         │
         ▼
┌─────────────────┐
│ Quality Reviewer│  ← 确认：代码是否干净？
│   代码质量审查   │     模块边界是否遵守？
└────────┬────────┘         测试是否充分？
         │
    ✅ 通过 │ ❌ 不通过
         │
         ▼
   Architect 合并
```

### 4.2 审查检查清单

**Spec Review 检查项**:
- [ ] 所有计划中的功能点已实现
- [ ] 没有实现计划外的功能（防止 scope creep）
- [ ] 接口与计划一致
- [ ] 测试覆盖了规格中的关键路径

**Code Quality Review 检查项**:
- [ ] 代码风格符合项目规范（`make check` 通过）
- [ ] 模块边界未被破坏（不直接调用其他模块内部）
- [ ] 无硬编码、无魔法数字
- [ ] 错误处理完善（使用异常而非错误码）
- [ ] 导入顺序正确（标准库 → 第三方 → 本项目）
- [ ] 类型注解完整

---

## 5. Worktree 并行开发

### 5.1 分支命名

```
feature/{module}/<description>    # 新功能
fix/{module}/<description>        # 缺陷修复
docs/<description>                # 文档更新
```

示例: `feature/composer/frontmatter-list`、`fix/ingest/rss-timeout`

### 5.2 Worktree 工作流

当多个模块需要并行开发时，使用 `using-git-worktrees` skill 创建隔离 workspace：

```bash
# 主目录保持 main 分支干净
git worktree add ../linglong-ingest-v2 feature/ingest/v2
cd ../linglong-ingest-v2
# 独立 Claude Code 会话在此开发
```

### 5.3 合并顺序

按模块依赖链顺序合并，避免破坏中间状态：

```
core → ingest → knowledge → composer → dispatch
```

**规则**:
- 任何模块修改 `core/` 或公共接口 → 必须先回主会话更新 ADR → 通知其他模块 Agent
- 合并前必须通过 CI（`make check`）
- 合并后删除 feature 分支

### 5.4 冲突解决

若两个 worktree 修改了同一文件：
1. 由 Architect 判断冲突影响范围
2. 若涉及接口变更 → 先合并 core 侧，再通知另一模块同步
3. 若独立变更 → 按依赖顺序合并，后合并的负责解决冲突

---

## 6. 与现有流程的衔接

本手册是对 `workflow.md` 的补充，而非替代。以下职责分工：

| 内容 | 所在文档 |
|------|----------|
| Git 分支模型、提交规范 | `workflow.md` |
| 代码风格、命名约定 | `workflow.md` |
| Agent 角色、Dispatch 规则、审查流程 | `agent-orchestration.md`（本文档） |
| 技术债务登记 | `tech-debt.md` |
| 发布流程 | `release-process.md` |

---

## 7. 快速参考

### 7.1 Architect 常用命令

```bash
# 创建任务跟踪
TaskCreate subject="..." description="..."

# 标记任务状态
TaskUpdate taskId="..." status="in_progress"
TaskUpdate taskId="..." status="completed"

# Dispatch 子 Agent（Developer）
Agent prompt="..." subagent_type="general-purpose"

# 查看任务列表
TaskList
```

### 7.2 Developer 常用命令

```bash
# 一键质量检查
make check

# 仅运行测试
make test

# 格式化代码
make format

# 安装依赖
make install
```

### 7.3 审查用语

**Spec Reviewer 输出模板**:
```
规格审查结果: ✅ 通过 / ❌ 需修改

问题列表:
1. [ ] 问题描述 → 修复建议
2. [ ] ...
```

**Code Quality Reviewer 输出模板**:
```
代码质量审查结果: ✅ 通过 / ❌ 需修改

优点:
- ...

问题列表（按严重程度）:
1. [Critical] 问题描述 → 修复建议
2. [Important] ...
3. [Minor] ...
```

---

## 参考

- [开发工作流](workflow.md)
- [技术债务](tech-debt.md)
- [项目总览](../../PROJECT_OVERVIEW.md)
- [架构设计](../../architecture.md)
- [子 Agent 驱动开发 Skill](https://skill/subagent-driven-development)
- [并行 Agent 调度 Skill](https://skill/dispatching-parallel-agents)
- [Git Worktree Skill](https://skill/using-git-worktrees)
