#!/bin/sh
set -eu

PROJECT_DIR="/opt/personal-agent-workspace/team_learn_plan"
LOG_FILE="$PROJECT_DIR/output/journey-loop.log"
LOCK_FILE="/tmp/team_learn_plan-journey.lock"
ENV_FILE="/opt/team_learn_plan_smoke.env"

exec 9>"$LOCK_FILE" || { echo "Cannot create lock file" >&2; exit 1; }
if ! flock -n 9; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') journey already running, skipping" >> "$LOG_FILE"
    exit 0
fi

cd "$PROJECT_DIR"

if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck source=/dev/null
    . "$ENV_FILE"
    set +a
fi

export JOURNEY_SCREENSHOT_DIR="${JOURNEY_SCREENSHOT_DIR:-output/journey-screenshots}"
mkdir -p "$JOURNEY_SCREENSHOT_DIR"

DOCKER="docker compose -f compose.yaml -f compose.https.yaml exec -T \
  -e SMOKE_MEMBER_USER \
  -e SMOKE_MEMBER_PASS \
  -e SMOKE_BUDDY_USER \
  -e SMOKE_BUDDY_PASS \
  -e SMOKE_LEADER_USER \
  -e SMOKE_LEADER_PASS \
  web"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

log "journey start"

log "journey cleanup-before"
$DOCKER python manage.py delete_smoke_journey >> "$LOG_FILE" 2>&1 || true

log "journey setup"
$DOCKER python manage.py create_smoke_journey >> "$LOG_FILE" 2>&1

log "journey test"
if python3 -m pytest tests/smoke/test_smoke_journey.py -q --tb=short >> "$LOG_FILE" 2>&1; then
    RESULT="passed"
else
    RESULT="failed"
fi

log "journey cleanup-after"
$DOCKER python manage.py delete_smoke_journey >> "$LOG_FILE" 2>&1 || true

log "journey $RESULT"

if [ "$RESULT" != "passed" ]; then
    exit 1
fi
