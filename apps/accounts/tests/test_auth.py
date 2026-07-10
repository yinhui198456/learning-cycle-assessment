import importlib
import sys

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse


User = get_user_model()


@pytest.mark.django_db
def test_anonymous_user_is_redirected_to_login(client):
    response = client.get(reverse("home"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


@pytest.mark.django_db
def test_valid_user_can_log_in_and_reach_home(client):
    User.objects.create_user(username="member", password="testpass123")
    assert client.login(username="member", password="testpass123")
    response = client.get(reverse("home"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_without_next_redirects_to_home(client):
    User.objects.create_user(username="member", password="testpass123")
    response = client.post(
        reverse("login"),
        {"username": "member", "password": "testpass123"},
    )
    assert response.status_code == 302
    assert response.url == reverse("home")


@pytest.mark.django_db
def test_invalid_credentials_remain_on_login_page(client):
    response = client.post(
        reverse("login"),
        {"username": "nobody", "password": "wrong"},
    )
    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
def test_login_form_redirects_to_next(client):
    User.objects.create_user(username="member", password="testpass123")
    login_url = f"{reverse('login')}?next=/"
    response = client.get(login_url)
    content = response.content.decode()
    assert 'name="next"' in content
    assert 'value="/"' in content

    response = client.post(
        reverse("login"),
        {"username": "member", "password": "testpass123", "next": "/"},
    )
    assert response.status_code == 302
    assert response.url == "/"


@pytest.mark.parametrize(
    "missing_var",
    [
        "DJANGO_SECRET_KEY",
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "DATABASE_URL",
    ],
)
def test_production_settings_require_env_var(monkeypatch, missing_var):
    required = {
        "DJANGO_SECRET_KEY": "secret",
        "DJANGO_ALLOWED_HOSTS": "example.com",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "https://example.com",
        "DATABASE_URL": "postgres://user:pass@localhost:5432/db",
    }
    for key, value in required.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv(missing_var, raising=False)

    for mod in list(sys.modules):
        if mod.startswith("config.settings"):
            del sys.modules[mod]

    with pytest.raises(ImproperlyConfigured):
        importlib.import_module("config.settings.production")


def test_production_settings_reject_sqlite_database_url(monkeypatch):
    required = {
        "DJANGO_SECRET_KEY": "secret",
        "DJANGO_ALLOWED_HOSTS": "example.com",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "https://example.com",
        "DATABASE_URL": "sqlite:///prod.sqlite3",
    }
    for key, value in required.items():
        monkeypatch.setenv(key, value)

    for mod in list(sys.modules):
        if mod.startswith("config.settings"):
            del sys.modules[mod]

    with pytest.raises(ImproperlyConfigured):
        importlib.import_module("config.settings.production")


def test_production_settings_have_secure_defaults(monkeypatch):
    required = {
        "DJANGO_SECRET_KEY": "secret",
        "DJANGO_ALLOWED_HOSTS": "example.com",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "https://example.com",
        "DATABASE_URL": "postgres://user:pass@localhost:5432/db",
    }
    for key, value in required.items():
        monkeypatch.setenv(key, value)

    for mod in list(sys.modules):
        if mod.startswith("config.settings"):
            del sys.modules[mod]

    production = importlib.import_module("config.settings.production")
    assert production.SECURE_SSL_REDIRECT is True
    assert production.SECURE_HSTS_SECONDS == 60
    assert production.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    assert production.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert production.SESSION_COOKIE_SECURE is True
    assert production.CSRF_COOKIE_SECURE is True
    assert production.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert not hasattr(production, "SECURE_BROWSER_XSS_FILTER")


def test_local_settings_disallow_wildcard_hosts():
    for mod in list(sys.modules):
        if mod.startswith("config.settings"):
            del sys.modules[mod]

    local = importlib.import_module("config.settings.local")
    assert "*" not in local.ALLOWED_HOSTS
    assert local.ALLOWED_HOSTS == ["localhost", "127.0.0.1", "[::1]"]
