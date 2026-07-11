# 使用手册

`team_learn_plan` 是团队年度学习计划系统，用于维护成员能力模型、学习主题、进度跟踪与历史记录。

## 用户角色

系统通过 Django 用户组区分角色：

- **Member（成员）**：完成能力自评、生成学习计划、执行学习项、提交进度与证据。
- **Buddy（伙伴）**：审阅并批准成员的学习计划，审阅证据并给出指导意见。
- **Leader（负责人）**：管理人员与伙伴分配、创建/归档学习周期、查看团队看板与导出报表。
- **Admin/Manager（管理员）**：通过 Django 后台 `/admin/` 管理全部数据，拥有最高权限。

## 主要入口

| 入口 | 地址 | 说明 |
| --- | --- | --- |
| 登录 | `/accounts/login/` | 普通用户登录入口 |
| 首页 | `/` | 根据角色跳转到对应看板 |
| 成员看板 | `/dashboard/member/` | 我的周期、计划、待办 |
| 伙伴看板 | `/dashboard/buddy/` | 待审计划、待审证据 |
| 负责人看板 | `/dashboard/leader/` | 团队概览、周期管理、报表导出 |
| 历史记录 | `/dashboard/history/` | 已归档周期与个人学习历史 |
| 能力目录 | `/learning/admin/capabilities/` | Leader/Admin 维护能力模型 |
| Django 后台 | `/admin/` | Admin 数据管理 |

## 首次登录

系统没有预置默认管理员密码，首次使用需先创建超级用户：

```bash
docker compose -f compose.yaml -f compose.https.yaml exec web \
    python manage.py createsuperuser
```

然后访问登录页：

- 普通用户登录：`https://<你的IP或域名>/accounts/login/`
- Django 后台：`https://<你的IP或域名>/admin/`

登录后，超级用户可在 Django 后台 `/admin/auth/group/` 和 `/admin/accounts/user/` 中：

- 将普通用户加入 `member`、`buddy`、`leader` 组来分配角色
- 在 `Mentorship` 中建立 `member -> buddy` 关系

角色组（`member`/`buddy`/`leader`）会在数据库迁移时自动创建，无需手动新建。

## 典型流程

### 1. 初始化能力目录

Leader 或 Admin 上传标准 Excel 模板，导入能力目录：

```bash
docker compose -f compose.yaml -f compose.https.yaml exec web \
    python manage.py import_learning_template /path/to/template.xlsx --apply
```

导入前可先去掉 `--apply` 进行 dry-run。

### 2. 创建学习周期

Leader 进入“学习周期管理”，创建新周期并添加成员。系统会自动为每个成员按当前能力目录生成评估项。

### 3. 成员自评与生成计划

成员进入“能力自评”，逐项填写当前水平与目标水平，保存后点击“生成学习计划”。计划初始为草稿，可编辑后提交给 Buddy 审批。

### 4. Buddy 审批计划

Buddy 在伙伴看板查看待审计划，可“批准”或“要求修改”。若要求修改，成员需调整后再次提交。

### 5. 执行与提交证据

计划生效后，成员按计划项执行学习，记录进度更新，并可上传证据附件。Buddy 可查看进度、发表评论、审阅证据。

### 6. Leader  oversight 与导出

Leader 看板展示完成率、逾期项、反复修改项等指标。可在报表入口导出：

- 个人学习计划：`/reports/personal/<cycle_id>/`
- 团队学习计划：`/reports/team/<cycle_id>/`

## 管理员常用操作

- 创建用户：Django 后台 `/admin/accounts/user/` 或 `/admin/auth/group/`
- 分配角色：将用户加入 `member`、`buddy`、`leader` 组
- 指定 Buddy：在后台 `Mentorship` 中建立 `buddy -> member` 关系
- 激活/禁用用户：在用户列表切换 `is_active`

## 注意事项

- 上传附件大小受 nginx `client_max_body_size 20m` 限制。
- 生产环境务必使用 HTTPS，并开启 `DJANGO_SECURE_SSL_REDIRECT`、`DJANGO_SESSION_COOKIE_SECURE`、`DJANGO_CSRF_COOKIE_SECURE`。
