import pytest
from django.test import Client
from django.urls import reverse

from apps.learning.models import LearningPlan, PlanItem
from apps.learning.services_execution import submit_evidence
from apps.learning.services_planning import submit_plan

from .test_metrics import _active_plan, _capability, _user


@pytest.fixture
def buddy_client(db):
    leader = _user("leader", "leader")
    member = _user("member", "member")
    reviewer = _user("reviewer", "member")
    buddy = _user("buddy", "buddy")

    pending = _active_plan(member, buddy, leader, _capability("T01.01.01"))
    pending.status = LearningPlan.Status.DRAFT
    pending.save(update_fields=["status"])
    submit_plan(pending, member)

    review = _active_plan(reviewer, buddy, leader, _capability("T02.01.01"), year=2027)
    submit_evidence(review.items.get(), reviewer, "done", "", [])

    client = Client()
    client.force_login(buddy)
    return client


@pytest.mark.django_db
def test_buddy_dashboard_lists_approval_and_review_todos(buddy_client):
    response = buddy_client.get(reverse("dashboard:buddy"))

    assert response.status_code == 200
    assert response.context["pending_plans"].count() == 1
    assert response.context["pending_reviews"].count() == 1
    assert response.context["pending_reviews"].get().execution_status == (
        PlanItem.ExecutionStatus.PENDING_REVIEW
    )
