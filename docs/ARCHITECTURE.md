# 架构与方案

## 技术栈

- **后端**：Python 3.13 + Django 5.2 + Gunicorn
- **数据库**：PostgreSQL 17（开发环境可用 SQLite）
- **前端**：Django 服务端模板 + 少量原生 JS
- **静态/媒体文件**：nginx 反向代理并直接服务
- **包管理**：`uv` + `pyproject.toml` + `uv.lock`
- **容器化**：Docker + Docker Compose
- **测试**：pytest + pytest-django + Playwright（UI 回归）

## 应用划分

| 应用 | 职责 |
| --- | --- |
| `apps/accounts` | 自定义 User、角色组、Mentorship 关系、登录/登出 |
| `apps/learning` | 核心领域：能力目录、学习周期、评估、学习计划、进度、证据、审批 |
| `apps/dashboard` | 角色化看板与聚合指标 |
| `apps/reports` | 个人与团队 Excel 报表导出 |

## 核心数据模型

```text
CapabilityCategory
  └── CapabilityDomain (level 1/2，层级)
        └── CapabilityItem
              └── CapabilityMaterial → LearningMaterial

LearningCycle
  └── CycleParticipant
        └── Assessment (per CapabilityItem，当前/目标水平 0-5)
        └── LearningPlan (draft → pending approval → active)
              └── PlanItem (assessment 快照 + 执行状态)
                    ├── ProgressUpdate
                    ├── GuidanceComment
                    ├── EvidenceSubmission
                    │       └── EvidenceAttachment
                    └── ReviewDecision

PlanApprovalEvent      # 计划审批审计
CatalogSyncLog         # 能力目录变更同步到活跃计划
Mentorship             # buddy → member 关系
```

## 角色权限

角色对应 Django 用户组 `member`、`buddy`、`leader`，在迁移时创建。视图层通过 `User.groups` 与 `Mentorship` 关系控制访问：

- 成员只能查看/编辑自己的计划与证据
- Buddy 只能审阅自己指导的成员
- Leader 可管理周期、用户、查看团队报表
- Admin 通过 Django 后台无限制访问

## 学习周期评估流程

1. Leader 创建 `LearningCycle` 并添加 `CycleParticipant`。
2. 加入时自动为每个生效的 `CapabilityItem` 创建 `Assessment`。
3. 成员填写自评后生成 `LearningPlan` 草稿。
4. Buddy 审批通过后计划变为 `active`。
5. 成员在执行过程中提交 `ProgressUpdate` 与 `EvidenceSubmission`。
6. Buddy 审阅并给出 `ReviewDecision` 或 `GuidanceComment`。
7. 周期结束后 Leader 归档，历史记录保留。

## 部署架构

```text
                    ┌─────────────┐
    HTTP/HTTPS  ──> │    nginx    │ ──┐
                    └─────────────┘   │
                         │            │
                    static/media      │
                         │            │
                    ┌────┴────┐       │
                    │   web   │ <─────┘
                    │ (Django)│
                    └────┬────┘
                         │
                    ┌────┴────┐
                    │    db   │
                    │(Postgres)│
                    └─────────┘
```

- `nginx` 服务静态文件、媒体文件，并将动态请求代理到 `web`。
- `web` 运行 Gunicorn，入口脚本会自动执行 `collectstatic` 与 `migrate`。
- `db` 使用 Docker named volume 持久化。

## 安全配置

生产设置位于 `config/settings/production.py`：

- `DEBUG = False`
- `SECURE_SSL_REDIRECT = true`（通过环境变量关闭）
- `SECURE_HSTS_SECONDS = 60`
- `SESSION_COOKIE_SECURE = true`
- `CSRF_COOKIE_SECURE = true`
- `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`
- `/health/` 被加入 `SECURE_REDIRECT_EXEMPT`，保证容器健康检查可用。

## 持续部署

- `scripts/deploy-https.sh` 每 5 分钟检测 GitHub `main` 分支。
- 发现新提交后执行 `git pull` 并使用 HTTPS 覆盖启动/重建容器。
- 通过 `flock` 防止并发执行。
- 部署日志：`output/deploy-loop.log`。

## 备份与恢复

- `scripts/backup.sh`：导出 PostgreSQL 并打包 `media/`、`emails/`，生成 SHA-256 校验文件。
- `scripts/restore.sh`：校验后恢复数据库与文件。
