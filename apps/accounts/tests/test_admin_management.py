import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Mentorship
from apps.accounts.services import assign_buddy, reassign_buddy, set_user_active
from apps.learning.models import (
    Assessment,
    CapabilityCategory,
    CapabilityDomain,
    CapabilityItem,
    LearningCycle,
    LearningPlan,
)
from apps.learning.services_planning import generate_plan, submit_plan

User = get_user_model()


def _user(username):
    return User.objects.create_user(username=username, password="testpass123")


def _add_role(user, role):
    user.groups.add(Group.objects.get(name=role))


@pytest.fixture
def leader(db):
    user = _user("leader")
    _add_role(user, "leader")
    return user


@pytest.fixture
def leader_client(leader):
    client = Client()
    client.force_login(leader)
    return client


@pytest.fixture
def member(db):
    user = _user("member")
    _add_role(user, "member")
    return user


@pytest.fixture
def buddy_one(db):
    user = _user("buddy-one")
    _add_role(user, "buddy")
    return user


@pytest.fixture
def buddy_two(db):
    user = _user("buddy-two")
    _add_role(user, "buddy")
    return user


@pytest.fixture
def pending_plan(db, leader, member, buddy_one):
    assign_buddy(member, buddy_one)
    category = CapabilityCategory.objects.create(name="Tech", sort_order=1)
    l1 = CapabilityDomain.objects.create(
        category=category, code="T01", name="Backend", level=1, sort_order=1
    )
    l2 = CapabilityDomain.objects.create(
        category=category, parent=l1, code="T01.01", name="API", level=2, sort_order=1
    )
    capability = CapabilityItem.objects.create(
        domain=l2, code="T01.01.01", name="Contracts", sort_order=1
    )
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR, year=2026, created_by=leader
    )
    cycle.add_participant(member)
    assessment = Assessment.objects.get(
        cycle=cycle, member=member, capability_item=capability
    )
    assessment.included = True
    assessment.save()
    plan = generate_plan(member, cycle)
    submit_plan(plan, member)
    return plan


@pytest.mark.django_db
def test_leader_can_deactivate_user(member):
    set_user_active(member, False)

    member.refresh_from_db()
    assert member.is_active is False


@pytest.mark.django_db
def test_reassign_buddy_preserves_history_and_transfers_pending_plan(
    pending_plan, member, buddy_one, buddy_two
):
    reassign_buddy(member, buddy_two)

    pending_plan.refresh_from_db()
    assert pending_plan.buddy == buddy_two
    assert Mentorship.objects.filter(member=member, buddy=buddy_one, ended_at__isnull=False).exists()
    assert Mentorship.objects.filter(member=member, buddy=buddy_two, ended_at__isnull=True).exists()


@pytest.mark.django_db
def test_leader_can_update_user_active_and_buddy_from_view(
    leader_client, pending_plan, member, buddy_two
):
    response = leader_client.post(
        reverse("user_active", args=[member.pk]),
        {"is_active": ""},
    )
    assert response.status_code == 302
    member.refresh_from_db()
    assert member.is_active is False

    member.is_active = True
    member.save()

    response = leader_client.post(
        reverse("user_buddy", args=[member.pk]),
        {"buddy": buddy_two.pk},
    )
    assert response.status_code == 302
    pending_plan.refresh_from_db()
    assert pending_plan.buddy == buddy_two
