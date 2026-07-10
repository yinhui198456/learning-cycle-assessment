# Task 5 handoff: plan generation and Buddy approval

## Goal

Build the minimum production flow after self-assessment:

- Member generates a learning plan from `Assessment.included=True`.
- The plan snapshots capability/material fields so later catalog edits do not rewrite already generated plans.
- Member submits the plan to the current Buddy.
- Current Buddy can approve or request changes.
- Member can edit returned draft fields and resubmit.

## Ponytail decisions

- Do not add `django-fsm-2`: four states fit a `CharField` plus service functions.
- Do not add `django-simple-history`: an explicit approval event table covers Task 5 audit needs.
- Keep files flat under `apps/learning/`; do not split `models.py` into a package in this task.

## Allowed files

- Modify: `apps/learning/models.py`
- Modify: `apps/learning/admin.py`
- Modify: `apps/learning/urls.py`
- Modify: `apps/learning/views.py`
- Modify: `templates/base.html` only if a minimal navigation entry is needed
- Create: `apps/learning/services_planning.py`
- Create: `apps/learning/migrations/0003_*.py`
- Create: `templates/learning/plan_detail.html`
- Create: `templates/learning/buddy_approvals.html`
- Create: `apps/learning/tests/test_plan_generation.py`
- Create: `apps/learning/tests/test_plan_approval.py`

Do not modify accounts behavior, capability import code, dependencies, deployment files, or other first-level projects.

## Core rules

- `LearningPlan` is unique per member/cycle.
- `generate_plan()` uses only included assessments for that member/cycle.
- Generation requires an active Buddy relationship for the member.
- A generated plan starts as `draft`.
- Status flow:
  - `draft -> pending_approval`
  - `changes_requested -> pending_approval`
  - `pending_approval -> changes_requested`
  - `pending_approval -> active`
- A pending or active plan cannot be edited by the member.
- A returned plan can be edited and resubmitted.
- Only the current Buddy can approve or request changes.
- Request changes requires a non-empty comment.
- Repeated submit/approve/request-change actions must fail.

## Verification

```bash
uv run pytest apps/learning/tests/test_plan_generation.py apps/learning/tests/test_plan_approval.py -q
uv run python -m pytest -q
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py check
git diff --check
```
