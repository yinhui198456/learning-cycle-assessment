from .base import *  # noqa: F403,F401

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-secret-key-not-for-production")  # noqa: F405

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}
