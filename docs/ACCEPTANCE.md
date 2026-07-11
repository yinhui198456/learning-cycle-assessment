# Acceptance Evidence

## Current status

- Core member / Buddy / Leader learning journeys are implemented.
- UIUX blocker/high issues from the 2026-07-10 audit are fixed.
- Medium/low UI affordance fixes have been applied.
- Local Docker Compose deployment has been built and health-checked.
- Remote server deployment, domain, and public HTTPS remain out of scope until separately confirmed.

## Verification commands

| Command | Status |
| --- | --- |
| `uv run pytest tests/test_member_journey.py tests/test_buddy_journey.py tests/test_leader_journey.py -q` | `3 passed` |
| `uv run pytest -q` | `216 passed in 71.20s` |
| `uv run python manage.py check` | `System check identified no issues (0 silenced).` |
| `uv run python manage.py makemigrations --check --dry-run` | `No changes detected` |
| `docker compose config --quiet` | passed |
| `docker compose up --build -d` | passed using `.env.example` values for local HTTP |
| `curl -fsS -i http://127.0.0.1:8080/health/` | `HTTP/1.1 200 OK`, `{"status": "ok"}` |
| `docker compose exec -T web sh scripts/backup.sh` | backup created under `./backups/` in the web container volume |

## UIUX regression

Full browser regression reused the four Playwright audit suites against the local Compose nginx endpoint:

| Suite | Status |
| --- | --- |
| Member journey | `2 passed` |
| Buddy journey | `4 passed` |
| Leader/admin journey | `2 passed` |
| Visual/accessibility smoke | `9 passed` |

Logs are stored under `output/uiux-regression-20260711/`.

## Notes

- Local plain-HTTP Compose deployments must set these flags to `false`: `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SESSION_COOKIE_SECURE`, and `DJANGO_CSRF_COOKIE_SECURE`. `.env.example` is configured this way.
- HTTPS deployment should set those flags back to `true` and provide trusted origins for the deployed host.
- Restore was not executed because it intentionally mutates the database. The restore script performs checksum verification before applying a dump.
- Test artifacts are intentionally kept under `output/`, which is gitignored.
