# 运维与发布

## 发布流程

### 发布前

- [ ] 确认当前里程碑所有 Issue 已完成或延期
- [ ] 确认 docs/ 与代码一致
- [ ] 全部测试通过：`pytest -v`

### 发布

```bash
# 1. 更新版本号
# 编辑 pyproject.toml: version = "x.y.z"

# 2. 提交
git add pyproject.toml
git commit -m "release: bump version to x.y.z"

# 3. 打标签
git tag -a vx.y.z -m "Release version x.y.z"

# 4. 推送
git push origin main
git push origin vx.y.z
```

### 发布后

- [ ] `pip install -e .` 导入无错误
- [ ] Composer 运行无报错

### 紧急修复

1. 在 main 修复 Bug 并补充测试
2. 提升补丁版本号（0.2.0 → 0.2.1）
3. 打标签 `v0.2.1` 并推送

## 版本号规则

采用语义化版本 `MAJOR.MINOR.PATCH`：

- **MAJOR**: 不兼容的 API 变更
- **MINOR**: 向下兼容的功能新增
- **PATCH**: 向下兼容的问题修复

---

## 技术债务

### DEBT-003: 配置中部分值仍硬编码

- **严重程度**: 中
- **状态**: 待解决
- **说明**: 部分超时、阈值等参数尚未提取到配置

### DEBT-007: OpenClawSource mtime 去重不稳定

- **严重程度**: 低
- **状态**: 已修复，需验证长期稳定性
- **说明**: 迁移后改为 ComposerState 内容哈希去重

### DEBT-010: Composer State 使用内容哈希而非 entity_id

- **严重程度**: 低
- **状态**: 已解决（v1.0 新增 output_log 表，按 entity_id 追踪输出状态）
- **说明**: 原先使用内容哈希去重，v1.0 改为基于 entity_id 的 output_log 追踪

### 已解决

| 编号 | 说明 | 解决时间 |
|------|------|----------|
| DEBT-001 | 旧 pipeline 代码未清理 | 2026-05-12 |
| DEBT-002 | Entity 模型字段不完整 | 2026-05-12 |
| DEBT-004 | Composer 从 pipeline 迁移 | 2026-05-12 |
| DEBT-005 | 缺少 lint/format 工具 | 2026-05-12 |
| DEBT-006 | tests/ 覆盖率不足 | 2026-05-12 |
| DEBT-008 | 封面图生成冲突 | 2026-05-13 |
| DEBT-009 | LLM Prompt 硬编码 | 2026-05-12 |
