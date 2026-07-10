import re
from pathlib import Path

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


@pytest.fixture
def leader_client(client, db):
    user = User.objects.create_user(username="leader", password="testpass123")
    user.groups.add(Group.objects.get(name="leader"))
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_user_admin_buddy_select_has_accessible_name(leader_client):
    member = User.objects.create_user(username="member", password="testpass123")
    member.groups.add(Group.objects.get(name="member"))
    buddy = User.objects.create_user(username="buddy", password="testpass123", is_active=True)
    buddy.groups.add(Group.objects.get(name="buddy"))

    response = leader_client.get(reverse("user_admin"))
    html = response.content.decode()

    assert response.status_code == 200
    assert re.search(
        r'<select[^>]*name=["\']buddy["\'][^>]*aria-label=',
        html,
    ), "Buddy <select> is missing an accessible name"


@pytest.mark.django_db
def test_admin_tables_are_wrapped_for_horizontal_scroll(leader_client):
    for url_name in ("user_admin", "learning:admin-capabilities"):
        response = leader_client.get(reverse(url_name))
        html = response.content.decode()

        assert response.status_code == 200
        table_count = html.count("<table")
        assert table_count > 0
        wrapped_opens = len(re.findall(r'<div class="table-wrap">\s*<table', html, flags=re.DOTALL))
        wrapped_closes = len(re.findall(r'</table>\s*</div>', html, flags=re.DOTALL))
        assert wrapped_opens == table_count, f"{url_name} has unwrapped table opens"
        assert wrapped_closes == table_count, f"{url_name} has unwrapped table closes"


def test_app_css_has_minimum_touch_affordance():
    css_path = finders.find("css/app.css")
    css = Path(css_path).read_text(encoding="utf-8")
    assert ".main-nav a" in css
    assert "min-height: 44px" in css
    assert "min-width: 44px" in css
    assert "button" in css
    assert "touch-action: manipulation" in css


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


@pytest.fixture
def buddy_client(client, db):
    user = User.objects.create_user(username="buddy", password="testpass123")
    user.groups.add(Group.objects.get(name="buddy"))
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_member_nav_shows_personal_assessment_and_workbench(member_client):
    response = member_client.get(reverse("dashboard:member"))
    html = response.content.decode()

    assert reverse("home") in html
    assert "个人" in html
    assert "能力自评" in html
    assert "Buddy" not in html
    assert "Leader" not in html


@pytest.mark.django_db
def test_buddy_nav_shows_buddy_and_workbench(buddy_client):
    response = buddy_client.get(reverse("dashboard:buddy"))
    html = response.content.decode()

    assert reverse("home") in html
    assert "Buddy" in html
    assert "个人" not in html
    assert "能力自评" not in html
    assert "Leader" not in html


@pytest.mark.django_db
def test_leader_nav_shows_leader_and_workbench(leader_client):
    response = leader_client.get(reverse("dashboard:leader"))
    html = response.content.decode()

    assert reverse("home") in html
    assert "Leader" in html
    assert "个人" not in html
    assert "Buddy" not in html
    assert "能力自评" not in html


@pytest.mark.django_db
def test_403_page_renders_branded_with_main_landmark(member_client):
    response = member_client.get(
        reverse("dashboard:leader"),
        raise_request_exception=False,
    )
    html = response.content.decode()

    assert response.status_code == 403
    assert html.count("<main") == 1
    assert reverse("home") in html


@pytest.mark.django_db
def test_404_page_renders_branded_with_main_landmark(client):
    response = client.get("/nonexistent-url/", raise_request_exception=False)
    html = response.content.decode()

    assert response.status_code == 404
    assert html.count("<main") == 1
    assert reverse("home") in html
