# 团队年度学习计划 Web 系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有能力模型 Excel 转换为可部署的多人学习计划 Web 系统，覆盖成员自评、Buddy 审批与验收、Leader 管理和团队分析。

**Architecture:** 使用 Django 5.2 LTS 单体应用和服务端模板，按 `accounts`、`learning`、`dashboard`、`reports` 四个业务边界组织代码。PostgreSQL 保存业务数据，服务器持久化卷保存附件；固定流程由 django-fsm-2 管理，关键模型由 django-simple-history 审计。

**Tech Stack:** Python 3.13、Django 5.2 LTS、PostgreSQL 17、pytest、pytest-django、django-fsm-2、django-simple-history、django-filter、django-tables2、django-import-export、openpyxl、Tabler、Chart.js、Docker Compose、Gunicorn、Nginx。

**Specification:** `docs/superpowers/specs/2026-07-09-team-learning-plan-web-design.md`

---

## 执行约束

- 项目根目录固定为 `/opt/personal-agent-workspace/team_learn_plan`。
- Codex 分阶段调用真实 Claude Code CLI；Claude Code 不提交。
- 每个任务开始前，Codex 在 handoff 中记录候选 GitHub 模块、许可证、复用范围和拒绝原因。
- Claude Code 只能修改当前任务列出的文件；遇到配置、脚本、数据写入、删除、跨项目操作或 sudo 时停止，由 Codex 向用户确认。
- Excel 原文件只读；初始化数据写入测试数据库，不回写 Excel。
- 当前目录不是独立 Git 仓库。开始 Task 1 前，Codex 必须获得用户对独立仓库初始化和项目配置文件写入的确认。
- 每个任务完成后，Codex 复跑验收命令、检查 diff 范围和 Git 状态；独立仓库及 remote 确认后才提交。

## 目标文件结构

```text
team_learn_plan/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/
│   │   ├── admin.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── tests/
│   ├── learning/
│   │   ├── admin.py
│   │   ├── filters.py
│   │   ├── forms.py
│   │   ├── models/
│   │   │   ├── base_data.py
│   │   │   ├── cycle.py
│   │   │   ├── execution.py
│   │   │   └── planning.py
│   │   ├── services/
│   │   │   ├── assessment.py
│   │   │   ├── importer.py
│   │   │   ├── planning.py
│   │   │   └── sync.py
│   │   ├── tables.py
│   │   ├── transitions.py
│   │   ├── urls.py
│   │   ├── views/
│   │   └── tests/
│   ├── dashboard/
│   │   ├── selectors.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── tests/
│   └── reports/
│       ├── excel.py
│       ├── urls.py
│       ├── views.py
│       └── tests/
├── templates/
├── static/vendor/
├── tests/
├── Dockerfile
├── compose.yaml
├── manage.py
└── pyproject.toml
```

## Task 1：最小生产骨架与登录

**Goal:** 交付可启动、可测试、可登录的 Django 应用。

**GitHub reuse:** 参考 Cookiecutter Django 的分层 settings、环境变量、Docker 和测试结构；不启用 allauth、Celery、REST API、云存储或真实邮件。

**Files:**

- Create: `pyproject.toml`
- Create: `manage.py`
- Create: `config/settings/base.py`
- Create: `config/settings/local.py`
- Create: `config/settings/production.py`
- Create: `config/urls.py`
- Create: `config/wsgi.py`
- Create: `apps/accounts/models.py`
- Create: `apps/accounts/admin.py`
- Create: `apps/accounts/views.py`
- Create: `apps/accounts/urls.py`
- Create: `templates/registration/login.html`
- Create: `templates/base.html`
- Create: `apps/accounts/tests/test_auth.py`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: 记录配置写入确认**

Codex 在 handoff 中列明本任务会新增 `pyproject.toml`、Django settings、`.env.example` 和 `.gitignore`，获得用户确认后再分派。

- [ ] **Step 2: 写登录失败测试**

```python
import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_anonymous_user_is_redirected_to_login(client):
    response = client.get(reverse("home"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))
```

- [ ] **Step 3: 验证测试先失败**

