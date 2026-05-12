# 计划：搭建 Linglong 多 Agent 编排开发体系

## 上下文

Linglong 目前是一个 5 模块 Python monorepo（core / ingest / knowledge / composer / dispatch），已有完善的**手动流程文档**（workflow.md、CLAUDE.md、release-process.md）和 56 个通过的测试。但调研发现：

- **零自动化**：没有 CI、Makefile、Git hooks，lint/test/release 全靠记忆
- **ADR 目录为空**：架构决策无沉淀，多 Agent 协作无据可依
- **全局 skills 未引用**：用户已安装 `subagent-driven-development`、`dispatching-parallel-agents` 等 5 个 skill，但项目文档未提及
- **`.claude/` 不在仓库**：Agent 配置无法共享
- **workflow.md 编号混乱**：影响可读性

用户希望建立一套完整的多 Agent 编排体系，让 Architect / Developer / Reviewer / Tester 四种角色能在 Claude Code 内有序协作，并覆盖开发、测试、审查三个环节。

---

## 目标

建立"地基 → 规范 → 并行 → 把关 → 验证"的完整链条：

1. **一键标准化命令**（Agent 不会忘步骤）
2. **Agent 协作流程文档化**（有据可依）
3. **Worktree 并行开发**（模块间不冲突）
4. **CI 自动审查**（低质量代码进不来）
5. **Demo 验证**（证明体系可用，形成可复制案例）

---

## 实施计划

### Phase 1：基础设施自动化（优先级：最高）

**目标**：把 lint / format / test 变成一键命令，修复文档编号。

**文件变更**：

| 操作 | 路径 | 说明 |
|------|------|------|
| 创建 | `Makefile` | 标准化命令入口 |
| 修改 | `pyproject.toml` | 补充 `[tool.pytest.ini_options]` 配置 |
| 修改 | `docs/30-development/workflow.md` | 修复 section 编号混乱（当前有重复的 4/5/6） |
| 创建 | `.github/workflows/ci.yml` | PR 时自动跑 lint + test |

**Makefile 内容草案**：

```makefile
.PHONY: install lint format test check

install:
	pip install -e ".[dev,ingest,knowledge]"

lint:
	ruff check src/ tests/
	black --check src/ tests/

format:
	ruff check src/ tests/ --fix
	black src/ tests/

test:
	pytest -q

check: lint test
```

**验证**：
- `make check` 在本机能一次跑通（56 tests + lint clean）
- PR 到本仓库时 GitHub Actions 能触发并显示结果

---

### Phase 2：Agent 协作流程文档化（优先级：最高）

**目标**：把"多 Agent 怎么配合"写进项目文档，引用全局 skills，成为规范。

**文件变更**：

| 操作 | 路径 | 说明 |
|------|------|------|
| 创建 | `docs/20-architecture/adr/001-multi-agent-collaboration.md` | ADR：多 Agent 协作模型决策 |
| 创建 | `docs/20-architecture/adr/002-document-driven-development.md` | ADR：文档先行流程决策 |
| 创建 | `docs/30-development/agent-orchestration.md` | 核心：Agent 编排手册 |
| 修改 | `docs/00-roadmap/v0.3.md` | 把 Agent 协作体系加入 roadmap |

**`agent-orchestration.md` 核心章节**：

1. **角色定义**
   - Architect：接口设计、ADR、任务分解（主会话）
   - Developer：代码实现（子 Agent / worktree）
   - Reviewer：代码审查（子 Agent，审查 diff + 模块边界）
   - Tester：测试补充（子 Agent，边缘 case + E2E）

2. **何时使用子 Agent**
   - 独立模块开发 → `subagent-driven-development`
   - 跨模块并行调研 → `dispatching-parallel-agents`
   - 复杂功能实现前 → `writing-plans`
   - 已有计划需执行 → `executing-plans`

3. **Dispatch 规则**
   - 子 Agent prompt 必须包含：模块边界、禁止修改的文件列表、必须回归的测试命令
   - 子 Agent 输出必须先经过 Reviewer 审查，再合并到主分支
   - 涉及 `core/models.py` 或 `core/config.py` 的变更必须通知所有模块 Agent

**验证**：
- 新加入的 Agent（或未来会话）阅读 `agent-orchestration.md` 后能独立判断如何 dispatch 任务

---

### Phase 3：Worktree + 分支策略落地（优先级：中）

**目标**：让 4 个模块能真正并行开发，接口变更受控。

**文件变更**：

| 操作 | 路径 | 说明 |
|------|------|------|
| 修改 | `docs/30-development/workflow.md` | 新增"并行开发工作流"章节 |
| 创建 | `scripts/setup-worktree.sh` | 一键为指定模块创建 worktree |

**新增 workflow 章节要点**：

- 每个模块的 feature 分支命名：`feature/{module}/<description>`
- Worktree 工作流：
  ```bash
  # 主目录保持 main 分支干净
  git worktree add ../linglong-ingest-v2 feature/ingest/v2
  cd ../linglong-ingest-v2
  # 独立 Claude Code 会话在此开发
  ```
- 接口变更规则：任何模块修改 `core/` 或公共接口 → 必须先回主会话更新 ADR → 通知其他模块 Agent
- 合并顺序：core → ingest → knowledge → composer → dispatch（按依赖链）

