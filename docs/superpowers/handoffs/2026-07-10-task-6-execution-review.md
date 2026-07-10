# Task 6 handoff: execution tracking and evidence review

## Goal

Complete the minimum execution loop after Buddy approval:

- Member appends progress updates with actual hours.
- Current Buddy adds guidance comments.
- Member submits evidence with optional link and attachments.
- Current Buddy requests changes or marks evidence completed.
- Evidence attachments are downloadable only by authorized users.

## Ponytail decisions

- Use Django `FileField` and `FileResponse`; no file-management dependency.
- Store execution status on `PlanItem`; facts stay in small append-only tables.
- Keep upload validation in services: max 5 files per submission, 20 MB per file, small allowlist of content types.

## Allowed files

- Modify: `apps/learning/models.py`
- Modify: `apps/learning/admin.py`
- Modify: `apps/learning/urls.py`
- Modify: `apps/learning/views.py`
- Create: `apps/learning/services_execution.py`
- Create: `apps/learning/migrations/0004_*.py`
- Create: `templates/learning/execution_detail.html`
- Create: `apps/learning/tests/test_progress.py`
- Create: `apps/learning/tests/test_evidence.py`
- Create: `apps/learning/tests/test_file_access.py`

Do not add dependencies or touch other first-level projects.

## Rules

- Only the plan member can add progress and submit evidence.
- Only the current Buddy can add guidance and review evidence.
- Evidence submission allowed from `working` or `changes_requested`.
- Evidence status flow on `PlanItem`: `working -> pending_review -> completed` or `pending_review -> changes_requested -> pending_review`.
- Request changes requires a non-empty comment.
- Completed items cannot accept more evidence or progress.
- Attachment download returns 404 for unrelated users.

## Verification

```bash
uv run pytest apps/learning/tests/test_progress.py apps/learning/tests/test_evidence.py apps/learning/tests/test_file_access.py -q
uv run python -m pytest -q
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py check
git diff --check
```