Run: `uv run pytest apps/accounts/tests/test_auth.py -q`

Expected: FAIL，因为项目、URL 或 `home` 尚不存在。

- [ ] **Step 4: 实现最小骨架**

依赖仅包含运行和测试当前任务需要的包。创建自定义 `User(AbstractUser)`，为后续角色扩展保留稳定用户表；首页使用 `LoginRequiredMixin`。本地设置使用 SQLite 仅供快速单测，生产设置强制读取 PostgreSQL 环境变量。

- [ ] **Step 5: 验证登录与系统检查**

Run:

```bash
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate
uv run pytest apps/accounts/tests/test_auth.py -q
uv run python manage.py check
```

Expected: 全部退出码为 0，测试 PASS，`check` 无问题。

- [ ] **Step 6: Codex 验证**

Codex 检查未引入 SPA、API、Celery、Redis、allauth 或外部邮件服务；确认秘密值不在版本库中。

## Task 2：角色、Buddy 绑定与角色工作台

**Goal:** 成员、Buddy、Leader 登录后进入对应工作台，并严格限制对象范围。

**GitHub reuse:** 使用 Django Groups/Permissions；不引入对象权限依赖。

**Files:**

- Modify: `apps/accounts/models.py`
- Create: `apps/accounts/services.py`
- Modify: `apps/accounts/views.py`
- Modify: `apps/accounts/urls.py`
- Create: `apps/accounts/tests/test_roles.py`
- Create: `apps/accounts/tests/test_mentorship.py`
- Create: `templates/accounts/home.html`
- Create: `templates/accounts/user_admin.html`

- [ ] **Step 1: 写绑定范围失败测试**

```python
@pytest.mark.django_db
def test_buddy_only_sees_bound_members(buddy_client, member, other_member):
    response = buddy_client.get(reverse("home"))
    members = list(response.context["members"])
    assert member in members
    assert other_member not in members
```

- [ ] **Step 2: 验证测试先失败**

Run: `uv run pytest apps/accounts/tests/test_roles.py apps/accounts/tests/test_mentorship.py -q`

Expected: FAIL，因为 Mentorship 和角色查询尚不存在。

- [ ] **Step 3: 实现角色和 Mentorship**

角色使用 `member`、`buddy`、`leader` 三个 Django Group。`Mentorship` 保存成员、Buddy、生效时间、失效时间；数据库约束保证每名成员最多一个当前 Buddy。角色工作台通过服务函数返回授权 queryset，不在模板层过滤。

- [ ] **Step 4: 验证角色边界**

Run: `uv run pytest apps/accounts/tests -q`

Expected: PASS；成员、Buddy、Leader 的首页数据范围不同。

- [ ] **Step 5: Codex 验证**

Codex 用三个测试账号访问首页和管理 URL，确认直接输入 URL 也无法越权。

## Task 3：能力模型、材料与 Excel 初始化导入

**Goal:** 从 V1.3 Excel 一次性导入 310 个三级能力项、学习材料和关联关系。

**GitHub reuse:** Django admin、django-import-export 和 openpyxl；业务初始化采用显式映射，不使用通用模型反射导入。

**Files:**

- Create: `apps/learning/models/__init__.py`
- Create: `apps/learning/models/base_data.py`
- Create: `apps/learning/admin.py`
- Create: `apps/learning/services/importer.py`
- Create: `apps/learning/management/commands/import_learning_template.py`
- Create: `apps/learning/tests/test_importer.py`
- Create: `apps/learning/tests/test_base_data.py`

- [ ] **Step 1: 记录脚本与数据写入确认**

Codex 列明将新增导入命令；命令只读取 Excel，默认 `--dry-run`，只有显式 `--apply` 才写数据库。获得用户确认后分派。

- [ ] **Step 2: 写导入失败测试**

```python
@pytest.mark.django_db
def test_template_import_builds_expected_catalog(template_path):
    result = import_template(template_path, apply=True)
    assert result.capability_items == 310
    assert CapabilityItem.objects.count() == 310
    assert LearningMaterial.objects.exists()
    assert not result.errors
```

- [ ] **Step 3: 验证测试先失败**

