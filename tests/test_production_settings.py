import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.urls import reverse

BASE_DIR = Path(__file__).resolve().parent.parent


def _run_django_setup(env_updates):
    env = os.environ.copy()
    env.update(env_updates)
    env.pop("DJANGO_SECRET_KEY", None) if "DJANGO_SECRET_KEY" not in env_updates else None
    return subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def _get_setting(name, env_updates):
    env = os.environ.copy()
    env.update(env_updates)
    code = (
        "import django; django.setup(); "
        "from django.conf import settings; "
        f"print(getattr(settings, {name!r}, None))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_production_settings_require_secret_key():
    result = _run_django_setup({
        "DJANGO_SETTINGS_MODULE": "config.settings.production",
        "DJANGO_ALLOWED_HOSTS": "localhost",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "http://localhost",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
    })

    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY must be set" in result.stderr


def test_production_settings_accept_valid_secret_key():
    result = _run_django_setup({
        "DJANGO_SETTINGS_MODULE": "config.settings.production",
        "DJANGO_SECRET_KEY": "x" * 50,
        "DJANGO_ALLOWED_HOSTS": "localhost",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "http://localhost",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
    })

    assert result.returncode == 0, result.stderr


@pytest.mark.django_db
def test_health_endpoint(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_secure_ssl_redirect_defaults_to_true():
    value = _get_setting("SECURE_SSL_REDIRECT", {
        "DJANGO_SETTINGS_MODULE": "config.settings.production",
        "DJANGO_SECRET_KEY": "x" * 50,
        "DJANGO_ALLOWED_HOSTS": "localhost",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "http://localhost",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
    })
    assert value == "True"


def test_secure_ssl_redirect_can_be_disabled():
    value = _get_setting("SECURE_SSL_REDIRECT", {
        "DJANGO_SETTINGS_MODULE": "config.settings.production",
        "DJANGO_SECRET_KEY": "x" * 50,
        "DJANGO_ALLOWED_HOSTS": "localhost",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "http://localhost",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
        "DJANGO_SECURE_SSL_REDIRECT": "false",
    })
    assert value == "False"
