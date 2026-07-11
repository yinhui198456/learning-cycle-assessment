#!/bin/sh
set -eu

PROJECT_DIR="/opt/personal-agent-workspace/team_learn_plan"
LOG_FILE="$PROJECT_DIR/output/smoke-loop.log"
LOCK_FILE="/tmp/team_learn_plan-smoke.lock"
ENV_FILE="/opt/team_learn_plan_smoke.env"

exec 9>"$LOCK_FILE" || { echo "Cannot create lock file" >&2; exit 1; }
if ! flock -n 9; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') smoke already running, skipping" >> "$LOG_FILE"
    exit 0
fi

cd "$PROJECT_DIR"

if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck source=/dev/null
    . "$ENV_FILE"
    set +a
fi

mkdir -p "${SMOKE_SCREENSHOT_DIR:-output/smoke-screenshots}"

echo "$(date '+%Y-%m-%d %H:%M:%S') smoke start" >> "$LOG_FILE"

if python3 -m pytest tests/smoke/test_smoke_readonly.py -q --tb=short >> "$LOG_FILE" 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') smoke passed" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') smoke failed, see $LOG_FILE and ${SMOKE_SCREENSHOT_DIR:-output/smoke-screenshots}/" >> "$LOG_FILE"
    exit 1
fi