Run: `uv run pytest apps/learning/tests/test_importer.py -q`

Expected: FAIL，因为模型和 importer 尚不存在。

- [ ] **Step 4: 实现基础数据和两阶段导入**

模型覆盖能力类别、一级/二级能力域、三级能力项、学习材料及多对多关系。预检验证 sheet、表头、编码唯一性、层级、材料编码和 310 行能力数据；写入在 `transaction.atomic()` 中执行。已使用数据只能停用。

- [ ] **Step 5: 验证 dry-run 和 apply**

Run:

```bash
uv run python manage.py import_learning_template \
  团队成员年度学习计划模板_基于能力模型_V1.3.xlsx --dry-run
uv run pytest apps/learning/tests/test_importer.py apps/learning/tests/test_base_data.py -q
```

Expected: dry-run 输出 310 个能力项且数据库无变化；测试 PASS。

- [ ] **Step 6: Codex 验证**

Codex抽查 P01.01.01、材料 P01-M001 和多材料能力项，确认字段与 Excel 相同。

## Task 4：学习周期与能力自评

**Goal:** Leader 创建两类周期，成员在高密度表格中自动保存自评。

**GitHub reuse:** django-tables2、django-filter、Tabler 表格与状态组件。

**Files:**

- Create: `apps/learning/models/cycle.py`
- Create: `apps/learning/services/assessment.py`
- Create: `apps/learning/forms.py`
- Create: `apps/learning/filters.py`
- Create: `apps/learning/tables.py`
- Create: `apps/learning/views/assessment.py`
- Create: `apps/learning/views/cycle.py`
- Create: `apps/learning/urls.py`
- Create: `templates/learning/assessment.html`
- Create: `templates/learning/cycle_admin.html`
- Create: `static/js/assessment.js`
- Create: `apps/learning/tests/test_cycles.py`
- Create: `apps/learning/tests/test_assessment.py`

- [ ] **Step 1: 写权限和自动保存失败测试**

```python
@pytest.mark.django_db
def test_member_cannot_update_another_members_assessment(
    member_client, other_member_assessment
):
    response = member_client.post(
        reverse("learning:assessment-save", args=[other_member_assessment.pk]),
        {"current_level": 2, "target_level": 3},
    )
    assert response.status_code == 404
```

- [ ] **Step 2: 验证测试先失败**

Run: `uv run pytest apps/learning/tests/test_cycles.py apps/learning/tests/test_assessment.py -q`

Expected: FAIL，因为周期、自评和保存端点尚不存在。

- [ ] **Step 3: 实现周期和 Assessment**

自然年周期和连续 12 个月周期统一保存明确的开始/结束日期。Assessment 唯一键为成员、周期、能力项；差距在服务端计算。批量操作和单行保存使用普通 Django POST，返回小型 JSON，不建设通用 REST API。

- [ ] **Step 4: 实现高密度自评页**

提供能力层级折叠、组合筛选、键盘移动、批量设置、保存状态和填写进度。JavaScript 只负责交互，权限和计算均在服务端。

- [ ] **Step 5: 验证**

Run:

```bash
uv run pytest apps/learning/tests/test_cycles.py apps/learning/tests/test_assessment.py -q
uv run python manage.py check
```

Expected: PASS；越权返回 404，归档周期写入返回 409。

- [ ] **Step 6: Codex 浏览器验收**

使用测试数据打开 310 行自评，验证筛选、折叠、键盘输入、批量操作和失败重试。

## Task 5：计划生成与 Buddy 审批

**Goal:** 从自评生成快照计划，并完成提交、退回、再提交和审批。

**GitHub reuse:** django-fsm-2 管理计划状态；django-simple-history 记录变更。

**Files:**

- Create: `apps/learning/models/planning.py`
- Create: `apps/learning/services/planning.py`
- Create: `apps/learning/transitions.py`
- Create: `apps/learning/views/planning.py`
- Create: `templates/learning/plan_detail.html`
- Create: `templates/learning/buddy_approvals.html`
- Create: `apps/learning/tests/test_plan_generation.py`
- Create: `apps/learning/tests/test_plan_approval.py`

