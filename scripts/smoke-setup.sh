#!/bin/sh
set -eu

PROJECT_DIR="/opt/personal-agent-workspace/team_learn_plan"
ENV_FILE="/opt/team_learn_plan_smoke.env"

if [ -f "$ENV_FILE" ]; then
    # shellcheck source=/dev/null
    . "$ENV_FILE"
fi

cd "$PROJECT_DIR"

docker compose -f compose.yaml -f compose.https.yaml exec -T web python - <<PY
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
import django
django.setup()
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
User = get_user_model()

users = [
    (os.environ.get('SMOKE_MEMBER_USER', 'smoke_member'),
     os.environ.get('SMOKE_MEMBER_PASS', ''), 'member'),
    (os.environ.get('SMOKE_BUDDY_USER', 'smoke_buddy'),
     os.environ.get('SMOKE_BUDDY_PASS', ''), 'buddy'),
    (os.environ.get('SMOKE_LEADER_USER', 'smoke_leader'),
     os.environ.get('SMOKE_LEADER_PASS', ''), 'leader'),
]

for username, password, role in users:
    if not password:
        print(f'SKIP {username}: no password set')
        continue
    user, created = User.objects.get_or_create(username=username)
    user.set_password(password)
    user.is_active = True
    user.save()
    group = Group.objects.get(name=role)
    user.groups.set([group])
    print(f"{'created' if created else 'updated'} {username} as {role}")
PY
