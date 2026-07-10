#!/bin/sh
set -eu

: "${CONFIRM_RESTORE:?CONFIRM_RESTORE must be set to yes}"
[ "$CONFIRM_RESTORE" = "yes" ] || { echo "CONFIRM_RESTORE must be yes" >&2; exit 1; }

: "${DATABASE_URL:?DATABASE_URL must be set}"

[ "$#" -ge 3 ] || {
    echo "Usage: $0 <db_dump_file> <assets_archive> <checksum_file>" >&2
    exit 1
}

DB_FILE="$1"
ASSETS_ARCHIVE="$2"
CHECKSUM_FILE="$3"

[ -f "$DB_FILE" ] || { echo "Database dump not found: $DB_FILE" >&2; exit 1; }
[ -f "$ASSETS_ARCHIVE" ] || { echo "Assets archive not found: $ASSETS_ARCHIVE" >&2; exit 1; }
[ -f "$CHECKSUM_FILE" ] || { echo "Checksum file not found: $CHECKSUM_FILE" >&2; exit 1; }

sha256sum -c "$CHECKSUM_FILE" || { echo "Checksum verification failed" >&2; exit 1; }

psql "$DATABASE_URL" < "$DB_FILE"
tar -xzf "$ASSETS_ARCHIVE"

echo "Restore completed."
