import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.staticfiles import finders
from django.urls import reverse

User = get_user_model()


@pytest.fixture
def member_client(client, db):
    user = User.objects.create_user(username="member", password="testpass123")
    user.groups.add(Group.objects.get(name="member"))
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_member_dashboard_has_single_main_landmark(member_client):
    response = member_client.get(reverse("dashboard:member"))
    html = response.content.decode()

    assert response.status_code == 200
    assert html.count("<main") == 1
    assert 'aria-current="page"' in html


@pytest.mark.django_db
def test_base_layout_loads_global_stylesheet(member_client):
    response = member_client.get(reverse("dashboard:member"))
    html = response.content.decode()

    assert 'href="/static/css/app.css"' in html
    assert finders.find("css/app.css")
