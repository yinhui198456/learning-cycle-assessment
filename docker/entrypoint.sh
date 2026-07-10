#!/bin/sh
set -eu

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"

python manage.py collectstatic --noinput
python manage.py migrate --noinput

exec "$@"
