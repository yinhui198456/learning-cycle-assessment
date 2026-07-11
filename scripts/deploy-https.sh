#!/bin/sh
set -eu

PROJECT_DIR="/opt/personal-agent-workspace/team_learn_plan"
LOG_FILE="$PROJECT_DIR/output/deploy-loop.log"
LOCK_FILE="/tmp/team_learn_plan-deploy.lock"
SSL_DIR="/opt/team_learn_plan_ssl"

exec 9>"$LOCK_FILE" || { echo "Cannot create lock file" >&2; exit 1; }
if ! flock -n 9; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') deploy already running, skipping" >> "$LOG_FILE"
    exit 0
fi

cd "$PROJECT_DIR"

export HOME=/root

# Ensure self-signed SSL certificates exist outside the git workspace
if [ ! -f "$SSL_DIR/selfsigned.crt" ] || [ ! -f "$SSL_DIR/selfsigned.key" ]; then
    mkdir -p "$SSL_DIR"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/selfsigned.key" \
        -out "$SSL_DIR/selfsigned.crt" \
        -subj "/CN=team-learn-plan" \
        -addext "subjectAltName=IP:118.25.27.18,IP:10.0.0.16" >> "$LOG_FILE" 2>&1
    chmod 600 "$SSL_DIR/selfsigned.key"
    chmod 644 "$SSL_DIR/selfsigned.crt"
    echo "$(date '+%Y-%m-%d %H:%M:%S') generated self-signed SSL certificate" >> "$LOG_FILE"
fi

git fetch origin main >> "$LOG_FILE" 2>&1

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') no changes on main ($LOCAL)" >> "$LOG_FILE"
    exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') new commit $REMOTE, deploying..." >> "$LOG_FILE"

if git pull origin main >> "$LOG_FILE" 2>&1; then
    if /usr/bin/docker compose -f compose.yaml -f compose.https.yaml up --build -d >> "$LOG_FILE" 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') deployed $REMOTE" >> "$LOG_FILE"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') docker compose failed" >> "$LOG_FILE"
        exit 1
    fi
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') git pull failed" >> "$LOG_FILE"
    exit 1
fi
