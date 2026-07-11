# 部署手册

## 环境要求

- Docker Engine
- Docker Compose（v2 及以上，支持 `!override` 标签）
- 生产服务器需开放 TCP 443（HTTPS）与 8080（HTTP 跳转）端口

## 本地开发部署（HTTP）

复制示例环境文件：

```bash
cp .env.example .env
```

`.env.example` 已配置为本地 HTTP，安全 cookie 标志均为 `false`。

启动栈：

```bash
docker compose up --build -d
```

访问：`http://localhost:8080/`

停止：

```bash
docker compose down
```

删除数据卷：

```bash
docker compose down -v
```

## 生产部署（HTTPS）

### 1. 准备环境文件

生产环境使用 `.env.production`：

```bash
cp .env.production .env.production
```

确认以下变量符合生产环境：

| 变量 | 生产建议值 |
| --- | --- |
| `DJANGO_SECRET_KEY` | 替换为强随机字符串 |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,10.0.0.16,118.25.27.18` 或你的域名 |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://10.0.0.16,https://118.25.27.18` 或你的域名 |
| `DJANGO_SECURE_SSL_REDIRECT` | `true` |
| `DJANGO_SESSION_COOKIE_SECURE` | `true` |
| `DJANGO_CSRF_COOKIE_SECURE` | `true` |

### 2. 准备 SSL 证书

默认使用自签名证书，存放于 `/opt/team_learn_plan_ssl/`：

```bash
mkdir -p /opt/team_learn_plan_ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /opt/team_learn_plan_ssl/selfsigned.key \
  -out /opt/team_learn_plan_ssl/selfsigned.crt \
  -subj "/CN=team-learn-plan" \
  -addext "subjectAltName=IP:118.25.27.18,IP:10.0.0.16"
chmod 600 /opt/team_learn_plan_ssl/selfsigned.key
chmod 644 /opt/team_learn_plan_ssl/selfsigned.crt
```

绑定域名后，替换为 Let’s Encrypt 等受信任证书即可。

### 3. 启动生产栈

```bash
docker compose -f compose.yaml -f compose.https.yaml up --build -d
```

`compose.https.yaml` 会：

- 将 web 服务的 `env_file` 覆盖为 `.env.production`
- 让 nginx 暴露 443 端口并挂载 HTTPS 配置与证书
- 保留 HTTP 8080 端口用于自动跳转 HTTPS

访问：`https://<你的IP或域名>/`

### 4. 持续部署

生产服务器已配置 cron：

```
/etc/cron.d/team-learn-plan-deploy
```

每 5 分钟执行 `scripts/deploy-https.sh`：

- 拉取 GitHub `main` 最新提交
- 若缺失证书则自动生成
- 使用 HTTPS 覆盖重建并启动容器
- 日志：`output/deploy-loop.log`

## 数据库与静态文件

- `web` 服务启动时会自动执行 `collectstatic` 和 `migrate`。
- 静态文件通过 nginx 直接服务。
- 媒体文件（证据附件等）持久化在 Docker volume `team_learn_plan_media`。

## 备份与恢复

### 备份

在 `web` 容器内执行：

```bash
docker compose -f compose.yaml -f compose.https.yaml exec web sh scripts/backup.sh
```

输出到 `./backups/`，包含数据库 dump、媒体/邮件归档、SHA-256 校验文件。

### 恢复

```bash
CONFIRM_RESTORE=yes docker compose -f compose.yaml -f compose.https.yaml exec -T web sh scripts/restore.sh \
    backups/db_YYYYMMDD_HHMMSS.sql \
    backups/assets_YYYYMMDD_HHMMSS.tar.gz \
    backups/sha256_YYYYMMDD_HHMMSS.txt
```

## 健康检查

- 应用健康：`https://<host>/health/`
- web 容器健康检查：`curl http://localhost:8000/health/`
- 数据库健康检查：`pg_isready`

## 故障排查

| 现象 | 排查方向 |
| --- | --- |
| 外部无法访问 443/8080 | 检查云安全组/防火墙是否放行对应端口 |
| nginx 启动失败 | 查看 `docker compose logs nginx`，常见原因是证书路径不存在 |
| web 健康检查失败 | 检查 `.env.production` 是否加载、数据库是否健康 |
| 静态文件 404 | 确认 `collectstatic` 已执行且 nginx 挂载了 `staticfiles` volume |
| HTTPS 跳转循环 | 确认 nginx 传递了 `X-Forwarded-Proto: https` |

## 环境变量参考

| 变量 | 说明 |
| --- | --- |
| `DJANGO_SETTINGS_MODULE` | 固定为 `config.settings.production` |
| `DJANGO_SECRET_KEY` | Django 密钥，生产必须替换 |
| `DJANGO_ALLOWED_HOSTS` | 逗号分隔的合法 Host 列表 |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | 逗号分隔的可信来源，需包含 HTTPS 地址 |
| `DJANGO_SECURE_SSL_REDIRECT` | 是否强制 HTTPS 跳转 |
| `DJANGO_SESSION_COOKIE_SECURE` | Cookie 是否仅通过 HTTPS 传输 |
| `DJANGO_CSRF_COOKIE_SECURE` | CSRF Cookie 是否仅通过 HTTPS 传输 |
| `DATABASE_URL` | PostgreSQL 连接字符串 |
