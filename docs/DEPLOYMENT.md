# Local Deployment

This guide covers local deployment only. Remote or cloud deployment is out of scope until separately confirmed.

## Requirements

- Docker Engine
- docker compose

> Note: `docker compose` is unavailable in the current Codex environment, so runtime validation of these commands may be blocked.

## Environment Variables

Copy `.env.example` to `.env` and update the values:

```bash
cp .env.example .env
```

Required variables for the `web` service:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Production secret key. Must be long and random. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated list of allowed hosts, e.g. `localhost,127.0.0.1`. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated list of trusted origins, e.g. `http://localhost`. |
| `DJANGO_SECURE_SSL_REDIRECT` | Set to `false` for local plain-HTTP deployments; defaults to `true`. |
| `DJANGO_SESSION_COOKIE_SECURE` | Set to `false` for local plain-HTTP deployments; use `true` behind HTTPS. |
| `DJANGO_CSRF_COOKIE_SECURE` | Set to `false` for local plain-HTTP deployments; use `true` behind HTTPS. |
| `DATABASE_URL` | PostgreSQL connection string. The compose file overrides this to point at the `db` service. |

## Run the Stack

```bash
docker compose up --build -d
```

The `web` service waits for the database healthcheck to pass before starting, then runs `collectstatic` and `migrate` via the entrypoint.

Access the application at http://localhost/.

The `nginx` service proxies requests to `web:8000`, serves `/static/` and `/media/`, and limits upload body size to 20 MB.

## Stop the Stack

```bash
docker compose down
```

To remove named volumes as well:

```bash
docker compose down -v
```

## Backup

The backup script dumps the database, archives the `media` and `emails` directories if present, and writes a SHA-256 checksum.

```bash
# From inside the web container or a local environment with DATABASE_URL set.
sh scripts/backup.sh
```

Outputs are written to `./backups/` by default (override with `BACKUPS_DIR`).

## Restore

Restore requires explicit confirmation and a verified checksum.

```bash
CONFIRM_RESTORE=yes sh scripts/restore.sh \
    backups/db_YYYYMMDD_HHMMSS.sql \
    backups/assets_YYYYMMDD_HHMMSS.tar.gz \
    backups/sha256_YYYYMMDD_HHMMSS.txt
```

This restores the database with `psql` and extracts the media/emails archive.
