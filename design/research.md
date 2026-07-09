# GitHub Module Research

## Research goal

按功能模块寻找成熟、持续维护且许可证清晰的开源项目，以“拼积木”方式组装系统；不寻找或 Fork 一个业务完全相同的 HRMS/LMS。

调研日期：2026-07-09。

## Selection rules

- 许可证允许当前项目使用和修改。
- 近期仍有维护活动，或基础能力足够稳定。
- 与 Django 单体架构兼容。
- 复用收益高于引入、升级和安全维护成本。
- 仅引入 V1 实际需要的模块。

## Selected modules

### Project foundation

- Candidate: Cookiecutter Django
- Source: https://github.com/cookiecutter/cookiecutter-django
- License: BSD-3-Clause
- Reuse: Docker、PostgreSQL、环境变量、生产/开发配置、测试和安全默认值。
- Constraint: 生成时关闭 Celery、REST API、云存储和真实邮件服务等非必要功能。

### UI foundation

- Candidate: Tabler
- Source: https://github.com/tabler/tabler
- License: MIT
- Reuse: 页面框架、导航、卡片、表格、表单、状态徽标和时间线。
- Constraint: 只引入实际使用的编译资源和组件，不复制完整示例站点。

### Workflow state management

- Candidate: django-fsm-2
- Source: https://github.com/django-commons/django-fsm-2
- License: MIT
- Reuse: 计划审批、成果验收和周期归档的受控状态转换、权限检查和并发保护。
- Constraint: 流程定义固定在代码中；V1 不建设可配置工作流引擎。

### Tables and filters

- Candidate: django-tables2
- Source: https://github.com/jieter/django-tables2
- Reuse: 分页、排序和表格渲染。
- Candidate: django-filter
- Source: https://github.com/carltongibson/django-filter
- Reuse: 能力项、计划、任务和管理列表的组合筛选。
- Constraint: 自评编辑仍使用本项目表单，不把核心业务写进通用表格组件。

### Audit history

- Candidate: django-simple-history
- Source: https://github.com/django-commons/django-simple-history
- License: BSD-3-Clause
- Reuse: 能力模型、计划、进展、验收和关键管理对象的变更历史。
- Constraint: 业务事件仍保留独立时间线记录，审计表不直接作为用户界面数据源。

### Import and export

- Candidate: django-import-export
- Source: https://github.com/django-import-export/django-import-export
- License: BSD-2-Clause
- Reuse: Leader 管理后台的基础数据导入导出。
- Candidate: openpyxl
- Reuse: 解析现有 Excel 模板，以及生成具有固定字段和格式的个人、团队 Excel。
- Constraint: 模板初始化和业务报表使用显式映射与校验，不依赖通用模型导出。

### Charts

- Candidate: Chart.js
- Source: https://github.com/chartjs/Chart.js
- License: MIT
- Reuse: 完成趋势、能力差距和能力域覆盖图。
- Constraint: 图表仅消费服务端聚合结果，不引入独立 BI 层。

## Native Django capabilities

以下需求使用 Django 原生能力，避免增加依赖：

- 账号密码、Groups 和 Permissions。
- 表单、CSRF、防越权查询和文件下载授权。
- FileField 和服务器持久化目录。
- 邮件文件后端和发送日志。
- Buddy 评论、进展、成果提交和站内待办业务模型。

## Rejected foundations

- Horilla HR: https://github.com/horilla/horilla-hr
  - Django 技术栈接近，但完整 HRMS 带来大量无关模块，且 LGPL-2.1 代码复用需要额外许可证管理。
- Frappe HR: https://github.com/frappe/hrms
  - 目标、绩效和审批能力成熟，但依赖 Frappe/ERPNext，GPL-3.0，部署和二次开发成本过高。
- SkillTree: https://github.com/NationalSecurityAgency/skills-service
  - Apache-2.0 且维护成熟，但定位是游戏化微学习，与年度能力计划和 Buddy 流程差距较大。
- Sema Developer Skills Matrix: https://github.com/Semalab/developer-skills-matrix
  - 可参考能力数据结构，但项目规模小且采用 AGPL-3.0，不作为代码底座。
- OpenGamifyLMS: https://github.com/puskunalis/opengamifylms
  - 课程、测验和游戏化功能不在 V1 范围，项目成熟度不足。

## Reuse gate for implementation

每个开发阶段开始前记录：

1. 当前功能是否已有选定组件。
2. 候选组件的许可证、维护状态和安全风险。
3. 复用的具体文件、API 或交互模式。
4. 未采用候选的原因。
5. 升级和替换边界。
