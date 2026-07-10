import datetime as dt

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.accounts.services import assign_buddy
from apps.learning.models import (
    Assessment,
    CapabilityCategory,
    CapabilityDomain,
    CapabilityItem,
    CatalogSyncLog,
    LearningCycle,
    LearningPlan,
    PlanItem,
)
from apps.learning.services_planning import approve_plan, generate_plan, submit_plan
from apps.learning.services_sync import DEFAULT_SYNC_FIELDS, preview_capability_sync, sync_capability

User = get_user_model()


def _user(username):
    return User.objects.create_user(username=username, password="testpass123")


def _add_role(user, role):
    user.groups.add(Group.objects.get(name=role))


@pytest.fixture
def sync_fixture(db):
    leader = _user("leader")
    _add_role(leader, "leader")
    member = _user("member")
    _add_role(member, "member")
    done_member = _user("done-member")
    _add_role(done_member, "member")
    buddy = _user("buddy")
    _add_role(buddy, "buddy")
    assign_buddy(member, buddy)
    assign_buddy(done_member, buddy)

    category = CapabilityCategory.objects.create(name="Tech", sort_order=1)
    l1 = CapabilityDomain.objects.create(
        category=category, code="T01", name="Backend", level=1, sort_order=1
    )
    l2 = CapabilityDomain.objects.create(
        category=category, parent=l1, code="T01.01", name="API", level=2, sort_order=1
    )
    capability = CapabilityItem.objects.create(
        domain=l2,
        code="T01.01.01",
        name="Old Name",
        suggested_level="P6",
        acceptance_method="Old Acceptance",
        estimated_hours="8",
        recommended_action="Old Task",
        sort_order=1,
    )

    active_cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR, year=2026, created_by=leader
    )
    active_cycle.add_participant(member)
    active_cycle.add_participant(done_member)
    archived_cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR, year=2027, created_by=leader
    )
    archived_cycle.add_participant(member)

    for cycle, plan_member in (
        (active_cycle, member),
        (active_cycle, done_member),
        (archived_cycle, member),
    ):
        assessment = Assessment.objects.get(
            cycle=cycle, member=plan_member, capability_item=capability
        )
        assessment.included = True
        assessment.planned_month = dt.date(cycle.start_date.year, 5, 1)
        assessment.save()
        plan = generate_plan(plan_member, cycle)
        submit_plan(plan, plan_member)
        approve_plan(plan, buddy)

    archived_cycle.status = LearningCycle.Status.ARCHIVED
    archived_cycle.save()

    active_item = PlanItem.objects.get(plan__cycle=active_cycle, plan__member=member)
    completed_item = PlanItem.objects.get(
        plan__cycle=active_cycle,
        plan__member=done_member,
    )
    completed_item.capability_name = "old completed"
    completed_item.execution_status = PlanItem.ExecutionStatus.COMPLETED
    completed_item.save()
    archived_item = PlanItem.objects.get(plan__cycle=archived_cycle)

    capability.name = "New Name"
    capability.suggested_level = "P7"
    capability.acceptance_method = "New Acceptance"
    capability.estimated_hours = "13"
    capability.recommended_action = "New Task"
    capability.save()

    return {
        "capability": capability,
        "active_item": active_item,
        "completed_item": completed_item,
        "archived_item": archived_item,
    }


@pytest.mark.django_db
def test_sync_preview_lists_only_unfinished_active_cycle_items(sync_fixture):
    preview = preview_capability_sync(sync_fixture["capability"], DEFAULT_SYNC_FIELDS)

    assert [row["plan_item"] for row in preview] == [sync_fixture["active_item"]]
    assert preview[0]["changes"]["capability_name"] == ("Old Name", "New Name")
    assert "task" not in preview[0]["changes"]


@pytest.mark.django_db
def test_sync_never_changes_completed_or_archived_items(sync_fixture):
    sync_capability(sync_fixture["capability"], [sync_fixture["active_item"].pk], DEFAULT_SYNC_FIELDS)

    sync_fixture["active_item"].refresh_from_db()
    sync_fixture["completed_item"].refresh_from_db()
    sync_fixture["archived_item"].refresh_from_db()

    assert sync_fixture["active_item"].capability_name == "New Name"
    assert sync_fixture["active_item"].suggested_level == "P7"
    assert sync_fixture["active_item"].acceptance_method == "Old Acceptance"
    assert sync_fixture["completed_item"].capability_name == "old completed"
    assert sync_fixture["archived_item"].capability_name == "Old Name"
    log = CatalogSyncLog.objects.get()
    assert log.capability_item == sync_fixture["capability"]
    assert log.plan_item == sync_fixture["active_item"]
    assert "capability_name" in log.field_names
