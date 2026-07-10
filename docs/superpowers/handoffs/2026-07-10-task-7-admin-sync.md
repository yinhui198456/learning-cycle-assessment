# Task 7 handoff: admin center and catalog sync

## Goal

Give Leader a minimal web management center for capability/material maintenance and safe catalog-to-plan synchronization.

## Ponytail decisions

- Use existing Django views/forms/admin; do not add `django-import-export`.
- Keep services flat as `services_sync.py`; do not restructure the app.
- Sync only explicitly selected snapshot fields. Default fields exclude member-editable task/month/acceptance/hours.

## Rules

- Leader-only pages.
- Capability/material edits use existing models.
- Sync preview lists only unfinished plan items in active cycles.
- Sync never changes completed plan items or items in archived cycles.
- Sync default does not overwrite member-edited task, acceptance method, estimated hours, planned month, or actual hours.

## Verification

```bash
uv run pytest apps/learning/tests/test_admin_center.py apps/learning/tests/test_sync.py -q
uv run python -m pytest -q
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py check
git diff --check
```
