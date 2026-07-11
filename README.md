# Team Learn Plan

团队年度学习计划 web 系统。用于维护成员能力模型、学习主题、进度跟踪与历史记录。

## Local setup

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --group dev
```

## Run tests

```bash
uv run pytest -q
```

Run only the journey tests:

```bash
uv run pytest tests/test_member_journey.py tests/test_buddy_journey.py tests/test_leader_journey.py -q
```

## Run Django locally

```bash
uv run python manage.py migrate
uv run python manage.py runserver
```

The local settings module is `config.settings.local`.

## Local Docker deployment

Copy the example environment file and start the stack:

```bash
cp .env.example .env
docker compose up --build -d
```

The compose stack includes PostgreSQL, the Django web service, and nginx. Access the app at http://localhost/.

- `web` waits for the database healthcheck, then runs `collectstatic` and `migrate`.
- `nginx` proxies to `web:8000`, serves static/media files, and limits uploads to 20 MB.

Stop the stack:

```bash
docker compose down
```

Remove volumes as well:

```bash
docker compose down -v
```

## Backup and restore

- `scripts/backup.sh` dumps the database and archives `media/` and `emails/` to `./backups/`.
- `scripts/restore.sh` restores from a backup after checksum verification.

See `docs/DEPLOYMENT.md` for details.

## Documentation

- [使用手册](docs/USAGE.md)
- [部署手册](docs/DEPLOYMENT.md)
- [架构与方案](docs/ARCHITECTURE.md)
- [验收记录](docs/ACCEPTANCE.md)

## Current limitations

Public HTTPS with a trusted certificate requires a custom domain and DNS configuration. The current production setup uses a self-signed certificate and exposes HTTPS via Docker Compose; replace the certificate in `/opt/team_learn_plan_ssl/` when a domain is available.
