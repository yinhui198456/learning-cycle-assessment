# Task 3 handoff: capability catalog and Excel import

## Goal

Implement the base-data layer for the learning-plan application and a safe,
one-time initializer for the supplied Excel template:

`/opt/personal-agent-workspace/团队成员年度学习计划模板_基于能力模型_V1.3.xlsx`

The workbook is input only. Never save or modify it.

## Repository and branch

- Project root:
  `/opt/personal-agent-workspace/team_learn_plan/.worktrees/task-3-catalog`
- Branch: `feat/capability-catalog`
- Baseline: Task 2, commit `d2f956a`
- No remote and no push.

## Allowed changes

- `pyproject.toml`
- `uv.lock`
- `config/settings/base.py`
- `apps/learning/**`
- this handoff document

Do not change accounts, existing templates, existing migrations, design files,
or the source workbook.

## Required model

Keep the schema direct and Django-native:

- `CapabilityCategory`
  - unique `name`
  - `sort_order`
  - `is_active`
- `CapabilityDomain`
  - `category` with `PROTECT`
  - nullable self-referencing `parent` with `PROTECT`
  - unique `code`
  - `name`
  - `level` restricted to 1 or 2
  - `sort_order`
  - `is_active`
- `LearningMaterial`
  - unique `code`
  - `name`, `material_type`, `source`, `description`, `status`
  - `is_active`
- `CapabilityItem`
  - `domain` with `PROTECT`
  - unique `code`
  - `name`
  - `suggested_level`
  - raw `material_reference` text, preserving indexed codes and free text
  - `acceptance_method`
  - `estimated_hours` as text because the workbook contains ranges
  - `recommended_action`
  - `sort_order`
  - `is_active`
  - many-to-many `materials` through `CapabilityMaterial`
- `CapabilityMaterial`
  - item FK with `CASCADE`
  - material FK with `PROTECT`
  - `sort_order`
  - unique item/material pair

Add sensible ordering, string representations, database constraints, an
initial migration, and minimal Django admin registration. Avoid speculative
repositories, DTOs, abstract service layers, or import frameworks.

## Workbook contract

Use `openpyxl` in `read_only=True` and `data_only=True` mode.

Required sheets:

- `02_能力差距自评`
- `06_学习材料索引`

Known V1.3 source facts that tests and validation should cover:

- 2 capability categories
- 6 first-level domains
- 47 second-level domains
- 310 third-level capability items
- 95 indexed learning materials
- all item and material codes are unique

Read the exact headers from the workbook and validate them explicitly. Normalize
cell values by trimming surrounding whitespace, but do not silently invent
required values.

Material-reference cells use `、` and can contain both material codes and
unindexed internal references, for example:

- `C01-M002、内部部署文档模板`
- `C01-M007、C01-M008、内部图示样例`

Only tokens matching `^[PC]\d{2}-M\d{3}$` are indexed-material links. Preserve
the complete source cell in `CapabilityItem.material_reference`. Nonmatching
tokens are valid free text and must not fail import. A code-shaped token that
does not exist in the material sheet must fail validation.

Validate hierarchy consistency:

- one code cannot map to conflicting names/categories/parents
- a level-2 domain belongs to the row's level-1 domain
- an item belongs to the row's level-2 domain

## Import API and command

Provide a small parser/service that can be tested without writing to the
database. Return a structured result or raise a clear domain-specific
validation exception.

Management command:

```bash
uv run python manage.py import_learning_template PATH
uv run python manage.py import_learning_template PATH --apply
```

Requirements:

- dry-run is the default and performs no database writes
- dry-run prints a concise count summary
- `--apply` parses and validates everything before writing
- apply is wrapped in `transaction.atomic`
- apply refuses to run when any learning catalog records already exist; this
  is an initializer, not a synchronizer
- any error leaves the database unchanged
- successful apply prints the imported counts

## TDD sequence

1. Write failing model tests for relationships, uniqueness, constraints, and
   deletion protection.
2. Implement models/migration/admin minimally.
3. Write failing parser tests using small temporary workbooks, including mixed
   material references, missing sheets/headers, duplicate/conflicting codes,
   hierarchy mismatch, and unknown code-shaped material references.
4. Implement parser.
5. Write failing command tests for dry-run, apply, refusal on populated data,
   and rollback.
6. Implement command/apply path.
7. Add one integration test against the supplied V1.3 workbook, asserting the
   known counts. It must read only; database writes are allowed only inside the
   isolated test database.

## Dependencies and checks

Add stable `openpyxl` (3.1.x) through `uv`, keeping the lockfile synchronized.

Run:

```bash
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py check
uv run python manage.py test
uv run python manage.py import_learning_template \
  /opt/personal-agent-workspace/团队成员年度学习计划模板_基于能力模型_V1.3.xlsx
git diff --check
git status --short
```

Do not commit, merge, push, or modify files outside the allowed list. Report
test evidence and any deliberate deviations.

## Task result

- Status: completed.
- Changed files: `pyproject.toml`, `uv.lock`, `config/settings/base.py`,
  `apps/learning/**` (models, migrations, admin, parser, management command,
  tests), and this handoff document.
- Source workbook was read only; no modifications.
- Verification:
  - `uv run python manage.py makemigrations --check --dry-run` → no changes.
  - `uv run python manage.py check` → no issues.
  - `uv run python manage.py test` → 39 tests OK.
  - `uv run python -m pytest` → 80 tests passed.
  - Dry-run against the V1.3 workbook → 2 categories, 53 domains, 310 items,
    95 materials.
  - Isolated test-database apply → 396 capability-material links.
  - `git diff --check` → clean.
- Source workbook used: the tracked project-root copy
  `团队成员年度学习计划模板_基于能力模型_V1.3.xlsx`; it remained unchanged.
