import datetime as dt
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
    LearningCycle,
    LearningPlan,
    PlanApprovalEvent,
)
from apps.learning.services_planning import (
    approve_plan,
    edit_plan_item,
    generate_plan,
    request_changes,
    submit_plan,
)

User = get_user_model()


def _user(username):
    return User.objects.create_user(username=username, password="testpass123")


def _add_role(user, role_name):
    user.groups.add(Group.objects.get(name=role_name))


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
def other_buddy(db):
    user = _user("other-buddy")
    _add_role(user, "buddy")
    return user


@pytest.fixture
def leader(db):
    user = _user("leader")
    _add_role(user, "leader")
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
def other_buddy_client(other_buddy):
    client = Client()
    client.force_login(other_buddy)
    return client


@pytest.fixture
def leader_client(leader):
    client = Client()
    client.force_login(leader)
    return client


@pytest.fixture
def plan(db, leader, member, buddy):
    assign_buddy(member, buddy)
    category = CapabilityCategory.objects.create(name="Tech", sort_order=1)
    l1 = CapabilityDomain.objects.create(
        category=category, code="T01", name="Backend", level=1, sort_order=1
    )
    l2 = CapabilityDomain.objects.create(
        category=category,
        parent=l1,
        code="T01.01",
        name="API",
        level=2,
        sort_order=1,
    )
    item = CapabilityItem.objects.create(
        domain=l2,
        code="T01.01.01",
        name="Contract Design",
        suggested_level="P6",
        recommended_action="Practice API reviews",
        acceptance_method="Review passed",
        estimated_hours="12",
        sort_order=1,
    )
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    cycle.add_participant(member)
    assessment = Assessment.objects.get(cycle=cycle, member=member, capability_item=item)
    assessment.current_level = 1
    assessment.target_level = 3
    assessment.included = True
    assessment.planned_quarter = "Q2"
    assessment.planned_month = dt.date(2026, 5, 1)
    assessment.save()
    return generate_plan(member, cycle)


@pytest.mark.django_db
def test_member_submits_plan_to_current_buddy(plan, member):
    submit_plan(plan, member)

    plan.refresh_from_db()
    assert plan.status == LearningPlan.Status.PENDING_APPROVAL
    assert plan.submitted_at is not None
    event = plan.approval_events.get()
    assert event.action == PlanApprovalEvent.Action.SUBMITTED
    assert event.actor == member


@pytest.mark.django_db
def test_member_can_resubmit_after_changes_requested(plan, member, buddy):
    submit_plan(plan, member)
    request_changes(plan, buddy, "Add evidence")
    edit_plan_item(plan.items.get(), member, {"task": "updated task"})

    submit_plan(plan, member)

    plan.refresh_from_db()
    assert plan.status == LearningPlan.Status.PENDING_APPROVAL
    assert list(plan.approval_events.values_list("action", flat=True)) == [
        PlanApprovalEvent.Action.SUBMITTED,
        PlanApprovalEvent.Action.CHANGES_REQUESTED,
        PlanApprovalEvent.Action.SUBMITTED,
    ]


@pytest.mark.django_db
def test_only_current_buddy_can_request_changes(plan, member, other_buddy):
    submit_plan(plan, member)

    with pytest.raises(PermissionError):
        request_changes(plan, other_buddy, "No")

    plan.refresh_from_db()
    assert plan.status == LearningPlan.Status.PENDING_APPROVAL


@pytest.mark.django_db
def test_request_changes_requires_comment(plan, member, buddy):
    submit_plan(plan, member)

    with pytest.raises(ValueError, match="comment"):
        request_changes(plan, buddy, " ")


@pytest.mark.django_db
def test_buddy_approves_pending_plan(plan, member, buddy):
    submit_plan(plan, member)
    approve_plan(plan, buddy)

    plan.refresh_from_db()
    assert plan.status == LearningPlan.Status.ACTIVE
    assert plan.approved_at is not None
    assert plan.approval_events.last().action == PlanApprovalEvent.Action.APPROVED


@pytest.mark.django_db
def test_repeated_submit_and_approval_actions_fail(plan, member, buddy):
    submit_plan(plan, member)
    with pytest.raises(ValueError, match="cannot be submitted"):
        submit_plan(plan, member)

    approve_plan(plan, buddy)
    with pytest.raises(ValueError, match="cannot be approved"):
        approve_plan(plan, buddy)
    with pytest.raises(ValueError, match="cannot request changes"):
        request_changes(plan, buddy, "Too late")


