# Task 1 Handoff — Django Bootstrap and Login

## Project root

`/opt/personal-agent-workspace/team_learn_plan`

## Goal

Create the smallest Django 5.2 LTS application that can start, run tests, redirect anonymous users to login, authenticate a local user, and pass Django system checks.

## Read first

- `AGENTS.md` from the workspace instructions provided by Codex.
- `docs/superpowers/specs/2026-07-09-team-learning-plan-web-design.md`
- `docs/superpowers/plans/2026-07-09-team-learning-plan-web.md`, Task 1 only.
- `design/research.md`, project foundation section only.

## Required reuse decision

- Follow Cookiecutter Django patterns for split settings, environment variables, custom user model, tests, and secure production defaults.
- Do not generate or add allauth, Celery, Redis, REST API, SPA tooling, cloud storage, Sentry, or external email providers.
- Use Django Groups later; Task 1 does not implement roles.

## Allowed files

- `pyproject.toml`
- `uv.lock`
- `manage.py`
- `config/__init__.py`
- `config/settings/__init__.py`
- `config/settings/base.py`
- `config/settings/local.py`
- `config/settings/production.py`
- `config/urls.py`
- `config/wsgi.py`
- `apps/__init__.py`
- `apps/accounts/__init__.py`
- `apps/accounts/apps.py`
- `apps/accounts/models.py`
- `apps/accounts/admin.py`
- `apps/accounts/views.py`
- `apps/accounts/urls.py`
- `apps/accounts/migrations/**`
- `apps/accounts/tests/**`
- `templates/base.html`
- `templates/registration/login.html`
- `.env.example`
- `.gitignore`
- `pytest.ini`

## Forbidden files and actions

- Do not modify the Excel file.
- Do not modify `design/**`, `docs/**`, or files outside this project.
- Do not add Docker, Nginx, deployment scripts, business models, role logic, dashboards, imports, or exports.
- Do not commit or push.
- Do not use sudo.
- Do not modify global Git or Claude settings.

## TDD sequence

1. Create only the dependency/test plumbing required to run pytest.
2. Write `test_anonymous_user_is_redirected_to_login`.
3. Run the exact test and confirm it fails because `home` or its protected view is missing.
4. Implement the minimum project, custom user, protected home view, login URL and templates.
5. Run the focused test and confirm it passes.
6. Add only the minimal login success and production-settings tests needed for Task 1; observe each fail before implementing its behavior.

## Implementation notes

- Use Python 3.13-compatible dependencies.
- Pin Django to the current 5.2 patch line, not Django 6.
- Set `AUTH_USER_MODEL = "accounts.User"` before the first migration.
- Local settings may use SQLite for fast tests and local execution.
- Production settings must require `DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS`, and `DJANGO_CSRF_TRUSTED_ORIGINS`.
- Use Django's file email backend in base/local settings; do not create an email log model in Task 1.
- `home` may render a minimal placeholder in `templates/base.html`; visual design belongs to Task 10.
- Prefer `uv` and pytest/pytest-django. Do not add a second package manager.

## Required commands

```bash
uv sync
uv run pytest apps/accounts/tests/test_auth.py -q
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate
uv run pytest -q
uv run python manage.py check
```

## Acceptance criteria

- Anonymous `GET /` redirects to the login page.
- A valid local user can log in and reach `/`.
- Invalid credentials remain on the login page with a form error.
- Custom `accounts.User` is active before the first migration.
- Production settings fail closed when mandatory environment variables are absent.
- All tests pass with no warnings caused by project code.
- `makemigrations --check --dry-run` reports no pending changes.
- `python manage.py check` reports no issues.
- Only allowed files changed.

## Stop conditions

Stop and report instead of proceeding if:

- package installation requires sudo;
- authentication or network access blocks dependency resolution;
- the task requires Docker, scripts, data writes, or changes outside allowed files;
- existing files conflict with this handoff;
- a required command fails for an environmental reason after one diagnosis attempt.

## Result

Claude Code must report:

- status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`;
- files changed;
- RED test command and expected failure;
- GREEN verification commands and results;
- any skipped acceptance criterion;
- no commit performed.

## Execution result

Status: `DONE`

### Observed RED

Initial protected-home test:

```text
$ uv run pytest apps/accounts/tests/test_auth.py -q
ImportError: No module named 'config'
pytest-django could not find a Django project (no manage.py file could be found)
```

The test runner and test existed before the Django project skeleton; the failure was caused by the missing project and protected home route.

Login redirect regression test:

```text
assert 'name="next"' in content
AssertionError
```

Production database boundary test:

```text
Failed: DID NOT RAISE ImproperlyConfigured
```

Production secure-default test:

```text
AttributeError: module 'config.settings.production' has no attribute 'SECURE_SSL_REDIRECT'
```

Each failure was observed by Claude Code before the corresponding implementation change.

### Verified GREEN

```text
$ uv sync
Resolved 14 packages

$ uv run pytest apps/accounts/tests/test_auth.py -q
11 passed

$ uv run python manage.py makemigrations --check --dry-run
No changes detected

$ uv run python manage.py migrate
No migrations to apply

$ uv run pytest -q
11 passed

$ uv run python manage.py check
System check identified no issues (0 silenced)
```

No commit or push was performed by Claude Code.
