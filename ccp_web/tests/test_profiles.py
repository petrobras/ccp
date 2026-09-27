"""Profile behaviour: desktop auto-login versus hosted login."""

import pytest
from django.conf import settings

pytestmark = pytest.mark.django_db


@pytest.mark.skipif(settings.CCP_MULTI_USER, reason="desktop profile only")
def test_desktop_logs_in_the_local_user(client):
    settings.ALLOWED_HOSTS = ["testserver"]
    response = client.get("/")
    assert response.status_code == 200
    assert response.wsgi_request.user.username == "local"


@pytest.mark.skipif(not settings.CCP_MULTI_USER, reason="hosted profile only")
def test_hosted_requires_login(client):
    settings.ALLOWED_HOSTS = ["testserver"]
    response = client.get("/")
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.skipif(not settings.CCP_MULTI_USER, reason="hosted profile only")
def test_hosted_signup_and_login_pages(client):
    settings.ALLOWED_HOSTS = ["testserver"]
    assert client.get("/accounts/login/").status_code == 200
    response = client.post(
        "/accounts/signup/",
        {
            "email": "carol@example.com",
            "password1": "a-Long-pw-123",
            "password2": "a-Long-pw-123",
        },
    )
    assert response.status_code == 302
    # The new account starts with its own empty workspace.
    assert client.get("/").status_code == 200


def test_home_creates_default_project(web):
    from ccp_web.core.models import Project

    assert web.get("/").status_code == 200
    assert Project.objects.filter(name="Default").count() == 1


def test_project_switch(web):
    from ccp_web.core.models import Project

    web.get("/")
    web.post("/projects/new/", {"name": "K-401"})
    project = Project.objects.get(name="K-401")
    web.post("/cases/new/straight_through/", {})
    assert project.cases.count() == 1
