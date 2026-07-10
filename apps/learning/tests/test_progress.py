import datetime as dt
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.services import assign_buddy
from apps.learning.models import (
    Assessment,
    CapabilityCategory,
    CapabilityDomain,
    CapabilityItem,
    GuidanceComment,
    LearningCycle,
    LearningPlan,
    ProgressUpdate,
)
from apps.learning.services_execution import add_guidance_comment, add_progress_update
from apps.learning.services_planning import approve_plan, generate_plan, submit_plan

User = get_user_model()


def _user(username):
    return User.objects.create_user(username=username, password="testpass123")


def _add_role(user, role):
    user.groups.add(Group.objects.get(name=role))


@pytest.fixture
def member(db):
    user = _user("member")
    _add_role(user, "member")
    return user


@pytest.fixture
def buddy(db):
    user = _user("buddy")
    _add_role(user, "buddy")
    return user


@pytest.fixture
def other_member(db):
    user = _user("other-member")
    _add_role(user, "member")
    return user


@pytest.fixture
def member_client(member):
    client = Client()
    client.force_login(member)
    return client


@pytest.fixture
def buddy_client(buddy):
    client = Client()
    client.force_login(buddy)
    return client


@pytest.fixture
def active_plan_item(db, member, buddy):
    leader = _user("leader")
    _add_role(leader, "leader")
    assign_buddy(member, buddy)
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
    assessment.planned_month = dt.date(2026, 5, 1)
    assessment.save()
    plan = generate_plan(member, cycle)
    submit_plan(plan, member)
    approve_plan(plan, buddy)
    return plan.items.get()


@pytest.mark.django_db
def test_member_adds_progress_and_total_hours(active_plan_item, member):
    add_progress_update(active_plan_item, member, "Read chapter 1", Decimal("1.5"))
    add_progress_update(active_plan_item, member, "Practice review", Decimal("2.0"))

    assert ProgressUpdate.objects.count() == 2
    assert active_plan_item.actual_hours == Decimal("3.5")


@pytest.mark.django_db
def test_non_member_cannot_add_progress(active_plan_item, other_member):
    with pytest.raises(PermissionError):
        add_progress_update(active_plan_item, other_member, "No", Decimal("1.0"))


@pytest.mark.django_db
def test_current_buddy_adds_guidance_comment(active_plan_item, buddy):
    comment = add_guidance_comment(active_plan_item, buddy, "Focus on API versioning")

    assert comment.author == buddy
    assert GuidanceComment.objects.count() == 1


@pytest.mark.django_db
def test_member_progress_and_buddy_comment_views(
    active_plan_item, member_client, buddy_client
):
    response = member_client.post(
        reverse("learning:progress-add", args=[active_plan_item.pk]),
        {"content": "done", "hours_spent": "1.5"},
    )
    assert response.status_code == HTTPStatus.FOUND

    response = buddy_client.post(
        reverse("learning:guidance-add", args=[active_plan_item.pk]),
        {"content": "add evidence"},
    )
    assert response.status_code == HTTPStatus.FOUND

    response = member_client.get(
        reverse("learning:execution-detail", args=[active_plan_item.pk])
    )
    assert response.status_code == HTTPStatus.OK
    content = response.content.decode()
    assert "done" in content
    assert "add evidence" in content


@pytest.mark.django_db
def test_other_member_progress_view_returns_not_found(active_plan_item, other_member):
    client = Client()
    client.force_login(other_member)

    response = client.post(
        reverse("learning:progress-add", args=[active_plan_item.pk]),
        {"content": "no", "hours_spent": "1"},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_invalid_progress_hours_view_returns_bad_request(active_plan_item, member_client):
    response = member_client.post(
        reverse("learning:progress-add", args=[active_plan_item.pk]),
        {"content": "done", "hours_spent": "abc"},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