- [ ] **Step 1: 写快照和状态失败测试**

```python
@pytest.mark.django_db
def test_approved_plan_cannot_be_edited(approved_plan, member_client):
    item = approved_plan.items.first()
    response = member_client.post(
        reverse("learning:plan-item-edit", args=[item.pk]),
        {"task": "changed"},
    )
    assert response.status_code == 409
```

- [ ] **Step 2: 验证测试先失败**

Run: `uv run pytest apps/learning/tests/test_plan_generation.py apps/learning/tests/test_plan_approval.py -q`

Expected: FAIL，因为 LearningPlan、PlanItem 和状态转换尚不存在。

- [ ] **Step 3: 实现生成和状态机**

`generate_plan()` 只处理 `included=True` 的 Assessment，并保存能力与材料快照。状态为 `draft → pending_approval → active`，退回为 `pending_approval → changes_requested → pending_approval`。退回意见必填，只有当前 Buddy 可决策。

- [ ] **Step 4: 验证审批**

Run: `uv run pytest apps/learning/tests/test_plan_generation.py apps/learning/tests/test_plan_approval.py -q`

Expected: PASS；重复提交、非绑定 Buddy 和审批后编辑均失败。

- [ ] **Step 5: Codex 端到端验收**

成员生成并提交计划，Buddy 退回，成员修改并重交，Buddy 通过；检查时间、操作者和意见记录完整。

## Task 6：进展、评论、成果附件与验收

**Goal:** 支持多条进展、Buddy 评论、多次成果提交及通过/退回。

**GitHub reuse:** Django FileField 和 Tabler 时间线；不引入通用评论或文件管理系统。

**Files:**

- Create: `apps/learning/models/execution.py`
- Create: `apps/learning/views/execution.py`
- Create: `templates/learning/execution_detail.html`
- Create: `apps/learning/tests/test_progress.py`
- Create: `apps/learning/tests/test_evidence.py`
- Create: `apps/learning/tests/test_file_access.py`

- [ ] **Step 1: 写附件越权失败测试**

```python
@pytest.mark.django_db
def test_unrelated_user_cannot_download_evidence(
    unrelated_client, evidence_attachment
):
    response = unrelated_client.get(
        reverse("learning:evidence-download", args=[evidence_attachment.pk])
    )
    assert response.status_code == 404
```

- [ ] **Step 2: 验证测试先失败**

Run: `uv run pytest apps/learning/tests/test_progress.py apps/learning/tests/test_evidence.py apps/learning/tests/test_file_access.py -q`

Expected: FAIL，因为执行和附件模型尚不存在。

- [ ] **Step 3: 实现执行时间线**

ProgressUpdate、GuidanceComment、EvidenceSubmission、EvidenceAttachment 和 ReviewDecision 分别保存事实记录。成果状态为 `working → pending_review → completed`，退回为 `pending_review → changes_requested → pending_review`。文件名随机化，单文件 20 MB，每批最多 5 个。

- [ ] **Step 4: 验证**

Run: `uv run pytest apps/learning/tests/test_progress.py apps/learning/tests/test_evidence.py apps/learning/tests/test_file_access.py -q`

Expected: PASS；附件类型、大小、数量和下载权限均受控。

- [ ] **Step 5: Codex 端到端验收**

成员追加两条进展并提交附件；Buddy 评论、退回、再次验收通过；确认时间线顺序和总实际耗时正确。

## Task 7：管理中心、影响预览与同步

**Goal:** Leader 在线维护能力、材料、账号、Buddy 关系和周期，并安全同步未完成计划。

**GitHub reuse:** Django admin/import-export 用于低频管理；自定义影响预览和同步页面处理业务规则。

**Files:**

- Modify: `apps/learning/admin.py`
- Create: `apps/learning/services/sync.py`
- Create: `apps/learning/views/admin_center.py`
- Create: `templates/learning/admin/capability_tree.html`
- Create: `templates/learning/admin/materials.html`
- Create: `templates/learning/admin/sync_preview.html`
- Modify: `templates/accounts/user_admin.html`
- Create: `apps/learning/tests/test_admin_center.py`
- Create: `apps/learning/tests/test_sync.py`