**`scripts/setup-worktree.sh` 草案**：

```bash
#!/bin/bash
MODULE=$1
BRANCH=$2
WORKTREE_DIR="../linglong-${MODULE}-${BRANCH}"

git worktree add "$WORKTREE_DIR" -b "feature/${MODULE}/${BRANCH}"
cd "$WORKTREE_DIR"
source venv/bin/activate 2>/dev/null || python -m venv venv
pip install -e ".[dev,${MODULE}]"
echo "Worktree ready at $(pwd)"
```

**验证**：
- 执行 `./scripts/setup-worktree.sh composer yaml-support` 能成功创建独立目录并安装依赖
- 在 worktree 中修改代码不影响主仓库的 main 分支

---

### Phase 4：CI 自动审查（优先级：中）

**目标**：PR 质量自动化把关，Reviewer 有机器辅助。

**文件变更**：

| 操作 | 路径 | 说明 |
|------|------|------|
| 修改 | `.github/workflows/ci.yml` | 增加 PR block 逻辑 |
| 创建 | `.github/pull_request_template.md` | PR 检查清单 |
| 修改 | `pyproject.toml` | 增加 `pytest-cov` 到 dev 依赖 |

**PR Template 检查清单**：

```markdown
## 检查清单
- [ ] `make check` 本地通过
- [ ] 涉及接口变更 → ADR 已更新
- [ ] 涉及 `core/` 变更 → 其他模块已通知
- [ ] 新增代码 → 测试已同步补充
- [ ] 文档（`docs/`、`README.md`）已同步更新
- [ ] 技术债务已更新（如适用）
```

**验证**：
- 提交一个故意破坏 lint 的 PR → CI 失败 → 无法 merge
- 提交合规 PR → CI 通过 → 检查清单显示在 PR 页面

---

### Phase 5：Demo 验证（优先级：低，但关键）

**目标**：用真实功能走一遍完整多 Agent 流程，形成可复制案例。

**选型**：**frontmatter 复杂 YAML 支持**（v0.3 Next Actions #4）
- 范围适中（只改 `composer/templates/blog.py` + 测试）
- 不涉及跨模块接口变更
- 能充分展示 Developer → Reviewer → Tester 的协作

**流程**：

1. **Architect**（主会话）
   - 分析 `templates/blog.py` 当前 frontmatter 实现
   - 写 ADR（如果需要）或更新 `docs/90-reference/blog-style-guide.md`
   - 定义目标：支持 `tags: [a, b]` 和 `categories: [x, y]` 的 list 格式

2. **Developer**（子 Agent / worktree）
   - 在 `feature/composer/frontmatter-list` 分支实现
   - 修改 `src/linglong/composer/templates/blog.py`
   - 补充 `tests/composer/test_blog_template.py`

3. **Reviewer**（子 Agent）
   - 审查 diff：是否硬编码？是否违反模块边界？文档是否同步？
   - 输出审查报告

4. **Tester**（子 Agent）
   - 补充边缘 case：空 list、嵌套 list、特殊字符、YAML 转义
   - 运行 `make check`

5. **主会话集成**
   - 合并修改 → PR → CI 通过 → merge
   - 记录过程到 `docs/30-development/agent-orchestration-demo.md`

**验证**：
- Demo 文档能让未来的 Agent 按图索骥复制该流程
- `make check` 在 Demo 完成后仍全部通过

---

## 关键约束与注意事项

1. **文档先行**：每个 Phase 开始前，先更新 roadmap / ADR / workflow，再写代码/脚本
2. **不破坏现有 workflow**：Makefile 命令是新增入口，原有 `pytest`、`ruff check` 等手动命令仍可用
3. **模块边界**：Phase 1-4 的脚本和配置尽量放在仓库根目录或 `.github/`，不侵入 `src/linglong/` 各模块
4. **可回滚**：CI 配置从宽松开始（先跑 lint + test），再逐步增加严格检查（如 coverage gate）

---

## 重用已有资源

| 资源 | 位置 | 用途 |
|------|------|------|
| 现有 ruff/black/mypy 配置 | `pyproject.toml` | Phase 1 直接复用，无需重新设计 |
| 现有测试 fixtures | `tests/composer/conftest.py` | Phase 5 Demo 复用 Composer 的临时存储 fixture |
| 全局 skills | `~/.claude/skills/` | Phase 2 文档中引用，告诉 Agent 何时调用 |
| 现有 Git 分支策略 | `docs/30-development/workflow.md` §1 | Phase 3 在此基础上扩展 worktree |

---

## 验收标准

全部 5 个 Phase 完成后，应满足：

1. 新 Agent 加入项目 → 阅读 `agent-orchestration.md` → 能在 10 分钟内理解如何协作
2. 任意开发者（人或 Agent）执行 `make check` → 一键得到 lint + test 结果
3. 提交 PR → CI 自动运行 → 失败则 block merge
4. 两个模块能同时在独立 worktree 中开发 → 合并时无冲突
5. `docs/30-development/agent-orchestration-demo.md` 存在 → 能按文档复刻一次完整的多 Agent 开发流程
