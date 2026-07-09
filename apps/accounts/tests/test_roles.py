import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Mentorship
from apps.accounts.services import (
    assign_buddy,
    has_role,
    primary_role,
    visible_members_for,
)

User = get_user_model()


def _user(username, is_active=True):
    return User.objects.create_user(
        username=username, password="testpass123", is_active=is_active
    )


def _add_role(user, role_name):
    group = Group.objects.get(name=role_name)
    user.groups.add(group)


@pytest.fixture
def member(db):
    user = _user("member")
    _add_role(user, "member")
    return user


@pytest.fixture
def other_member(db):
    user = _user("other-member")
    _add_role(user, "member")
    return user


@pytest.fixture
def buddy(db):
    user = _user("buddy")
    _add_role(user, "buddy")
    return user


@pytest.fixture
def leader(db):
    user = _user("leader")
    _add_role(user, "leader")
    return user


@pytest.fixture
def no_role_user(db):
    return _user("no-role")


@pytest.fixture
def member_client(client, member):
    client.force_login(member)
    return client


@pytest.fixture
def buddy_client(client, buddy):
    client.force_login(buddy)
    return client


@pytest.fixture
def leader_client(client, leader):
    client.force_login(leader)
    return client


@pytest.fixture
def no_role_client(client, no_role_user):
    client.force_login(no_role_user)
    return client


@pytest.mark.django_db
def test_has_role_checks_group_membership(member, buddy, leader):
    assert has_role(member, "member")
    assert not has_role(member, "buddy")
    assert not has_role(member, "leader")

    assert has_role(buddy, "buddy")
    assert has_role(leader, "leader")


@pytest.mark.django_db
def test_primary_role_follows_precedence(member, buddy, leader, no_role_user):
    assert primary_role(member) == "member"
    assert primary_role(buddy) == "buddy"
    assert primary_role(leader) == "leader"
    assert primary_role(no_role_user) is None


@pytest.mark.django_db
def test_member_sees_only_self(member):
    qs = visible_members_for(member)
    assert list(qs) == [member]


@pytest.mark.django_db
def test_buddy_sees_current_bound_members(member, other_member, buddy):
    assign_buddy(member, buddy)

    qs = visible_members_for(buddy)
    assert member in qs
    assert other_member not in qs


@pytest.mark.django_db
def test_buddy_does_not_see_ended_members(member, buddy):
    mentorship = assign_buddy(member, buddy)
    mentorship.ended_at = timezone.localdate()
    mentorship.save()

    qs = visible_members_for(buddy)
    assert member not in qs


@pytest.mark.django_db
def test_leader_sees_active_members(member, other_member, leader):
    qs = visible_members_for(leader)
    assert member in qs
    assert other_member in qs


@pytest.mark.django_db
def test_leader_does_not_see_inactive_members(member, leader):
    member.is_active = False
    member.save()

    qs = visible_members_for(leader)
    assert member not in qs


@pytest.mark.django_db
def test_user_without_role_sees_none(no_role_user):
    qs = visible_members_for(no_role_user)
    assert not qs.exists()


@pytest.mark.django_db
def test_assign_buddy_creates_active_mentorship(member, buddy):
    mentorship = assign_buddy(member, buddy)
    assert mentorship.member == member
    assert mentorship.buddy == buddy
    assert mentorship.ended_at is None
    assert Mentorship.objects.filter(member=member, ended_at__isnull=True).count() == 1


# ---- Workbench and admin views ----


@pytest.mark.django_db
def test_member_workbench_context(member_client, member):
    response = member_client.get(reverse("home"))
    assert response.status_code == 200
    assert response.context["role"] == "member"
    assert member in response.context["members"]


@pytest.mark.django_db
def test_buddy_workbench_context(buddy_client, member, buddy):
    assign_buddy(member, buddy)
    response = buddy_client.get(reverse("home"))
    assert response.status_code == 200
    assert response.context["role"] == "buddy"
    assert member in response.context["members"]


@pytest.mark.django_db
def test_leader_workbench_context(leader_client, member, other_member):
    response = leader_client.get(reverse("home"))
    assert response.status_code == 200
    assert response.context["role"] == "leader"
    assert member in response.context["members"]
    assert other_member in response.context["members"]


@pytest.mark.django_db
def test_leader_user_admin_page_returns_200(leader_client):
    response = leader_client.get(reverse("user_admin"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_member_is_denied_user_admin(member_client):
    response = member_client.get(reverse("user_admin"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_buddy_is_denied_user_admin(buddy_client):
    response = buddy_client.get(reverse("user_admin"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_anonymous_user_is_redirected_from_user_admin(client):
    response = client.get(reverse("user_admin"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


@pytest.mark.django_db
def test_workbench_pages_render_without_template_errors(
    member_client, buddy_client, leader_client
):
    for test_client in (member_client, buddy_client, leader_client):
        response = test_client.get(reverse("home"))
        assert response.status_code == 200
        assert b"</html>" in response.content.lower()
