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
- [ ] 全部测试通过

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
- **说明**: 迁移后改为按内容哈希去重

### DEBT-010: Composer State 使用内容哈希而非 entity_id

- **严重程度**: 低
- **状态**: 已关闭（composer 模块已在 v2.5 移除）
- **说明**: 原 composer 的 State 组件已随模块一并删除

### 已解决

| 编号 | 说明 | 解决时间 |
|------|------|----------|
| DEBT-001 | 旧 pipeline 代码未清理 | 2026-05-12 |
| DEBT-002 | Entity 模型字段不完整 | 2026-05-12 |
| DEBT-004 | Composer 从 pipeline 迁移（已移除） | 2026-05-12 |
| DEBT-005 | 缺少 lint/format 工具 | 2026-05-12 |
| DEBT-006 | tests/ 覆盖率不足 | 2026-05-12 |
| DEBT-008 | 封面图生成冲突 | 2026-05-13 |
| DEBT-009 | LLM Prompt 硬编码 | 2026-05-12 |

---

## 服务安全加固

服务器 `localhost` 上部署了 3 个 Docker 服务供 linglong 使用，需启用 API Key 认证防止未授权访问。

### 服务清单

| 端口 | 服务 | 用途 | 认证方式 |
|------|------|------|----------|
| 8088 | SearXNG | 网页搜索 | Bearer Token（limiter 插件） |
| 1200 | RSSHub | RSS 聚合 | URL 参数 `?key=xxx` |
| 7997 | Embedding | 向量嵌入 | Bearer Token（已有 `embedding_api_key` 配置） |

### SearXNG 加固

通过 nginx 反向代理实现 Bearer Token 认证。

1. SearXNG 容器绑定到 `127.0.0.1:8089`（仅本地可访问）：
```bash
docker run -d --name searxng -p 127.0.0.1:8089:8080 \
  -v /opt/searxng/settings.yml:/etc/searxng/settings.yml:ro \
  searxng/searxng:latest
```

2. nginx 配置 `/etc/nginx/conf.d/searxng.conf`：
```nginx
map $http_authorization $searxng_auth {
    "Bearer your-secret-key" 1;
    default 0;
}
server {
    listen 8088;
    location / {
        if ($searxng_auth = 0) {
            return 403;
        }
        proxy_pass http://127.0.0.1:8089;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. 启用 limiter（可选，防滥用）：
```yaml
# settings.yml
server:
  limiter: true
```

### RSSHub 加固

在 RSSHub 的 `docker-compose.yml` 或 `docker run` 中设置环境变量：

```bash
docker run -d -p 1200:1200 -e ACCESS_KEY=your-secret-key diygod/rsshub
```

在 linglong 配置中设置：

```yaml
# .linglong.yaml
ingest:
  rsshub_access_key: ${RSSHUB_ACCESS_KEY}
```

### Embedding 服务加固

Embedding 服务已支持 `embedding_api_key` 配置（Bearer Token 认证）。设置方式：

```yaml
# .linglong.yaml
knowledge:
  embedding_api_key: ${EMBEDDING_API_KEY}
```

如需反向代理，可用 nginx：

```nginx
location /embeddings {
    proxy_pass http://127.0.0.1:7997;
    proxy_set_header Authorization $http_authorization;
}
```

### 环境变量设置

在本地设置环境变量（不要写入代码仓库）：

```bash
# ~/.zshrc 或 ~/.bashrc
export SEARXNG_API_KEY="your-searxng-secret"
export RSSHUB_ACCESS_KEY="your-rsshub-secret"
export EMBEDDING_API_KEY="your-embedding-secret"
```

### MCP Client 配置

MCP Server 以子进程方式启动，API Key 需通过 `env` 字段注入（不继承 shell 环境变量）：

```json
{
  "mcpServers": {
    "linglong": {
      "command": "bash",
      "args": ["-c", "cd /path/to/linglong && source venv/bin/activate && python -m linglong.mcp"],
      "env": {
        "SEARXNG_API_KEY": "your-key",
        "RSSHUB_ACCESS_KEY": "your-key",
        "EMBEDDING_API_KEY": "your-key"
      }
    }
  }
}
```

**注意**：MCP 子进程不会读取 `~/.bashrc`，必须通过 `env` 显式传入。
