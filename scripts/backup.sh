#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL must be set}"

BACKUPS_DIR="${BACKUPS_DIR:-./backups}"
MEDIA_DIR="${MEDIA_DIR:-./media}"
EMAILS_DIR="${EMAILS_DIR:-./emails}"

mkdir -p "$BACKUPS_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_FILE="$BACKUPS_DIR/db_$TIMESTAMP.sql"
ASSETS_FILE="$BACKUPS_DIR/assets_$TIMESTAMP.tar.gz"
CHECKSUM_FILE="$BACKUPS_DIR/sha256_$TIMESTAMP.txt"

pg_dump "$DATABASE_URL" > "$DB_FILE"

ASSETS_TAR_ARGS=""
[ -d "$MEDIA_DIR" ] && ASSETS_TAR_ARGS="$ASSETS_TAR_ARGS $MEDIA_DIR"
[ -d "$EMAILS_DIR" ] && ASSETS_TAR_ARGS="$ASSETS_TAR_ARGS $EMAILS_DIR"

if [ -n "$ASSETS_TAR_ARGS" ]; then
    tar -czf "$ASSETS_FILE" $ASSETS_TAR_ARGS
else
    tar -czf "$ASSETS_FILE" --files-from /dev/null
fi

sha256sum "$DB_FILE" "$ASSETS_FILE" > "$CHECKSUM_FILE"

echo "Backup created:"
echo "  Database: $DB_FILE"
echo "  Assets:   $ASSETS_FILE"
echo "  Checksum: $CHECKSUM_FILE"
