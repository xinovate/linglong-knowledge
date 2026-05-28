# 运维与发布

Linglong Knowledge 的发布流程、服务部署和故障排查。

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
- [ ] MCP 远程端点 `https://your-domain.com/mcp/knowledge` 可达
- [ ] Redis `linglong-redis` 容器运行正常
- [ ] Cloudflare Tunnel `cloudflared-mcp` 服务运行正常
- [ ] Cloudflare SSL 证书未过期

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
| DEBT-010 | Composer State（模块已移除） | 2026-05-27 |

---

## 服务安全加固

服务器 `localhost` 上部署了 Docker 服务供 linglong 使用，需启用 API Key 认证防止未授权访问。

### 服务清单

| 端口 | 服务 | 用途 | 认证方式 |
|------|------|------|----------|
| 7997 | Embedding | 向量嵌入 | Bearer Token（`embedding_api_key` 配置） |

### Embedding 服务加固

设置方式：

```yaml
# .knowledge.yml
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
export EMBEDDING_API_KEY="your-embedding-secret"
```

### MCP Client 配置

MCP Server 以子进程方式启动，API Key 需通过 `env` 字段注入（不继承 shell 环境变量）：

```json
{
  "mcpServers": {
    "linglong-knowledge": {
      "command": "bash",
      "args": ["-c", "cd /path/to/linglong-knowledge && source venv/bin/activate && python -m linglong.mcp"],
      "env": {
        "EMBEDDING_API_KEY": "your-key"
      }
    }
  }
}
```

**注意**：MCP 子进程不会读取 `~/.bashrc`，必须通过 `env` 显式传入。

---

## Cloudflare Tunnel 部署

`your-domain.com` 通过 Cloudflare Tunnel 暴露 MCP 服务，绕过阿里云 ICP 域名备案拦截。

### 架构

```
用户 → https://your-domain.com → Cloudflare CDN → Tunnel → 127.0.0.1:9900 (linglong-mcp)
```

### 服务清单

| 服务 | 说明 |
|------|------|
| `cloudflared-mcp` | Cloudflare Tunnel 守护进程（systemd） |
| `linglong-mcp` | MCP Server（systemd，监听 127.0.0.1:9900） |
| `linglong-redis` | Token 认证存储（Docker，127.0.0.1:6379） |

### 关键文件

| 路径 | 说明 |
|------|------|
| `/root/.cloudflared/config.yml` | Tunnel 配置（指向 127.0.0.1:9900） |
| `/root/.cloudflared/cert.pem` | Cloudflare 授权证书 |
| `/root/.cloudflared/<tunnel-id>.json` | Tunnel 凭证 |
| `/etc/systemd/system/cloudflared-mcp.service` | systemd 服务 |
| `/etc/nginx/conf.d/blog.conf` | nginx（博客 443，MCP 已移至 Tunnel） |

### DNS 配置

`your-domain.com` 为 CNAME 记录指向 `cfargotunnel.com`，由 Cloudflare 代理（橙色云）。

### Token 管理

```bash
# 新增 token
redis-cli SET knowledge-<random> active

# 查看所有 token
redis-cli KEYS 'knowledge-*'

# 删除 token
redis-cli DEL knowledge-<random>
```

### 故障排查

```bash
# 检查 Tunnel 状态
systemctl status cloudflared-mcp

# 检查 MCP 服务状态
systemctl status linglong-mcp

# 测试 MCP 端点
curl -X POST https://your-domain.com/mcp/knowledge \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```
