# 部署手册

## 环境要求

- Docker Engine
- Docker Compose（v2 及以上，支持 `!override` 标签）
- 生产服务器外部建议开放 TCP 8443（HTTPS）与 8080（HTTP 跳转）；内网仍可使用 443
- 若只给内部使用，开放 443 即可

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
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://10.0.0.16,https://118.25.27.18,https://118.25.27.18:8443` 或你的域名 |
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
- 让 nginx 暴露 443（内网）和 8443（外网）两个 HTTPS 端口，并挂载 HTTPS 配置与证书
- 保留 HTTP 8080 端口用于自动跳转 HTTPS（外网 8080 会跳转到 8443）

访问：

- 内网：`https://<你的IP或域名>/`
- 外网：`https://<你的IP或域名>:8443/`

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

## 首次登录与管理后台

生产环境没有默认管理员账号，首次部署后必须手动创建超级用户：

```bash
docker compose -f compose.yaml -f compose.https.yaml exec web \
    python manage.py createsuperuser
```

创建完成后通过以下地址登录：

- 普通用户登录：
  - 内网：`https://<你的IP或域名>/accounts/login/`
  - 外网：`https://<你的IP或域名>:8443/accounts/login/`
- Django 管理后台：
  - 内网：`https://<你的IP或域名>/admin/`
  - 外网：`https://<你的IP或域名>:8443/admin/`

登录后，在 Django 后台 `/admin/accounts/user/` 和 `/admin/auth/group/` 中：

- 将用户加入 `member`、`buddy`、`leader` 组来分配角色
- 在 `Mentorship` 中建立 `member -> buddy` 关系

角色组会在数据库迁移时自动创建，无需手动新建。

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

- 应用健康：`https://<host>:8443/health/`（外网）或 `https://<host>/health/`（内网）
- web 容器健康检查：`curl http://localhost:8000/health/`
- 数据库健康检查：`pg_isready`

## 循环工程（Loop Engineering）

项目配置了两条 Playwright 验证循环，用于在生产环境持续验证端到端可用性与核心流程连贯性。

### 只读冒烟循环

- Cron：`/etc/cron.d/team-learn-plan-smoke`，每小时 :17 执行
- 脚本：`scripts/smoke-loop.sh`
- 测试：`tests/smoke/test_smoke_readonly.py`
- 内容：Member / Buddy / Leader 登录并检查对应工作台
- 日志：`output/smoke-loop.log`
- 截图：`output/smoke-screenshots/`

### 完整用户旅程循环

- Cron：`/etc/cron.d/team-learn-plan-journey`，每天 03:42 执行
- 脚本：`scripts/journey-loop.sh`
- 测试：`tests/smoke/test_smoke_journey.py`
- 数据命令：
  - `python manage.py create_smoke_journey`：创建/更新专用测试用户与 Buddy 关系
  - `python manage.py delete_smoke_journey`：清理测试产生的周期、计划、评估与证据数据
- 流程：Leader 创建周期 → Member 自评并生成计划 → Buddy 审批 → Member 提交进展与证据 → Buddy 验收 → Leader 归档周期
- 日志：`output/journey-loop.log`
- 截图：`output/journey-screenshots/`

> 测试账号与密码从 `/opt/team_learn_plan_smoke.env` 读取，文件不进入 Git。

## 故障排查

| 现象 | 排查方向 |
| --- | --- |
| 外部无法访问 8443/8080 | 检查云安全组/防火墙是否放行对应端口；443 仅在内网使用 |
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
