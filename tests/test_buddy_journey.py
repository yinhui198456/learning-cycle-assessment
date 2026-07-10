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
    ReviewDecision,
)
from apps.learning.services_execution import review_evidence, submit_evidence
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


@pytest.mark.django_db
def test_buddy_journey_approve_after_changes():
    # Roles
    leader = _user("leader")
    _add_role(leader, "leader")
    member = _user("member")
    _add_role(member, "member")
    buddy = _user("buddy")
    _add_role(buddy, "buddy")
    other_buddy = _user("other_buddy")
    _add_role(other_buddy, "buddy")

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

    # Included assessment
    assessment = Assessment.objects.get(
        cycle=cycle, member=member, capability_item=capability
    )
    assessment.included = True
    assessment.current_level = 1
    assessment.target_level = 3
    assessment.planned_month = dt.date(2026, 5, 1)
    assessment.save()

    # Plan generation
    plan = generate_plan(member, cycle)
    item = plan.items.get()

    # Member submits plan
    submit_plan(plan, member)
    assert plan.status == LearningPlan.Status.PENDING_APPROVAL

    # Wrong buddy cannot approve or request changes
    with pytest.raises(PermissionError):
        approve_plan(plan, other_buddy)
    with pytest.raises(PermissionError):
        request_changes(plan, other_buddy, "Need changes")

    # Current buddy requests changes
    request_changes(plan, buddy, "Please refine the task")
    assert plan.status == LearningPlan.Status.CHANGES_REQUESTED

    # Member edits and resubmits
    edit_plan_item(
        item,
        member,
        {"task": "Refined task for the journey", "estimated_hours": "10"},
    )
    submit_plan(plan, member)
    assert plan.status == LearningPlan.Status.PENDING_APPROVAL

    # Current buddy approves
    approve_plan(plan, buddy)
    assert plan.status == LearningPlan.Status.ACTIVE

    # Ensure the item sees the active plan before execution
    item.refresh_from_db()
    item.plan.refresh_from_db()

    # Member submits evidence
    submission_1 = submit_evidence(
        item,
        member,
        "First evidence",
        "https://example.com/evidence1",
        [SimpleUploadedFile("evidence1.pdf", b"ok", content_type="application/pdf")],
    )
    item.refresh_from_db()
    assert item.execution_status == PlanItem.ExecutionStatus.PENDING_REVIEW

    # Current buddy requests evidence changes
    review_evidence(
        submission_1,
        buddy,
        ReviewDecision.Decision.CHANGES_REQUESTED,
        "Please add more details",
    )
    item.refresh_from_db()
    assert item.execution_status == PlanItem.ExecutionStatus.CHANGES_REQUESTED

    # Member submits evidence again
    submission_2 = submit_evidence(
        item,
        member,
        "Updated evidence",
        "https://example.com/evidence2",
        [SimpleUploadedFile("evidence2.pdf", b"ok2", content_type="application/pdf")],
    )
    item.refresh_from_db()
    assert item.execution_status == PlanItem.ExecutionStatus.PENDING_REVIEW

    # Current buddy completes the review
    review_evidence(
        submission_2,
        buddy,
        ReviewDecision.Decision.COMPLETED,
        "Looks good now",
    )
    item.refresh_from_db()

    assert item.execution_status == PlanItem.ExecutionStatus.COMPLETED
    assert EvidenceSubmission.objects.count() == 2
