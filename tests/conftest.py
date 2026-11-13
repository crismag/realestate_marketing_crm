import datetime as dt
import os

import pytest

os.environ.setdefault("CRM_ENV", "test")


@pytest.fixture(autouse=True)
def _isolated_dirs(settings, tmp_path):
    settings.VAR_DIR = tmp_path
    settings.CRM_BACKUP_DIR = tmp_path / "backups"
    settings.EMAIL_FILE_PATH = tmp_path / "staff_mail"
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # speed only; prod uses Argon2
    yield


@pytest.fixture
def now():
    return dt.datetime(2026, 11, 16, 2, 0, tzinfo=dt.UTC)  # Monday 10:00 Asia/Shanghai


@pytest.fixture
def frozen(now):
    from crm.core import clock

    clock.set_frozen(now)
    yield now
    clock.set_frozen(None)


@pytest.fixture
def users(db):
    from crm.accounts.models import User

    def make(email, name, **kw):
        return User.objects.create_user(email, name, "a-long-test-password-1", **kw)

    return {
        "ana": make("ana@example.test", "Ana Agent"),
        "ben": make("ben@example.test", "Ben Broker"),
        "cora": make("cora@example.test", "Cora Coordinator"),
        "max": make("max@example.test", "Max Manager"),
        "admin": make("admin@example.test", "Ada Admin", is_staff=True),
    }


@pytest.fixture
def pool(db, users):
    from crm.work.models import Pool

    return Pool.objects.create(name="North team pool", coordinator=users["cora"])


@pytest.fixture
def policy(db):
    from crm.core.services import get_policy

    return get_policy()


@pytest.fixture
def make_contact(db, users):
    from crm.contacts.services import capture_contact

    def make(name="Carla Customer", *, actor=None, destination="me", pool=None, email="", inquiry="", **data):
        result = capture_contact(actor=actor or users["ana"], data={"display_name": name, "email": email, **data},
                                 destination=destination, pool=pool, inquiry_message=inquiry)
        return result.contact

    return make


def run_worker(**kw):
    from crm.automation.worker import Worker

    return Worker(worker_id="test-worker", poll_seconds=0).run_once(**kw)
