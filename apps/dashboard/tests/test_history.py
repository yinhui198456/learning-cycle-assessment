import pytest
from django.test import Client
from django.urls import reverse

from apps.learning.models import LearningCycle

from .test_metrics import _active_plan, _capability, _user


@pytest.fixture
def leader_client(db):
    leader = _user("leader", "leader")
    member = _user("member", "member")
    buddy = _user("buddy", "buddy")
    archived_plan = _active_plan(member, buddy, leader, _capability())
    archived_plan.cycle.status = LearningCycle.Status.ARCHIVED
    archived_plan.cycle.save(update_fields=["status"])

    client = Client()
    client.force_login(leader)
    return client


@pytest.mark.django_db
def test_history_dashboard_lists_archived_cycles_only(leader_client):
    response = leader_client.get(reverse("dashboard:history"))

    assert response.status_code == 200
    cycles = response.context["cycles"]
    assert cycles.count() == 1
    assert cycles.get().status == LearningCycle.Status.ARCHIVED