- [ ] **Step 1: 写同步边界失败测试**

```python
@pytest.mark.django_db
def test_sync_never_changes_completed_or_archived_items(sync_fixture):
    sync_capability(sync_fixture.capability, sync_fixture.selected_active_items)
    sync_fixture.completed_item.refresh_from_db()
    sync_fixture.archived_item.refresh_from_db()
    assert sync_fixture.completed_item.snapshot_name == "old"
    assert sync_fixture.archived_item.snapshot_name == "old"
```

- [ ] **Step 2: 验证测试先失败**

Run: `uv run pytest apps/learning/tests/test_admin_center.py apps/learning/tests/test_sync.py -q`

Expected: FAIL，因为影响预览和同步服务尚不存在。

- [ ] **Step 3: 实现影响预览和同步**

预览列出字段差异和受影响计划项；Leader 显式选择对象与字段。服务拒绝已完成项和归档周期，默认不覆盖成员修改的月份、任务、验收方式和耗时。Buddy 换绑前转交待办。

- [ ] **Step 4: 验证**

Run: `uv run pytest apps/learning/tests/test_admin_center.py apps/learning/tests/test_sync.py apps/accounts/tests -q`

Expected: PASS；停用不破坏历史快照，换绑保留历史关系。

- [ ] **Step 5: Codex 验收**

检查能力树、材料多对多、账号停用、Buddy 转交、归档检查和审计记录。

## Task 8：角色看板、待办与历史周期

**Goal:** 提供成员、Buddy、Leader 三类工作台和可下钻指标。

**GitHub reuse:** Chart.js、Tabler 卡片/时间线；聚合查询由 Django ORM 实现。

**Files:**

- Create: `apps/dashboard/selectors.py`
- Create: `apps/dashboard/views.py`
- Create: `apps/dashboard/urls.py`
- Create: `templates/dashboard/member.html`
- Create: `templates/dashboard/buddy.html`
- Create: `templates/dashboard/leader.html`
- Create: `templates/dashboard/history.html`
- Create: `apps/dashboard/tests/test_metrics.py`
- Create: `apps/dashboard/tests/test_todos.py`
- Create: `apps/dashboard/tests/test_history.py`

- [ ] **Step 1: 写汇总一致性失败测试**

```python
@pytest.mark.django_db
def test_leader_completion_metric_matches_drilldown(leader_client):
    response = leader_client.get(reverse("dashboard:leader"))
    metric = response.context["metrics"]["completed_items"]
    drilldown = response.context["completed_items"]
    assert metric == drilldown.count()
```

- [ ] **Step 2: 验证测试先失败**

Run: `uv run pytest apps/dashboard/tests -q`

Expected: FAIL，因为 selector 和工作台尚不存在。

- [ ] **Step 3: 实现 selector 与角色页面**

指标定义严格使用规格中的查询口径。待办实时读取计划和成果状态，不建立重复通知表。长期无进展阈值为代码常量 30 天，反复退回阈值为 2 次。

- [ ] **Step 4: 验证**

Run: `uv run pytest apps/dashboard/tests -q`

Expected: PASS；所有指标可下钻，归档历史只读。

- [ ] **Step 5: Codex 浏览器验收**

分别检查成员下一步、Buddy 队列和 Leader 风险看板；确认图表无数据时也有明确空状态。

## Task 9：个人/团队 Excel 与邮件模拟日志

**Goal:** 导出个人完整周期和团队汇总 Excel，并记录待发送邮件内容。

**GitHub reuse:** openpyxl 负责固定格式工作簿；Django file email backend 负责模拟邮件。

**Files:**

- Create: `apps/reports/excel.py`
- Create: `apps/reports/views.py`
- Create: `apps/reports/urls.py`
- Create: `apps/reports/tests/test_personal_export.py`
- Create: `apps/reports/tests/test_team_export.py`
- Modify: `apps/accounts/models.py` to add `EmailLog`
- Create: `apps/accounts/tests/test_email_log.py`

- [ ] **Step 1: 写导出失败测试**

