# 安全要求

## 认证

- MCP 远程端点：Token 认证，通过 `TokenAuthMiddleware` 实现
- Token 来源：Redis 优先，静态降级。格式：`linglong-<模块>-<随机串>`
- Redis 存储：key = token 值，value = `"active"`，无 TTL
- Token 和 API Key 禁止提交到 git，使用环境变量或 Redis

## API Key 管理

- 所有第三方服务密钥（智谱、SearXNG、RSSHub、Embedding）从环境变量加载
- systemd 服务文件用 `Environment=` 指令，不在 Python 源码中硬编码
- 本地开发：密钥可放 `.linglong.yaml`（已 gitignore）或环境变量

## SQL 注入防护

- 所有用户输入必须参数化查询（`?` 占位符）
- 动态 WHERE 仅限硬编码列名构建
- 详见 `code-style.md` SQL 章节

## 网络安全

- SearXNG：nginx 反向代理 + API Key 校验
- RSSHub：`ACCESS_KEY` 参数保护
- Embedding 服务：Bearer Token 认证
- MCP 服务：绑定 `127.0.0.1`，外部通过 nginx 反代或 Cloudflare Tunnel 访问

## 敏感数据

- 禁止在日志中记录 API Key、Token、用户凭据
- `.env`、凭据文件、密钥文件禁止提交到 git
- `wiki/personal/` 含敏感记录，禁止通过公开端点暴露

## Cloudflare Tunnel

- 远程 MCP 使用 Cloudflare Tunnel（出站连接），无需开放入站端口
- DNS 由 Cloudflare NS 管理（`ns.cloudflare.com` / `ns.cloudflare.com`）
- SSL 在 Cloudflare 终止，Tunnel → 本地服务走 HTTP localhost
- 部署细节见 `docs/operations.md`
