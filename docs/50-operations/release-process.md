# 发布流程

本文档定义 linglong 从版本规划到线上验证的完整发布 checklist。

## 发布前准备

### 1. 核对路线图

- [ ] 确认当前里程碑（Milestone）的所有 Issue / Task 已完成或已延期。
- [ ] 确认 `docs/` 中的设计与操作文档与代码实现一致。

### 2. 运行测试

```bash
cd /home/user/projects/linglong
source venv/bin/activate
python -m pytest tests/ -v
```

- [ ] 全部单元测试通过。
- [ ] 手动执行回归 checklist，关键用例通过。

### 3. 更新 CHANGELOG

按照 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 格式，在 `CHANGELOG.md` 中：

1. 将 `[Unreleased]` 下的内容整理为新版本节。
2. 新增版本节格式：

```markdown
## [x.y.z] - YYYY-MM-DD

### Added
- ...

### Changed
- ...

### Fixed
- ...
```

- [ ] CHANGELOG 已更新并提交。

## 版本发布

### 4. 提升版本号

当前版本号记录在 `pyproject.toml` 中。修改后提交：

```bash
# 编辑 pyproject.toml，将 version = "0.1.0" 改为新版本
sed -i '' 's/version = "0.1.0"/version = "0.2.0"/' pyproject.toml
git add pyproject.toml CHANGELOG.md
git commit -m "release: bump version to 0.2.0"
```

### 5. 创建标签

```bash
git tag -a v0.2.0 -m "Release version 0.2.0"
```

### 6. 推送代码与标签

```bash
git push origin main
git push origin v0.2.0
```

## 发布后验证

### 7. 安装验证

```bash
pip install -e .
python -c "import linglong; print('OK')"
```

- [ ] 导入无错误。

### 8. Composer 模块验证（如涉及内容生产）

```bash
python -c "
from linglong.composer import Composer
from linglong.knowledge.store import KnowledgeStore
from linglong.core.models import Entity, EntityStatus, Source, SourceType

store = KnowledgeStore()
entity = Entity(
    content='# 测试\n\n内容',
    created_by='agent:test',
    status=EntityStatus.AUTO_CONFIRMED,
    sources=[Source(type=SourceType.MEMORY, name='test')],
)
store.create(entity)

p = Composer()
result = p.run()
print(result)
"
```

- [ ] Composer 运行无报错。
- [ ] 生成内容格式正确。

## 紧急修复流程

若线上发现严重 Bug，可跳过部分文档步骤，按以下最小流程执行：

1. 在主干修复 Bug 并补充测试。
2. 更新 CHANGELOG（标记为 Fixed）。
3. 提升补丁版本号（如 `0.2.0` → `0.2.1`）。
4. 打标签 `v0.2.1` 并推送。
5. 验证部署。

## 版本号规则

本项目采用语义化版本（SemVer）：

- **MAJOR**：不兼容的 API 变更或架构重构。
- **MINOR**：向下兼容的功能新增（如新模块、新配置项）。
- **PATCH**：向下兼容的问题修复。
