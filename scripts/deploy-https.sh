#!/bin/sh
set -eu

PROJECT_DIR="/opt/personal-agent-workspace/team_learn_plan"
LOG_FILE="$PROJECT_DIR/output/deploy-loop.log"
LOCK_FILE="/tmp/team_learn_plan-deploy.lock"

exec 9>"$LOCK_FILE" || { echo "Cannot create lock file" >&2; exit 1; }
if ! flock -n 9; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') deploy already running, skipping" >> "$LOG_FILE"
    exit 0
fi

cd "$PROJECT_DIR"

export HOME=/root

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
