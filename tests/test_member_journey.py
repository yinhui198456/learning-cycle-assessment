import datetime as dt
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.services import assign_buddy
from apps.learning.models import (
    Assessment,
    CapabilityCategory,
    CapabilityDomain,
    CapabilityItem,
    EvidenceSubmission,
    LearningCycle,
    LearningPlan,
    PlanItem,
)
from apps.learning.services_execution import add_progress_update, submit_evidence
from apps.learning.services_planning import (
    approve_plan,
    edit_plan_item,
    generate_plan,
    submit_plan,
)

User = get_user_model()


def _user(username):
    return User.objects.create_user(username=username, password="testpass123")


def _add_role(user, role_name):
    user.groups.add(Group.objects.get(name=role_name))


@pytest.mark.django_db
def test_member_journey_end_to_end():
    # Roles
    leader = _user("leader")
    _add_role(leader, "leader")
    member = _user("member")
    _add_role(member, "member")
    buddy = _user("buddy")
    _add_role(buddy, "buddy")

    # Capability catalog
    category = CapabilityCategory.objects.create(name="Tech", sort_order=1)
    domain_l1 = CapabilityDomain.objects.create(
        category=category, code="T01", name="Backend", level=1, sort_order=1
    )
    domain_l2 = CapabilityDomain.objects.create(
        category=category,
        parent=domain_l1,
        code="T01.01",
        name="API",
        level=2,
        sort_order=1,
    )
    capability = CapabilityItem.objects.create(
        domain=domain_l2,
        code="T01.01.01",
        name="Contract Design",
        acceptance_method="Design review",
        estimated_hours="12",
        recommended_action="Read and practice",
        sort_order=1,
        is_active=True,
    )

    # Cycle and participant
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    cycle.add_participant(member)

    # Buddy assignment
    assign_buddy(member, buddy)

    # Assessment
    assessment = Assessment.objects.get(
        cycle=cycle, member=member, capability_item=capability
    )
    assessment.included = True
    assessment.current_level = 1
    assessment.target_level = 3
    assessment.planned_month = dt.date(2026, 5, 1)
    assessment.save()

    # Plan generation and edit
    plan = generate_plan(member, cycle)
    item = plan.items.get()
    edit_plan_item(
        item,
        member,
        {"task": "Updated task for the journey", "estimated_hours": "10"},
    )

    # Submit and approve
    submit_plan(plan, member)
    approve_plan(plan, buddy)

    # Execution
    add_progress_update(item, member, "Made progress", Decimal("2.0"))
    submit_evidence(
        item,
        member,
        "Done",
        "https://example.com/evidence",
        [SimpleUploadedFile("evidence.pdf", b"ok", content_type="application/pdf")],
    )

    plan.refresh_from_db()
    item.refresh_from_db()

    assert plan.status == LearningPlan.Status.ACTIVE
    assert item.execution_status == PlanItem.ExecutionStatus.PENDING_REVIEW
    assert EvidenceSubmission.objects.count() == 1
