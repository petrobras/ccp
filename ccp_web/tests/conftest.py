"""Fixtures for the ccp web tests.

Run with ``uv run pytest ccp_web/tests`` (pytest.ini selects
``ccp_web.settings.test``). ``CCP_TEST_MULTI_USER=1`` runs the suite with the
hosted owner model (login required, no auto-login).
"""

import os
from pathlib import Path

import pytest

os.environ.setdefault("CCP_PARALLEL", "0")

import ccp  # noqa: E402

APP_DIR = Path(ccp.__file__).parent / "app"
SLOW_FILES = ("test_flows.py",)


def pytest_addoption(parser):
    parser.addoption(
        "--run-full-evaluation",
        action="store_true",
        default=False,
        help="also run the full ccp.Evaluation rebuild on mock data (minutes)",
    )


def pytest_collection_modifyitems(items):
    for item in items:
        if item.path.name in SLOW_FILES:
            item.add_marker(pytest.mark.slow)


@pytest.fixture
def example():
    def read(name):
        return (APP_DIR / name).read_bytes()

    return read


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        username="alice", email="alice@example.com", password="pw-alice-123"
    )


@pytest.fixture
def web(client, user, settings):
    """A logged-in client (both profiles)."""
    settings.ALLOWED_HOSTS = ["testserver"]
    client.force_login(user)
    return client


@pytest.fixture(autouse=True)
def restore_ccp_config():
    method = ccp.config.POLYTROPIC_METHOD
    yield
    ccp.config.POLYTROPIC_METHOD = method


def import_case(web, content, name="example.ccp"):
    """POST a .ccp file and return the created case."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    from ccp_web.core.models import Case

    response = web.post("/cases/import/", {"file": SimpleUploadedFile(name, content)})
    assert response.status_code == 302, response.content[:500]
    return Case.objects.order_by("-pk").first(), response["Location"]
