# Task 2 Handoff — Roles, Mentorships, and Role Workbenches

## Project root

`/opt/personal-agent-workspace/team_learn_plan/.worktrees/task-2-roles`

Branch: `feat/roles-mentorships`

## Goal

Add member, Buddy, and Leader roles using Django Groups; add one active Buddy relationship per member with history; show role-scoped workbench data; deny direct access to Leader-only pages.

## Read first

- `docs/superpowers/specs/2026-07-09-team-learning-plan-web-design.md`
- `docs/superpowers/plans/2026-07-09-team-learning-plan-web.md`, Task 2 only
- `apps/accounts/**`
- `templates/base.html`

## Reuse decision

- Use Django's built-in `Group`, `PermissionsMixin`, class-based views, ORM constraints, and `transaction.atomic`.
- Do not add django-guardian, django-rules, a custom permission backend, middleware, signals, or a role field on `User`.
- Use a migration to create the three fixed groups: `member`, `buddy`, `leader`.

## Allowed files

- Modify: `apps/accounts/models.py`
- Modify: `apps/accounts/admin.py`
- Modify: `apps/accounts/views.py`
- Modify: `apps/accounts/urls.py`
- Create: `apps/accounts/services.py`
- Create: `apps/accounts/migrations/0002_*.py`
- Create: `apps/accounts/tests/test_roles.py`
- Create: `apps/accounts/tests/test_mentorship.py`
- Create: `templates/accounts/home.html`
- Create: `templates/accounts/user_admin.html`
- Modify: `templates/base.html` only if required to turn it into a layout extended by the new pages

## Forbidden files and actions

- Do not modify settings, dependencies, lockfiles, deployment files, design documents, plans, other handoffs, or the Excel template.
- Do not create a role model, generic repository layer, custom auth backend, API, SPA, form framework, or JavaScript.
- Do not implement account creation/editing, password reset administration, task transfer, or Buddy reassignment UI; those belong to Task 7.
- Do not modify shared or production data. Test database writes are allowed.
- Do not commit, merge, or push.
- Do not use sudo or modify Git/Claude global configuration.

## Required model

Add `Mentorship` with:

- `member`: `ForeignKey(User)`, related name `mentorships_as_member`.
- `buddy`: `ForeignKey(User)`, related name `mentorships_as_buddy`.
- `started_at`: date, default `timezone.localdate`.
- `ended_at`: nullable date.
- `created_at`: auto timestamp.

Database constraints:

- one active row (`ended_at IS NULL`) per member;
- member and Buddy cannot be the same user;
- `ended_at` is null or not earlier than `started_at`.

Do not delete historical relationships.

## Required services

Implement the minimum functions:

- `has_role(user, role_name) -> bool`
- `primary_role(user) -> str | None`, precedence `leader`, `buddy`, `member`
- `visible_members_for(user) -> QuerySet[User]`
  - Leader: active users in `member`
  - Buddy: active currently bound members
  - Member: only self
  - no role: empty queryset
- `assign_buddy(member, buddy) -> Mentorship`
  - requires active users;
  - requires member/buddy groups;
  - rejects same user;
  - rejects a second active relationship;
  - executes atomically.

Do not implement automatic replacement of an existing Buddy in Task 2.

## Required views

- Replace the placeholder home view with a role-aware workbench.
- Context contains `role` and `members` from the services above.
- Render `templates/accounts/home.html`, which extends `base.html`.
- Add a Leader-only read-only user administration page at `/accounts/users/`.
- Anonymous users redirect to login.
- Authenticated non-Leaders receive HTTP 403 from the Leader-only URL.

## TDD sequence

1. Write the database-constraint tests first.
2. Run them and capture failure because `Mentorship` does not exist.
3. Implement only the model/migration required to pass.
4. Write service visibility/assignment tests.
5. Run and capture failures because services do not exist.
6. Implement services.
7. Write workbench and Leader-only URL tests.
8. Run and capture failures because views/templates/URLs do not exist.
9. Implement views/templates/URLs.
10. Run the full suite.

## Minimum tests

### Mentorship

- migration creates all three groups;
- active relationship is unique per member;
- same user cannot be member and Buddy;
- end date cannot precede start date;
- ended relationship remains queryable as history;
- `assign_buddy` rejects wrong roles, inactive users, and duplicate active assignment.

### Visibility

- member sees only self;
- Buddy sees current bound member and not unrelated or ended members;
- Leader sees active members;
- user without role sees none.

### Views

- each role gets the expected workbench context;
- Leader-only user page returns 200 to Leader;
- direct access returns 403 to member and Buddy;
- anonymous access redirects to login;
- all pages render without template errors.

## Required commands

```bash
uv sync
uv run pytest apps/accounts/tests/test_mentorship.py -q
uv run pytest apps/accounts/tests/test_roles.py -q
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate
uv run pytest -q
uv run python manage.py check
git status --short
```

## Acceptance criteria

- Three Django Groups exist after migration.
- The database enforces valid mentorship history and one active Buddy per member.
- Services enforce user activity and role rules.
- Role-scoped queryset behavior is covered by tests.
- Leader-only URL is protected server-side.
- Existing Task 1 authentication tests remain green.
- No new dependency or forbidden file is added.
- No commit or push occurs.

## Stop conditions

Stop and report if:

- SQLite cannot enforce the chosen constraints consistently with PostgreSQL;
- implementing the task requires settings, dependencies, scripts, production data, or files outside the allowlist;
- migration conflicts with the existing initial migration;
- a required command fails for an environmental reason after one diagnosis attempt.

## Result

Report:

- status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`;
- changed files;
- each RED command and expected failure;
- GREEN verification output;
- skipped criteria or concerns;
- confirmation that no commit was made.

## Execution result

Status: `DONE`

Observed RED:

```text
test_mentorship.py:
ImportError: cannot import name 'Mentorship' from 'apps.accounts.models'

test_roles.py:
ModuleNotFoundError: No module named 'apps.accounts.services'

view tests:
KeyError: 'role'
NoReverseMatch: Reverse for 'user_admin' not found

history protection:
Failed: DID NOT RAISE ProtectedError

concurrent assignment boundary:
IntegrityError: simulated unique violation
```

Verified GREEN:

```text
$ uv run pytest apps/accounts/tests/test_mentorship.py -q
13 passed

$ uv run pytest apps/accounts/tests/test_roles.py -q
17 passed

$ uv run python manage.py makemigrations --check --dry-run
No changes detected

$ uv run python manage.py migrate
No migrations to apply

$ uv run pytest -q
41 passed

$ uv run python manage.py check
System check identified no issues (0 silenced)
```

No commit, merge, or push was performed by Claude Code.