```python
@pytest.mark.django_db
def test_personal_export_contains_required_sheets(member_client, active_cycle):
    response = member_client.get(
        reverse("reports:personal", args=[active_cycle.pk])
    )
    workbook = load_workbook(BytesIO(response.content))
    assert workbook.sheetnames == ["自评结果", "年度计划", "执行与验收"]
```

- [ ] **Step 2: 验证测试先失败**

Run: `uv run pytest apps/reports/tests apps/accounts/tests/test_email_log.py -q`

Expected: FAIL，因为导出和 EmailLog 尚不存在。

- [ ] **Step 3: 实现固定格式导出**

个人导出包含自评、计划、执行和验收；团队导出包含成员/Buddy、完成/延期/耗时、能力差距和覆盖明细。字符串清理非法控制字符，日期、耗时和百分比使用明确格式。

- [ ] **Step 4: 实现邮件模拟**

审批、退回、临期和验收事件生成 EmailLog，并通过 Django file backend 写入本地邮件目录；不连接 SMTP。

- [ ] **Step 5: 验证**

Run:

```bash
uv run pytest apps/reports/tests apps/accounts/tests/test_email_log.py -q
uv run python manage.py check
```

Expected: PASS；工作簿可由 openpyxl 重新打开且无 Excel 错误值。

- [ ] **Step 6: Codex 抽查**

比较个人导出和团队导出中的同一成员数据，确认统计一致。

## Task 10：视觉整合、可访问性与设计 QA

**Goal:** 将确认的角色工作台方向落地，并达到桌面端可用性标准。

**GitHub reuse:** 按需引入 Tabler 编译资源和 Chart.js；保留许可证文件。

**Files:**

- Modify: `templates/base.html`
- Modify: `templates/**/*.html`
- Create: `static/vendor/tabler/`
- Create: `static/vendor/chartjs/`
- Create: `static/css/app.css`
- Create: `tests/test_accessibility_smoke.py`
- Create: `THIRD_PARTY_LICENSES.md`

- [ ] **Step 1: 写页面结构失败检查**

```python
@pytest.mark.django_db
def test_member_dashboard_has_single_main_landmark(member_client):
    response = member_client.get(reverse("dashboard:member"))
    html = response.content.decode()
    assert html.count("<main") == 1
    assert 'aria-current="page"' in html
```

- [ ] **Step 2: 验证检查先失败**

Run: `uv run pytest tests/test_accessibility_smoke.py -q`

Expected: FAIL，因为统一页面语义和导航状态尚未完成。

- [ ] **Step 3: 整合 UI**

使用一个主导航、一个主操作、清晰焦点样式、表单 label、错误摘要、空状态和状态文字。颜色不作为唯一状态提示。自评表保留高密度，成员工作台保留年度时间线。

- [ ] **Step 4: 验证**

Run:

```bash
uv run pytest tests/test_accessibility_smoke.py -q
uv run pytest -q
```

Expected: PASS。

- [ ] **Step 5: Codex 设计 QA**

Codex 使用 `design-qa` 对照 `design/context.md` 和规格检查层级、流程、状态、错误、桌面宽度和三类角色页面；修复所有 HIGH 问题后才能进入部署。

## Task 11：Docker、备份恢复与公有云部署

**Goal:** 构建生产镜像，完成 PostgreSQL/附件持久化、健康检查、备份恢复和服务器部署。

**GitHub reuse:** Cookiecutter Django 和 Docker 官方 Django/Compose 模式；数据库使用 `service_healthy`。

**Files:**

- Create: `Dockerfile`
- Create: `compose.yaml`
- Create: `docker/entrypoint.sh`
- Create: `docker/nginx.conf`
- Create: `scripts/backup.sh`
- Create: `scripts/restore.sh`
- Create: `docs/DEPLOYMENT.md`
- Modify: `.env.example`
- Create: `tests/test_production_settings.py`

- [ ] **Step 1: 获取边界确认**

Codex 分别确认：

1. 允许新增 Docker、Nginx、备份脚本和生产配置。
2. 允许连接指定公有云服务器并部署。
3. 服务器 remote、IP、用户和目标目录已明确。

