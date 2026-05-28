# 隐私规约

本仓库为公开仓库，以下内容禁止出现在代码、文档、配置、测试、日志中（包括 git 历史）：

## 禁止项

- **服务器 IP** 和公网端口映射 — 用 `localhost` 或 `your-domain.com` 占位
- **个人路径** — `/Users/<name>/`、`/home/<name>/` 等真实路径用通用占位符
- **基础设施细节** — DNS 记录、Cloudflare tunnel ID、SSL 证书路径、systemd 服务名、nginx 配置路径
- **内部服务 URL** — SearXNG、RSSHub、Embedding 等真实端点地址
- **凭据** — API Key、Token、密码，无论明文还是硬编码默认值

## 允许保留的公开信息

- `pyproject.toml` 作者字段（开源项目标准）
- 仓库 URL（`github.com/<user>/linglong-knowledge`）
- 通用示例值（`human:alice`、`your-key`、`localhost:7997`）

## 检查方法

```bash
grep -rn "敏感模式" --include="*.py" --include="*.md" --include="*.yml" | grep -v .venv/
```
