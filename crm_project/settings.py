"""Settings for the Real Estate CRM.

All environment-dependent values come from CRM_* environment variables (see
.env.example). Nothing secret is committed. SQLite is the current database;
see docs/MYSQL_MIGRATION.md for the planned MySQL path.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
VAR_DIR = Path(os.environ.get("CRM_VAR_DIR", BASE_DIR / "var"))
VAR_DIR.mkdir(parents=True, exist_ok=True)


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


CRM_ENV = os.environ.get("CRM_ENV", "development")  # development | test | production
# Development defaults to DEBUG on so the README quick start works without a .env file
# (DEBUG off needs collectstatic). Production refuses DEBUG below.
DEBUG = env_bool("CRM_DEBUG", CRM_ENV == "development")
if DEBUG and CRM_ENV == "production":
    raise ImproperlyConfigured("CRM_DEBUG must be off when CRM_ENV=production.")


def _load_secret_key() -> str:
    key = os.environ.get("CRM_SECRET_KEY")
    if key:
        return key
    if CRM_ENV == "production":
        raise ImproperlyConfigured("CRM_SECRET_KEY must be set when CRM_ENV=production.")
    # Development/test bootstrap: a random per-install key stored outside git.
    key_file = VAR_DIR / "secret_key"
    if key_file.exists():
        return key_file.read_text().strip()
    key = secrets.token_urlsafe(50)
    fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(key)
    return key


SECRET_KEY = _load_secret_key()
ALLOWED_HOSTS = env_list("CRM_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")
CSRF_TRUSTED_ORIGINS = env_list("CRM_CSRF_TRUSTED_ORIGINS", "")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "crm.core",
    "crm.accounts",
    "crm.contacts",
    "crm.work",
    "crm.attention",
    "crm.automation",
    "crm.comms",
    "crm.reporting",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "crm.core.middleware.RequestContextMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "crm.accounts.middleware.ForcePasswordChangeMiddleware",
    "crm.core.middleware.WorkspaceTimezoneMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "crm.core.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "crm_project.urls"
WSGI_APPLICATION = "crm_project.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "crm.core.context_processors.workspace",
            ],
        },
    }
]

# --- Database -----------------------------------------------------------------
# SQLite with WAL, a busy timeout, foreign keys (Django enables PRAGMA
# foreign_keys on every SQLite connection) and IMMEDIATE transactions so a
# write transaction takes the write lock up front instead of failing on upgrade.
DB_PATH = Path(os.environ.get("CRM_DB_PATH", VAR_DIR / "crm.sqlite3"))
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DB_PATH,
        "OPTIONS": {
            "timeout": 5,
            "transaction_mode": "IMMEDIATE",
            "init_command": (
                "PRAGMA journal_mode=WAL;"
                "PRAGMA synchronous=NORMAL;"
                "PRAGMA busy_timeout=5000;"
                "PRAGMA foreign_keys=ON;"
            ),
        },
        # File-based test database so tests exercise real SQLite locking/WAL behaviour.
        "TEST": {"NAME": os.environ.get("CRM_TEST_DB_PATH") or str(VAR_DIR / "test-crm.sqlite3")},
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Authentication -------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:today"
LOGOUT_REDIRECT_URL = "accounts:login"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
CRM_LOGIN_MAX_FAILURES = int(os.environ.get("CRM_LOGIN_MAX_FAILURES", "5"))
CRM_LOGIN_LOCK_MINUTES = int(os.environ.get("CRM_LOGIN_LOCK_MINUTES", "15"))

# --- Sessions, cookies and headers ---------------------------------------------
SECURE_COOKIES = env_bool("CRM_SECURE_COOKIES", CRM_ENV == "production")
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_NAME = "crm_session"
SESSION_COOKIE_AGE = int(os.environ.get("CRM_SESSION_HOURS", "12")) * 3600
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_NAME = "crm_csrftoken"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = SECURE_COOKIES
CSRF_FAILURE_VIEW = "crm.core.views.csrf_failure"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = env_bool("CRM_SSL_REDIRECT", False)
SECURE_HSTS_SECONDS = int(os.environ.get("CRM_HSTS_SECONDS", "0"))
if os.environ.get("CRM_BEHIND_TLS_PROXY"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# No CORS headers are emitted: the CRM is same-origin only.
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 400

# --- Internationalisation -------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"  # storage and server clock; display uses the workspace timezone
USE_I18N = False
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = VAR_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG or CRM_ENV == "test"
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

# --- CRM runtime ----------------------------------------------------------------
CRM_BACKUP_DIR = Path(os.environ.get("CRM_BACKUP_DIR", VAR_DIR / "backups"))
CRM_EMAIL_TRANSPORT = os.environ.get("CRM_EMAIL_TRANSPORT", "sandbox")  # only 'sandbox' is implemented
CRM_WORKER_LEASE_SECONDS = int(os.environ.get("CRM_WORKER_LEASE_SECONDS", "120"))
CRM_WORKER_POLL_SECONDS = float(os.environ.get("CRM_WORKER_POLL_SECONDS", "5"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"redact": {"()": "crm.core.logging.RedactingFilter"}},
    "formatters": {"structured": {"()": "crm.core.logging.StructuredFormatter"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "filters": ["redact"], "formatter": "structured"},
    },
    "root": {"handlers": ["console"], "level": os.environ.get("CRM_LOG_LEVEL", "INFO")},
    "loggers": {
        "django.db.backends": {"level": "WARNING"},
    },
}