任何一项未确认时，只完成本地构建，不执行远程部署。

- [ ] **Step 2: 写生产配置失败测试**

```python
def test_production_settings_reject_missing_secret_key(monkeypatch):
    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
    with pytest.raises(ImproperlyConfigured):
        importlib.import_module("config.settings.production")
```

- [ ] **Step 3: 验证测试先失败**

Run: `uv run pytest tests/test_production_settings.py -q`

Expected: FAIL，因为生产设置尚未强制秘密配置。

- [ ] **Step 4: 实现容器和健康检查**

Web 使用 Gunicorn；PostgreSQL 使用 `pg_isready`；Web 等待数据库健康。数据库、附件、静态文件、邮件日志和备份目录使用明确卷。Nginx 限制上传大小并代理静态/媒体授权端点。

- [ ] **Step 5: 实现备份恢复**

`backup.sh` 同时打包 `pg_dump` 和附件目录并生成校验和；`restore.sh` 要求空目标库或显式确认变量，校验归档后恢复数据库和附件。

- [ ] **Step 6: 本地验证**

Run:

```bash
docker compose config
docker compose build
docker compose up -d
docker compose exec web python manage.py migrate --check
curl --fail http://127.0.0.1/health/
docker compose exec web pytest -q
```

Expected: 全部退出码为 0，健康检查返回 200。

- [ ] **Step 7: 备份恢复演练**

在测试数据上执行备份，清空独立测试环境，恢复后比较用户数、能力项数、计划项数和附件 SHA-256。

- [ ] **Step 8: 远程部署**

仅在 Step 1 全部确认后执行。没有域名和 HTTPS 时只部署测试数据，并在登录页显示“验收环境，禁止录入真实数据”。

- [ ] **Step 9: Codex 生产验收**

Codex检查容器健康、迁移、静态资源、附件权限、日志、备份文件权限和重启后数据持久性。

## Task 12：最终回归与交付

**Goal:** 证明规格中的权限、流程、数据和部署要求全部满足。

**Files:**

- Create: `tests/test_member_journey.py`
- Create: `tests/test_buddy_journey.py`
- Create: `tests/test_leader_journey.py`
- Create: `docs/ACCEPTANCE.md`
- Create: `README.md`

- [ ] **Step 1: 建立三条端到端失败测试**

成员旅程覆盖自评、计划和成果提交；Buddy 旅程覆盖审批、退回和验收；Leader 旅程覆盖管理、看板下钻和归档。

- [ ] **Step 2: 运行并记录首次失败**

Run: `uv run pytest tests/test_member_journey.py tests/test_buddy_journey.py tests/test_leader_journey.py -q`

Expected: 若存在未闭环路径则 FAIL，并准确指出缺失状态或页面。

- [ ] **Step 3: 仅修复验收缺口**

不得在最终回归阶段增加规格外功能；每个修复必须对应失败的验收测试。

- [ ] **Step 4: 全量验证**

Run:

```bash
uv run pytest -q
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
docker compose config
docker compose build
git status --short
```

Expected: 测试、检查和构建全部通过；没有未生成迁移；Git 状态只包含本项目预期文件。

- [ ] **Step 5: Codex 最终审查**

Codex核对规格 16 节、GitHub 复用记录、第三方许可证、diff 范围、测试结果、部署状态和未完成外部前置条件。

- [ ] **Step 6: 提交与推送门**

确认项目独立 Git remote 与目标仓库匹配后，Codex提交。除非用户明确要求且 remote 已核对，不执行 push。

## 阶段提交建议

Claude Code 不提交。独立仓库和 remote 确认后，Codex 在每个 Task 验证通过后使用以下提交粒度：

```text
chore: bootstrap team learning plan app
feat: add roles and mentorships
feat: import capability catalog
feat: add learning cycles and assessments
feat: add plan approval workflow
feat: add progress and evidence review
feat: add leader administration
feat: add role dashboards
feat: add Excel reports and email logs
feat: integrate dashboard UI
chore: add production deployment
test: cover end-to-end learning journeys
```