@pytest.mark.django_db
def test_active_plan_item_cannot_be_edited(plan, member, buddy):
    submit_plan(plan, member)
    approve_plan(plan, buddy)

    with pytest.raises(ValueError, match="cannot be edited"):
        edit_plan_item(plan.items.get(), member, {"task": "changed"})


@pytest.mark.django_db
def test_member_cannot_edit_another_members_plan_item(plan, other_member):
    with pytest.raises(PermissionError):
        edit_plan_item(plan.items.get(), other_member, {"task": "changed"})


@pytest.mark.django_db
def test_member_submit_view_and_buddy_approval_view(plan, member_client, buddy_client):
    response = member_client.post(reverse("learning:plan-submit", args=[plan.pk]))
    assert response.status_code == HTTPStatus.FOUND

    response = buddy_client.get(reverse("learning:buddy-approvals"))
    assert response.status_code == HTTPStatus.OK
    assert plan.member.username in response.content.decode()

    response = buddy_client.post(reverse("learning:plan-approve", args=[plan.pk]))
    assert response.status_code == HTTPStatus.FOUND
    plan.refresh_from_db()
    assert plan.status == LearningPlan.Status.ACTIVE


@pytest.mark.django_db
def test_non_buddy_and_wrong_buddy_cannot_approve(
    plan, member, leader_client, other_buddy_client
):
    submit_plan(plan, member)

    response = leader_client.post(reverse("learning:plan-approve", args=[plan.pk]))
    assert response.status_code == HTTPStatus.FORBIDDEN

    response = other_buddy_client.post(reverse("learning:plan-approve", args=[plan.pk]))
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_repeated_submit_view_returns_conflict(plan, member_client):
    response = member_client.post(reverse("learning:plan-submit", args=[plan.pk]))
    assert response.status_code == HTTPStatus.FOUND

    response = member_client.post(reverse("learning:plan-submit", args=[plan.pk]))
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.django_db
def test_blank_request_changes_view_returns_bad_request(plan, member, buddy_client):
    submit_plan(plan, member)

    response = buddy_client.post(
        reverse("learning:plan-request-changes", args=[plan.pk]),
        {"comment": " "},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_buddy_can_view_assigned_pending_plan_detail(plan, member, buddy_client):
    submit_plan(plan, member)

    response = buddy_client.get(reverse("learning:plan-detail", args=[plan.pk]))

    assert response.status_code == HTTPStatus.OK
    assert plan.cycle.name in response.content.decode()
    assert plan.items.get().capability_name in response.content.decode()


@pytest.mark.django_db
def test_buddy_approvals_page_links_to_plan_detail(plan, member, buddy_client):
    submit_plan(plan, member)

    response = buddy_client.get(reverse("learning:buddy-approvals"))

    assert response.status_code == HTTPStatus.OK
    assert reverse("learning:plan-detail", args=[plan.pk]) in response.content.decode()
    assert plan.items.get().capability_name in response.content.decode()


@pytest.mark.django_db
def test_member_draft_plan_detail_shows_inline_edit_form(plan, member_client):
    item = plan.items.get()

    response = member_client.get(reverse("learning:plan-detail", args=[plan.pk]))

    assert response.status_code == HTTPStatus.OK
    content = response.content.decode()
    assert reverse("learning:plan-item-edit", args=[item.pk]) in content
    assert f'name="task"' in content
    assert f'name="acceptance_method"' in content


@pytest.mark.django_db
def test_member_pending_plan_detail_hides_inline_edit_form(plan, member_client):
    submit_plan(plan, plan.member)

    response = member_client.get(reverse("learning:plan-detail", args=[plan.pk]))

    assert response.status_code == HTTPStatus.OK
    content = response.content.decode()
    assert reverse("learning:plan-item-edit", args=[plan.items.get().pk]) not in content


@pytest.mark.django_db
def test_buddy_changes_requested_plan_detail_hides_member_edit_actions(
    plan, member, buddy, buddy_client
):
    submit_plan(plan, member)
    request_changes(plan, buddy, "revise")

    response = buddy_client.get(reverse("learning:plan-detail", args=[plan.pk]))

    assert response.status_code == HTTPStatus.OK
    content = response.content.decode()
    assert reverse("learning:plan-item-edit", args=[plan.items.get().pk]) not in content
    assert reverse("learning:plan-submit", args=[plan.pk]) not in content
